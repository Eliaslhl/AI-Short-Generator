#!/usr/bin/env python3
"""
Check what config Railway actually has
Add this to backend/main.py startup
"""

import os
import logging

logger = logging.getLogger(__name__)

def log_email_config():
    """Log email config at startup"""
    print("\n" + "=" * 60)
    print("EMAIL CONFIGURATION AT STARTUP")
    print("=" * 60)
    print(f"MAIL_USERNAME:    {os.getenv('MAIL_USERNAME', 'NOT SET')}")
    print(f"MAIL_FROM:        {os.getenv('MAIL_FROM', 'NOT SET')}")
    print(f"MAIL_SERVER:      {os.getenv('MAIL_SERVER', 'NOT SET')}")
    print(f"MAIL_PORT:        {os.getenv('MAIL_PORT', 'NOT SET')}")
    print(f"MAIL_STARTTLS:    {os.getenv('MAIL_STARTTLS', 'NOT SET')}")
    print(f"MAIL_SSL_TLS:     {os.getenv('MAIL_SSL_TLS', 'NOT SET')}")
    print(f"MAIL_SUPPRESS_SEND: {os.getenv('MAIL_SUPPRESS_SEND', 'NOT SET')}")
    print("=" * 60 + "\n")
    
    logger.info("Email config logged above")

# Call this in FastAPI startup event
