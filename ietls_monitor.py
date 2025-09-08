import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from bs4 import BeautifulSoup

# --- Configuration ---
NOVEMBER_URL = "https://irsafam.org/ielts/timetable?month%5B%5D=11"
NO_DATES_MESSAGE_TEXT = "بر اساس جستجوی شما هیچ آزمونی پیدا نشد. لطفا جستجوی خود را اصلاح نمایید."

# Email credentials from GitHub Secrets
EMAIL_ADDRESS = os.environ["EMAIL_ADDRESS"]
EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]
TO_EMAIL = os.environ.get("TO_EMAIL", EMAIL_ADDRESS)  # send to yourself if TO_EMAIL not set

STATUS_FILE = "ielts_november_status.txt"


def get_page_content(url):
    try:
        response = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0'
        })
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"❌ Error fetching page: {e}")
        return None


def check_november_availability(html_content):
    if html_content is None:
        return False
    soup = BeautifulSoup(html_content, 'html.parser')
    warning_div = soup.find('div', class_='alert-warning')
    if warning_div and NO_DATES_MESSAGE_TEXT in warning_div.text:
        return False
    # Look for "تکمیل ظرفیت" (full) or "ثبت نام" (register) buttons
    if soup.find('button', string='تکمیل ظرفیت') or soup.find('button', string='ثبت نام'):
        return True
    return False


def send_notification_email(subject, body):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = TO_EMAIL
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        print("✅ Email sent successfully.")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")


def get_last_status():
    if os.path.exists(STATUS_FILE):
        with open(STATUS_FILE, 'r') as f:
            return f.read().strip()
    return "UNKNOWN"


def save_status(status):
    with open(STATUS_FILE, 'w') as f:
        f.write(status)


if __name__ == "__main__":
    html_content = get_page_content(NOVEMBER_URL)
    last_status = get_last_status()

    if html_content:
        is_available = check_november_availability(html_content)
        if is_available and last_status != "AVAILABLE":
            send_notification_email(
                "✅ IELTS November Dates ARE Available!",
                f"Good news! IELTS November dates appear to be available.\n\nCheck here: {NOVEMBER_URL}"
            )
            save_status("AVAILABLE")
        elif not is_available and last_status == "AVAILABLE":
            send_notification_email(
                "⚠️ IELTS November Dates Disappeared",
                f"IELTS November dates were previously available but now seem gone.\n\nCheck here: {NOVEMBER_URL}"
            )
            save_status("NOT_AVAILABLE")
        else:
            save_status("AVAILABLE" if is_available else "NOT_AVAILABLE")
            print("No change in status.")
    else:
        print("⚠️ Could not fetch page content.")
