#!/usr/bin/env python3
"""
Script de reset du mot de passe pour un utilisateur local (SQLite)
Usage :
  export NEW_PASSWORD='Test1234!'
  python reset_password_local.py
"""
from backend.auth.router import hash_password
import sqlite3, os, sys

email = "test.youtube.pro@test.com"
new_pw = os.environ.get("NEW_PASSWORD") or "Test1234!"

db_path = "data/app.db"
if not os.path.exists(db_path):
    print("Fichier DB introuvable:", db_path)
    sys.exit(2)

h = hash_password(new_pw)
conn = sqlite3.connect(db_path)
c = conn.cursor()
# Vérifier si l'utilisateur existe
c.execute("SELECT id, email FROM users WHERE email=?", (email,))
row = c.fetchone()
if not row:
    print("Utilisateur non trouvé:", email)
    conn.close()
    sys.exit(1)

c.execute("UPDATE users SET hashed_password=? WHERE email=?", (h, email))
conn.commit()
conn.close()
print(f"Mot de passe mis à jour pour {email} (nouveau mot de passe: {new_pw})")
