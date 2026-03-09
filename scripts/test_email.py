import asyncio
from pathlib import Path
from dotenv import dotenv_values
from fastapi_mail import FastMail, MessageSchema, MessageType, ConnectionConfig

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
env = dotenv_values(ENV_PATH)
print("MAIL_USERNAME:", env.get("MAIL_USERNAME"))
print("MAIL_SERVER:", env.get("MAIL_SERVER"))
print("MAIL_PORT:", env.get("MAIL_PORT"))
print("SUPPRESS:", env.get("MAIL_SUPPRESS_SEND"))

conf = ConnectionConfig(
    MAIL_USERNAME=env.get("MAIL_USERNAME") or "",
    MAIL_PASSWORD=env.get("MAIL_PASSWORD") or "",
    MAIL_FROM=env.get("MAIL_FROM") or env.get("MAIL_USERNAME") or "",
    MAIL_FROM_NAME="AI Shorts Test",
    MAIL_PORT=int(env.get("MAIL_PORT") or 587),
    MAIL_SERVER=env.get("MAIL_SERVER") or "smtp.gmail.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
    SUPPRESS_SEND=False,
)


async def test():
    fm = FastMail(conf)
    msg = MessageSchema(
        subject="Test AI Shorts Generator",
        recipients=[env.get("MAIL_USERNAME") or ""],
        body="<b>Test envoi email - ca marche !</b>",
        subtype=MessageType.html,
    )
    await fm.send_message(msg)
    print("Email envoye avec succes !")


asyncio.run(test())
