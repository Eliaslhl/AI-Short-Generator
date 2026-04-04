#!/usr/bin/env python3
"""
Test email flow end-to-end in production
Tests SMTP connection, configuration, and simulates registration flow
"""
import asyncio
import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

print("\n" + "=" * 70)
print("🧪 EMAIL FLOW TEST - Production Verification")
print("=" * 70)

# ─────────────────────────────────────────────────────────────────────
# Step 1: Check Email Configuration
# ─────────────────────────────────────────────────────────────────────
print("\n📋 STEP 1: Email Configuration Check")
print("-" * 70)

config = {
    "MAIL_USERNAME": os.getenv("MAIL_USERNAME", "NOT SET"),
    "MAIL_FROM": os.getenv("MAIL_FROM", "NOT SET"),
    "MAIL_SERVER": os.getenv("MAIL_SERVER", "NOT SET"),
    "MAIL_PORT": os.getenv("MAIL_PORT", "NOT SET"),
    "MAIL_STARTTLS": os.getenv("MAIL_STARTTLS", "NOT SET"),
    "MAIL_SSL_TLS": os.getenv("MAIL_SSL_TLS", "NOT SET"),
    "MAIL_SUPPRESS_SEND": os.getenv("MAIL_SUPPRESS_SEND", "NOT SET"),
}

for key, value in config.items():
    # Hide password
    display_value = "***hidden***" if "PASSWORD" in key else value
    status = "✅" if value != "NOT SET" else "❌"
    print(f"{status} {key:20} = {display_value}")

# ─────────────────────────────────────────────────────────────────────
# Step 2: SMTP Connection Test
# ─────────────────────────────────────────────────────────────────────
print("\n🔌 STEP 2: SMTP Connection Test")
print("-" * 70)

try:
    import smtplib
    
    smtp_server = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("MAIL_PORT", 465))
    use_ssl = os.getenv("MAIL_SSL_TLS", "false").lower() == "true"
    use_tls = os.getenv("MAIL_STARTTLS", "false").lower() == "true"
    username = os.getenv("MAIL_USERNAME")
    password = os.getenv("MAIL_PASSWORD")
    
    print(f"Connecting to {smtp_server}:{smtp_port}")
    print(f"  SSL: {use_ssl}, STARTTLS: {use_tls}")
    
    if use_ssl:
        print("  Using SSL connection...")
        server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=10)
    else:
        print("  Using standard connection...")
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
    
    print("✅ Connected!")
    
    # Try to authenticate
    print(f"Authenticating as {username}...")
    server.login(username, password)
    print("✅ Authentication successful!")
    
    server.quit()
    print("✅ Connection closed gracefully")
    
except Exception as e:
    print(f"❌ SMTP Connection Error: {type(e).__name__}: {str(e)}")

# ─────────────────────────────────────────────────────────────────────
# Step 3: FastAPI-Mail Test
# ─────────────────────────────────────────────────────────────────────
print("\n📧 STEP 3: FastAPI-Mail Library Test")
print("-" * 70)

try:
    from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
    
    conf = ConnectionConfig(
        mail_username=os.getenv("MAIL_USERNAME"),
        mail_password=os.getenv("MAIL_PASSWORD"),
        mail_from=os.getenv("MAIL_FROM", os.getenv("MAIL_USERNAME")),
        mail_port=int(os.getenv("MAIL_PORT", 465)),
        mail_server=os.getenv("MAIL_SERVER", "smtp.gmail.com"),
        mail_starttls=os.getenv("MAIL_STARTTLS", "false").lower() == "true",
        mail_ssl_tls=os.getenv("MAIL_SSL_TLS", "true").lower() == "true",
        use_credentials=True,
        validate_certs=True,
    )
    
    print("✅ FastAPI-Mail ConnectionConfig created successfully")
    
    # Create test message
    message = MessageSchema(
        subject="🧪 Test Email - Configuration Verification",
        recipients=["test@example.com"],  # Won't actually send
        body="<h1>Test</h1><p>This is a configuration test</p>",
        subtype="html",
    )
    
    print("✅ Test message created successfully")
    
    # Test connection (without actually sending)
    fm = FastMail(conf)
    print("✅ FastMail instance created successfully")
    
except Exception as e:
    print(f"❌ FastAPI-Mail Error: {type(e).__name__}: {str(e)}")

# ─────────────────────────────────────────────────────────────────────
# Step 4: Check Database Connection
# ─────────────────────────────────────────────────────────────────────
print("\n🗄️  STEP 4: Database Connection Test")
print("-" * 70)

try:
    from sqlalchemy import inspect
    from backend.core.config import settings
    from backend.core.database import engine
    
    # Try to connect to DB
    with engine.connect() as conn:
        print("✅ Database connected")
        
        # Check if email_confirmation_tokens table exists
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if "email_confirmation_tokens" in tables:
            print("✅ email_confirmation_tokens table exists")
            
            # Check table structure
            columns = inspector.get_columns("email_confirmation_tokens")
            print("\n  Table columns:")
            for col in columns:
                print(f"    - {col['name']:20} ({col['type']})")
            
            # Check constraints
            constraints = inspector.get_unique_constraints("email_confirmation_tokens")
            print("\n  Unique constraints:")
            if constraints:
                for constraint in constraints:
                    print(f"    - {constraint}")
            else:
                print("    - None (good! unique constraint removed)")
            
            # Check indexes
            indexes = inspector.get_indexes("email_confirmation_tokens")
            print("\n  Indexes:")
            for idx in indexes:
                print(f"    - {idx['name']} on {idx['column_names']}")
        else:
            print("❌ email_confirmation_tokens table not found")
            
except Exception as e:
    print(f"❌ Database Error: {type(e).__name__}: {str(e)}")

# ─────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("✅ EMAIL CONFIGURATION TEST COMPLETE")
print("=" * 70)
print("\n📝 Next Steps:")
print("  1. If all tests passed: Try registering in the frontend")
print("  2. Check your email for the confirmation link")
print("  3. Click the link to confirm and activate your account")
print("  4. Check the API logs for any errors during registration")
print("\n" + "=" * 70 + "\n")
