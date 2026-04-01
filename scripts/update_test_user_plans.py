#!/usr/bin/env python3
"""
update_test_user_plans.py
Ajuste les plans et quotas des comptes de test dans la base SQLite locale selon le tableau fourni.
"""
import sqlite3
from datetime import datetime

db_path = "data/app.db"
users = [
    # Youtube Platform
    {"email": "test.youtube.free@test.com", "plan_youtube": "free", "plan_twitch": "free", "yt_limit": 1, "tw_limit": 1},
    {"email": "test.youtube.standard@test.com", "plan_youtube": "standard", "plan_twitch": "free", "yt_limit": 10, "tw_limit": 1},
    {"email": "test.youtube.pro@test.com", "plan_youtube": "pro", "plan_twitch": "free", "yt_limit": 25, "tw_limit": 1},
    {"email": "test.youtube.proplus@test.com", "plan_youtube": "proplus", "plan_twitch": "free", "yt_limit": 50, "tw_limit": 1},
    # Twitch Platform
    {"email": "test.twitch.free@test.com", "plan_youtube": "free", "plan_twitch": "free", "yt_limit": 1, "tw_limit": 1},
    {"email": "test.twitch.standard@test.com", "plan_youtube": "free", "plan_twitch": "standard", "yt_limit": 1, "tw_limit": 10},
    {"email": "test.twitch.pro@test.com", "plan_youtube": "free", "plan_twitch": "pro", "yt_limit": 1, "tw_limit": 25},
    {"email": "test.twitch.proplus@test.com", "plan_youtube": "free", "plan_twitch": "proplus", "yt_limit": 1, "tw_limit": 50},
    # Combo Platform
    {"email": "test.combo.standard@test.com", "plan_youtube": "standard", "plan_twitch": "standard", "yt_limit": 10, "tw_limit": 10},
    {"email": "test.combo.pro@test.com", "plan_youtube": "pro", "plan_twitch": "pro", "yt_limit": 25, "tw_limit": 25},
    {"email": "test.combo.proplus@test.com", "plan_youtube": "proplus", "plan_twitch": "proplus", "yt_limit": 50, "tw_limit": 50},
]

conn = sqlite3.connect(db_path)
c = conn.cursor()

for u in users:
    c.execute("""
        UPDATE users
        SET plan_youtube=?, plan_twitch=?, youtube_generations_month=0, twitch_generations_month=0, updated_at=?
        WHERE email=?
    """, (u["plan_youtube"], u["plan_twitch"], datetime.utcnow().isoformat(), u["email"]))
    # Optionnel : tu peux aussi forcer le plan principal (legacy)
    c.execute("""
        UPDATE users
        SET plan=?
        WHERE email=?
    """, (u["plan_youtube"], u["email"]))

conn.commit()
conn.close()
print("Plans et quotas mis à jour pour tous les comptes de test.")
