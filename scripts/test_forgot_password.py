"""
Test direct de l'endpoint forgot-password + envoi email.
Lance ce script pendant que le backend tourne.
"""
import asyncio
import sys
from pathlib import Path

# Ajouter le root au path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.services.email_service import send_reset_email

async def main():
    token = "test_token_" + "a" * 54  # 64 chars
    email = "eliaslahlouh@gmail.com"
    print(f"Envoi d'un email de reset a {email}...")
    try:
        await send_reset_email(email, token)
        print("✅ Email envoye avec succes !")
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(main())
