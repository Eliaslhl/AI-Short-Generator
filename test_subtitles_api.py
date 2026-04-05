#!/usr/bin/env python3
"""
Test en DIRECT de la feature sous-titres via API
Génère 2 jobs: UN SANS sous-titres, UN AVEC sous-titres
"""

import urllib.request
import urllib.error
import json
from datetime import datetime
import time

# Config
BASE_URL = "http://localhost:8000"
VIDEO_URL = "https://www.youtube.com/watch?v=IX-ydXPvQqQ"
MAX_CLIPS = 1

# Pour test local, on utilise des valeurs de test
TEST_USER_ID = "test-user-123"


def make_request(endpoint, payload, timeout=300):
    """Faire une requête HTTP POST"""
    url = f"{BASE_URL}{endpoint}"
    
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=data,
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status, json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.reason}
    except Exception as e:
        return None, {"error": str(e)}


def check_server():
    """Vérifier que le serveur est actif"""
    print("\n" + "="*80)
    print("🔍 VÉRIFICATION SERVEUR")
    print("="*80)
    
    try:
        with urllib.request.urlopen(f"{BASE_URL}/health", timeout=5) as response:
            if response.status == 200:
                print(f"✅ Serveur est actif: {BASE_URL}")
                print(f"   Status: {response.status}")
                return True
    except Exception as e:
        print(f"❌ Serveur n'est pas accessible: {e}")
        print("   Assurez-vous que le serveur tourne: make back")
        return False
    
    return False


def test_without_subtitles():
    """Test: Générer UN clip SANS sous-titres"""
    print("\n" + "="*80)
    print("🔴 TEST 1: CLIP SANS SOUS-TITRES (mode par défaut)")
    print("="*80)
    print(f"URL: {VIDEO_URL}")
    print(f"Endpoint: POST {BASE_URL}/api/generate")
    payload_display = {
        "youtube_url": "https://www.youtube.com/watch?v=IX-ydXPvQqQ",
        "max_clips": 1,
        "include_subtitles": False
    }
    print(f"Payload: {json.dumps(payload_display, indent=2)}")
    print("Attente: Pas d'emoji/captions dans le clip\n")
    
    try:
        payload = {
            "youtube_url": VIDEO_URL,
            "max_clips": MAX_CLIPS,
            "include_subtitles": False  # EXPLICITE: pas de sous-titres
        }
        
        print("📤 Envoi requête...")
        status, response = make_request("/api/generate", payload)
        
        print(f"📥 Réponse: HTTP {status}")
        
        if status == 200:
            print("✅ Génération réussie!")
            print(f"   Job ID: {response.get('job_id')}")
            print(f"   Status: {response.get('status')}")
            print(f"   Message: {response.get('message')}")
            return True, response
        else:
            print(f"❌ Erreur HTTP {status}")
            print(f"   Response: {response}")
            return False, None
                
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_with_subtitles():
    """Test: Générer UN clip AVEC sous-titres"""
    print("\n" + "="*80)
    print("🟢 TEST 2: CLIP AVEC SOUS-TITRES")
    print("="*80)
    print(f"URL: {VIDEO_URL}")
    print(f"Endpoint: POST {BASE_URL}/api/generate")
    payload_display = {
        "youtube_url": "https://www.youtube.com/watch?v=IX-ydXPvQqQ",
        "max_clips": 1,
        "include_subtitles": True
    }
    print(f"Payload: {json.dumps(payload_display, indent=2)}")
    print("Attente: Emojis + captions visibles dans le clip\n")
    
    try:
        payload = {
            "youtube_url": VIDEO_URL,
            "max_clips": MAX_CLIPS,
            "include_subtitles": True  # EXPLICITE: avec sous-titres
        }
        
        print("📤 Envoi requête...")
        status, response = make_request("/api/generate", payload)
        
        print(f"📥 Réponse: HTTP {status}")
        
        if status == 200:
            print("✅ Génération réussie!")
            print(f"   Job ID: {response.get('job_id')}")
            print(f"   Status: {response.get('status')}")
            print(f"   Message: {response.get('message')}")
            return True, response
        else:
            print(f"❌ Erreur HTTP {status}")
            print(f"   Response: {response}")
            return False, None
                
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def main():
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*15 + "TEST FEATURE SOUS-TITRES VIA API (EN DIRECT)" + " "*18 + "║")
    print("╚" + "="*78 + "╝")
    
    # Vérifier serveur
    server_ok = check_server()
    
    if not server_ok:
        print("\n⚠️  Serveur non accessible. Démarrez avec: make back")
        return 1
    
    # Test 1: Sans sous-titres
    print("\n⏳ Génération clip SANS sous-titres...")
    test1_ok, data1 = test_without_subtitles()
    
    # Test 2: Avec sous-titres
    print("\n⏳ Génération clip AVEC sous-titres...")
    test2_ok, data2 = test_with_subtitles()
    
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
        print("🎉 REQUÊTES ENVOYÉES AVEC SUCCÈS!")
        print("\n📝 Prochaines étapes:")
        print("   1. Les clips se génèrent en arrière-plan (peut prendre quelques minutes)")
        print("   2. Vérifiez les fichiers dans: data/videos/")
        print("   3. Comparez les deux clips:")
        print("      - Clip SANS subtitles (include_subtitles=false):")
        print("        → Devrait avoir MOINS d'overlay de texte")
        print("      - Clip AVEC subtitles (include_subtitles=true):")
        print("        → Devrait avoir emojis + texte visible")
        print("\n   Job IDs générés:")
        if data1:
            print(f"      • Sans subtitles: {data1.get('job_id')}")
        if data2:
            print(f"      • Avec subtitles:  {data2.get('job_id')}")
    else:
        print("⚠️  Certains tests ont échoué. Voir détails ci-dessus.")
    print("="*80 + "\n")
    
    return 0 if all_pass else 1


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
