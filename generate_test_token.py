#!/usr/bin/env python3
"""
Créer un token JWT pour tester l'API en local
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from backend.config import settings
from backend.models import User
from backend.auth.jwt_utils import create_jwt_token
from datetime import datetime

# Créer un utilisateur test
test_user = User(
    id="test-user-123",
    email="test@example.com",
    hashed_password="test",
    is_verified=True,
    created_at=datetime.now()
)

# Créer un token
token = create_jwt_token({"sub": test_user.email, "user_id": test_user.id})

print("\n" + "="*80)
print("🔑 TOKEN JWT POUR TEST LOCAL")
print("="*80)
print(f"\nToken: {token}\n")
print("Usage dans les requêtes:")
print(f"  curl -H 'Authorization: Bearer {token}' http://localhost:8000/api/generate\n")
print("="*80 + "\n")
