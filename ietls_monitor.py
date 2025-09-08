import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
import os # To potentially use environment variables for sensitive info

# --- Configuration ---
NOVEMBER_URL = "https://irsafam.org/ielts/timetable?month%5B%5D=11"
# The text that indicates NO dates are available for November
NO_DATES_MESSAGE_TEXT = "بر اساس جستجوی شما هیچ آزمونی پیدا نشد. لطفا جستجوی خود را اصلاح نمایید."

# Email settings
# It's recommended to use environment variables for sensitive data like passwords.
# Example: EMAIL_ADDRESS = os.environ.get("IELTS_EMAIL_ADDRESS")
EMAIL_ADDRESS = "road2product@gmail.com"  # Your sending email address
EMAIL_PASSWORD = "edju jalq npwv vroo"    # Your Gmail App Password
RECIPIENT_EMAIL = "road2product@gmail.com" # Where to send the notification
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465 # 465 for SSL, 587 for TLS (STARTTLS)

# Polling interval (how often to check the website) in seconds
# Checking every 5 minutes (300 seconds) to quickly catch any available dates
POLLING_INTERVAL_SECONDS = 300 # Check every 5 minutes

# File to keep track of the last known status
# This prevents sending multiple emails if dates are found.
STATUS_FILE = "ielts_november_status.txt"

# --- Functions ---

def get_page_content(url, max_retries=3):
    """Fetches the HTML content of a given URL with retries."""
    for attempt in range(max_retries):
        try:
            print(f"Attempt {attempt + 1} of {max_retries} to fetch the page...")
            response = requests.get(url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36'
            })
            response.raise_for_status()
            print("Successfully fetched the page!")
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"Error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 5  # Progressive delay: 5s, 10s, 15s
                print(f"Waiting {wait_time} seconds before retrying...")
                time.sleep(wait_time)
            else:
                print("All retry attempts failed.")
                return None

def check_november_availability(html_content):
    """
    Checks the HTML content for the presence of November dates.
    It returns True if dates are found, False otherwise.
    """
    if html_content is None:
        return False

    soup = BeautifulSoup(html_content, 'html.parser')

    # The warning message for no dates is inside a <p> tag within a <div> with class "alert alert-warning"
    warning_div = soup.find('div', class_='alert-warning')

    if warning_div and NO_DATES_MESSAGE_TEXT in warning_div.text:
        return False # No dates found, warning message is present
    else:
        # If the warning div is not found OR if its text does NOT contain the NO_DATES_MESSAGE
        # it means there might be dates or other content.
        # We also need to check for actual date listings to be sure.
        # The actual date listings are in <div class="col-md-9 offset-lg-0 col-lg-9"> which contain other elements like "تکمیل ظرفیت"
        # Let's look for the main container of date cards
        date_cards_container = soup.find('div', class_='col-md-9') # This seems to hold the date entries

        # If this container exists and it has more than just empty space or the warning,
        # it's a good indicator that dates might be listed.
        # This is a bit of an assumption and might need fine-tuning if the HTML structure changes.
        if date_cards_container:
            # Check for specific date entry elements. Example:
            # A date entry seems to be wrapped in <div class="row pt-lg-4 pt-sm-4 pb-lg-3 pb-sm-3 pr-lg-3 pl-lg-3 mb-lg-4 mb-sm-4">
            # or it's within 'col-md-9' and contains 'تکمیل ظرفیت' (full) or 'ثبت نام' (register)
            if soup.find('button', string='تکمیل ظرفیت') or soup.find('button', string='ثبت نام'):
                return True # Found buttons related to dates, even if full
            elif NO_DATES_MESSAGE_TEXT not in html_content:
                # If the warning message is explicitly NOT in the HTML, and we found the container,
                # it's very likely dates are there.
                return True

        return False # Fallback: Assume no dates if specific indicators aren't met


