#!/usr/bin/env python3
"""
Test en DIRECT de la feature sous-titres via API
Génère 2 clips: UN SANS sous-titres, UN AVEC sous-titres
"""

import asyncio
import httpx
import json
from datetime import datetime

# Config
BASE_URL = "http://localhost:8000"
VIDEO_URL = "https://www.youtube.com/watch?v=IX-ydXPvQqQ"
MAX_CLIPS = 1

# Pour test local, on utilise des valeurs de test
TEST_USER_ID = "test-user-123"
TEST_JOB_ID_NO_SUBS = f"test-job-no-subs-{int(datetime.now().timestamp())}"
TEST_JOB_ID_WITH_SUBS = f"test-job-with-subs-{int(datetime.now().timestamp())}"


async def test_without_subtitles():
    """Test: Générer UN clip SANS sous-titres"""
    print("\n" + "="*80)
    print("🔴 TEST 1: CLIP SANS SOUS-TITRES (mode par défaut)")
    print("="*80)
    print(f"URL: {VIDEO_URL}")
    print(f"Endpoint: POST {BASE_URL}/api/generate")
    print(f"Body: {{ 'youtube_url': '...', 'max_clips': {MAX_CLIPS}, 'include_subtitles': false }}")
    print("Attente: Pas d'emoji/captions dans le clip\n")
    
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            payload = {
                "youtube_url": VIDEO_URL,
                "max_clips": MAX_CLIPS,
                "include_subtitles": False  # EXPLICITE: pas de sous-titres
            }
            
            print(f"📤 Envoi requête...")
            response = await client.post(
                f"{BASE_URL}/api/generate",
                json=payload
            )
            
            print(f"📥 Réponse: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Génération réussie!")
                print(f"   Job ID: {data.get('job_id')}")
                print(f"   Status: {data.get('status')}")
                print(f"   Message: {data.get('message')}")
                return True, data
            else:
                print(f"❌ Erreur HTTP {response.status_code}")
                print(f"   Response: {response.text}")
                return False, None
                
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False, None


async def test_with_subtitles():
    """Test: Générer UN clip AVEC sous-titres"""
    print("\n" + "="*80)
    print("🟢 TEST 2: CLIP AVEC SOUS-TITRES")
    print("="*80)
    print(f"URL: {VIDEO_URL}")
    print(f"Endpoint: POST {BASE_URL}/api/generate")
    print(f"Body: {{ 'youtube_url': '...', 'max_clips': {MAX_CLIPS}, 'include_subtitles': true }}")
    print("Attente: Emojis + captions visibles dans le clip\n")
    
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            payload = {
                "youtube_url": VIDEO_URL,
                "max_clips": MAX_CLIPS,
                "include_subtitles": True  # EXPLICITE: avec sous-titres
            }
            
            print(f"📤 Envoi requête...")
            response = await client.post(
                f"{BASE_URL}/api/generate",
                json=payload
            )
            
            print(f"📥 Réponse: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Génération réussie!")
                print(f"   Job ID: {data.get('job_id')}")
                print(f"   Status: {data.get('status')}")
                print(f"   Message: {data.get('message')}")
                return True, data
            else:
                print(f"❌ Erreur HTTP {response.status_code}")
                print(f"   Response: {response.text}")
                return False, None
                
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False, None


async def check_server():
    """Vérifier que le serveur est actif"""
    print("\n" + "="*80)
    print("🔍 VÉRIFICATION SERVEUR")
    print("="*80)
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{BASE_URL}/health")
            
            if response.status_code == 200:
                print(f"✅ Serveur est actif: {BASE_URL}")
                print(f"   Response: {response.text}")
                return True
            else:
                print(f"⚠️  Serveur répond avec {response.status_code}")
                return True  # Continue anyway
    except Exception as e:
        print(f"❌ Serveur n'est pas accessible: {e}")
        print(f"   Assurez-vous que le serveur tourne: make back")
        return False


async def main():
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*15 + "TEST FEATURE SOUS-TITRES VIA API (EN DIRECT)" + " "*18 + "║")
    print("╚" + "="*78 + "╝")
    
    # Vérifier serveur
    server_ok = await check_server()
    
    if not server_ok:
        print("\n⚠️  Serveur non accessible. Démarrez avec: make back")
        return 1
    
    # Test 1: Sans sous-titres
    print("\n⏳ Génération clip SANS sous-titres...")
    test1_ok, data1 = await test_without_subtitles()
    
    # Test 2: Avec sous-titres
    print("\n⏳ Génération clip AVEC sous-titres...")
    test2_ok, data2 = await test_with_subtitles()
    
    # Résumé
    print("\n" + "="*80)
    print("📊 RÉSUMÉ DES TESTS")
    print("="*80)
    
    results = {
        "Serveur accessible": "✅",
        "Clip SANS sous-titres": "✅" if test1_ok else "❌",
        "Clip AVEC sous-titres": "✅" if test2_ok else "❌",
    }
    
    for test_name, status in results.items():
        print(f"{status} {test_name}")
    
    all_pass = all(status == "✅" for status in results.values())
    
    print("\n" + "="*80)
    if all_pass:
        print("🎉 TOUS LES TESTS PASSENT!")
        print("\n📝 Prochaines étapes:")
        print("   1. Attendez que les clips se génèrent (peut prendre quelques minutes)")
        print("   2. Vérifiez les fichiers dans: data/videos/")
        print("   3. Comparez les deux clips:")
        print("      - Clip SANS subtitles: devrait avoir MOINS d'overlay")
        print("      - Clip AVEC subtitles: devrait avoir emojis + texte")
    else:
        print("⚠️  Certains tests ont échoué. Voir détails ci-dessus.")
    print("="*80 + "\n")
    
    return 0 if all_pass else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
