#!/bin/bash
# check_local_env.sh
# Vérifie que tout pointe bien vers le local (backend, DB, front, script)

set -e

# 1. Vérifier DATABASE_URL
if [ -z "$DATABASE_URL" ]; then
  echo "✅ DATABASE_URL n'est PAS défini dans ce shell (OK, local)"
else
  echo "❌ DATABASE_URL est défini: $DATABASE_URL"
  exit 1
fi

# 2. Vérifier que le backend tourne sur SQLite
if grep -q "sqlite+aiosqlite" backend/database.py; then
  echo "✅ backend/database.py contient bien la config SQLite"
else
  echo "❌ backend/database.py ne contient pas la config SQLite"
  exit 1
fi

# 3. Vérifier que le fichier SQLite existe
if [ -f data/app.db ]; then
  echo "✅ Fichier data/app.db trouvé (base locale)"
else
  echo "❌ Fichier data/app.db absent ! Fais un register pour le créer."
  exit 1
fi

# 4. Vérifier que l'utilisateur existe dans la base locale
USER_EMAIL="test.youtube.pro@test.com"
USER_COUNT=$(sqlite3 data/app.db "SELECT COUNT(*) FROM users WHERE email='$USER_EMAIL';")
if [ "$USER_COUNT" -eq 1 ]; then
  echo "✅ Utilisateur $USER_EMAIL trouvé dans la base locale."
else
  echo "❌ Utilisateur $USER_EMAIL absent de la base locale. Fais un register."
  exit 1
fi

# 5. Vérifier que le front utilise bien l'API locale
if [ -f frontend-react/.env.local ]; then
  if grep -q 'VITE_API_URL=http://localhost:8000' frontend-react/.env.local; then
    echo "✅ frontend-react/.env.local pointe bien sur http://localhost:8000"
  else
    echo "❌ frontend-react/.env.local ne pointe pas sur http://localhost:8000"
    exit 1
  fi
else
  echo "⚠️  frontend-react/.env.local absent, vérifie la config front à la main."
fi

echo "\nTout est bien configuré pour le local !"