def send_notification_email(subject, body):
    """Sends an email notification."""
    msg = MIMEMultipart()
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = RECIPIENT_EMAIL
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server: # Use SMTP_SSL for port 465
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        print("Email notification sent successfully!")
    except smtplib.SMTPAuthenticationError:
        print("Failed to send email: Authentication error. Check your email address and app password.")
    except Exception as e:
        print(f"Failed to send email: {e}")

def get_last_status():
    """Reads the last known status from a file."""
    if os.path.exists(STATUS_FILE):
        with open(STATUS_FILE, 'r') as f:
            return f.read().strip()
    return "UNKNOWN"

def save_status(status):
    """Saves the current status to a file."""
    with open(STATUS_FILE, 'w') as f:
        f.write(status)

# --- Main Monitoring Loop ---
if __name__ == "__main__":
    print("Starting IELTS November timetable monitor...")
    
    # Send a test email to verify the email configuration
    print("Sending test email...")
    send_notification_email(
        "IELTS Monitor - Started Monitoring",
        "The IELTS monitoring script has started and will check for November dates every 5 minutes.\n\n" +
        f"The script will monitor this URL: {NOVEMBER_URL}\n\n" +
        "You will receive notifications when:\n" +
        "1. November dates become available\n" +
        "2. Every 24 hours as a status update\n" +
        "3. If there are any errors or issues\n\n" +
        "The script is now running..."
    )
    
    # Add variables for daily status tracking
    last_daily_update = time.time()
    DAILY_UPDATE_INTERVAL = 24 * 60 * 60  # 24 hours in seconds
    
    last_status = get_last_status()
    print(f"Last known status: {last_status}")

    while True:
        print(f"\nChecking November timetable at {time.ctime()}...")
        html_content = get_page_content(NOVEMBER_URL)

        if html_content:
            is_available = check_november_availability(html_content)

            if is_available:
                if last_status != "AVAILABLE":
                    subject = "IELTS November Dates ARE Available!"
                    body = f"Good news! IELTS November dates appear to be available on irsafam.org.\n\nCheck here: {NOVEMBER_URL}\n\nThis is an automated notification."
                    send_notification_email(subject, body)
                    save_status("AVAILABLE")
                    last_status = "AVAILABLE"
                    print("November dates found and notification sent!")
                else:
                    print("November dates are still available. No new notification needed.")
            else:
                if last_status == "AVAILABLE":
                    # This case handles if dates were available but then disappeared (less common)
                    subject = "IELTS November Dates Disappeared (Re-check Needed)"
                    body = f"IELTS November dates were previously available but now seem to be gone. Please check: {NOVEMBER_URL}"
                    send_notification_email(subject, body)
                    save_status("NOT_AVAILABLE")
                    last_status = "NOT_AVAILABLE"
                    print("November dates disappeared and notification sent.")
                else:
                    print("November dates not yet available.")
                    save_status("NOT_AVAILABLE") # Keep status updated even if not available
                    last_status = "NOT_AVAILABLE"
        else:
            print("Could not fetch page content. Will retry later.")
            # Do not change status if page fetch failed, to avoid losing "AVAILABLE" status mistakenly

        # Check if it's time for daily status update
        current_time = time.time()
        if current_time - last_daily_update >= DAILY_UPDATE_INTERVAL:
            print("Sending daily status update...")
            send_notification_email(
                "IELTS Monitor - Daily Status Update",
                f"The IELTS monitoring script is still running and checking for November dates every 5 minutes.\n\n" +
                f"Current status: {'AVAILABLE' if last_status == 'AVAILABLE' else 'No dates available yet'}\n" +
                f"Last checked: {time.ctime()}\n\n" +
                f"The script will continue monitoring: {NOVEMBER_URL}"
            )
            last_daily_update = current_time
            
        print(f"Waiting for {POLLING_INTERVAL_SECONDS} seconds before next check...")
        time.sleep(POLLING_INTERVAL_SECONDS)