#!/usr/bin/env python3
"""
Direct SMTP connection test to Gmail
"""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

MAIL_USERNAME = os.getenv('MAIL_USERNAME', 'aishortsgenerators@gmail.com')
MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', '')
MAIL_FROM = os.getenv('MAIL_FROM', 'aishortsgenerators@gmail.com')
MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
MAIL_PORT = int(os.getenv('MAIL_PORT', '465'))

print("=" * 60)
print("DIRECT SMTP TEST")
print("=" * 60)
print(f"\nConfiguration:")
print(f"  Username: {MAIL_USERNAME}")
print(f"  From: {MAIL_FROM}")
print(f"  Server: {MAIL_SERVER}:{MAIL_PORT}")
print(f"  Password: {'*' * 8 if MAIL_PASSWORD else 'NOT SET'}")

if not MAIL_PASSWORD:
    print("\n❌ ERROR: MAIL_PASSWORD not set!")
    exit(1)

try:
    print(f"\n1️⃣  Connecting to {MAIL_SERVER}:{MAIL_PORT}...")
    
    # Use SSL (port 465)
    if MAIL_PORT == 465:
        print("   Using SSL connection...")
        server = smtplib.SMTP_SSL(MAIL_SERVER, MAIL_PORT, timeout=10)
    else:
        print("   Using STARTTLS connection...")
        server = smtplib.SMTP(MAIL_SERVER, MAIL_PORT, timeout=10)
        server.starttls()
    
    print("   ✅ Connected!")
    
    print(f"\n2️⃣  Authenticating as {MAIL_USERNAME}...")
    server.login(MAIL_USERNAME, MAIL_PASSWORD)
    print("   ✅ Authentication successful!")
    
    print(f"\n3️⃣  Sending test email...")
    
    msg = MIMEMultipart()
    msg['From'] = MAIL_FROM
    msg['To'] = 'test@example.com'
    msg['Subject'] = 'Test Email from AI Shorts Generator'
    
    body = """
    This is a test email to verify SMTP configuration.
    
    If you received this, the email configuration is working correctly!
    
    - AI Shorts Generator
    """
    
    msg.attach(MIMEText(body, 'plain'))
    
    # Send email
    server.send_message(msg)
    print("   ✅ Email sent successfully!")
    
    server.quit()
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED - SMTP is working!")
    print("=" * 60)
    print("\n📧 Next steps:")
    print("  1. Check your test@example.com inbox (if real)")
    print("  2. Try sending a real email with a test registration")
    print("  3. Check Railway logs if email still doesn't arrive")
    
except smtplib.SMTPAuthenticationError as e:
    print(f"\n❌ AUTHENTICATION FAILED: {e}")
    print("\nPossible causes:")
    print("  1. Wrong App Password (check it has no spaces)")
    print("  2. Gmail 2FA not enabled on the account")
    print("  3. Account not created yet")
    print("\nSolution: Go to https://myaccount.google.com/apppasswords")
    
except smtplib.SMTPException as e:
    print(f"\n❌ SMTP ERROR: {e}")
    print("\nPossible causes:")
    print("  1. Wrong port (try 465 for SSL or 587 for STARTTLS)")
    print("  2. Network/firewall blocking connection")
    print("  3. Server temporarily unavailable")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
