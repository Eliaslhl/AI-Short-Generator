#!/usr/bin/env python3
"""
Test simplifié: crée un utilisateur test en base et génère les clips
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

import asyncio
from datetime import datetime, timezone
import uuid

# Imports backend
from sqlalchemy import select
from backend.database import get_db, async_engine, Base
from backend.models.user import User
from backend.models.subscription import SubscriptionPlan
from backend.auth.jwt import create_token


async def create_test_user():
    """Créer un utilisateur test en base de données"""
    print("\n" + "="*80)
    print("👤 CRÉATION UTILISATEUR TEST")
    print("="*80)
    
    # Créer les tables d'abord
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Créer l'utilisateur test
    test_user = User(
        id=str(uuid.uuid4()),
        email="test-subtitles@example.com",
        hashed_password="test",
        is_active=True,
        is_verified=True,
        plan_reset_date=datetime.now(timezone.utc),
    )
    
    # Sauvegarder en base
    async for session in get_db():
        session.add(test_user)
        await session.commit()
        await session.refresh(test_user)
        
        print(f"✅ Utilisateur créé:")
        print(f"   ID: {test_user.id}")
        print(f"   Email: {test_user.email}")
        
        # Créer un token JWT
        token = create_token({"sub": test_user.id})
        print(f"\n🔑 Token JWT généré:")
        print(f"   {token}\n")
        
        return test_user.id, token


async def main():
    try:
        user_id, token = await create_test_user()
        
        print("="*80)
        print("\n✨ Prochaine étape: Utiliser le token pour les requêtes API\n")
        print("Exemple avec curl:")
        print(f'  curl -X POST http://localhost:8000/api/generate \\')
        print(f'    -H "Authorization: Bearer {token}" \\')
        print(f'    -H "Content-Type: application/json" \\')
        print(f'    -d \'{{"youtube_url": "https://www.youtube.com/watch?v=IX-ydXPvQqQ", "max_clips": 1, "include_subtitles": false}}\'')
        print("\n" + "="*80 + "\n")
        
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
