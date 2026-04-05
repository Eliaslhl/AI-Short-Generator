#!/usr/bin/env python3
"""
Test la feature sous-titres via l'endpoint TEST sans authentification
"""

import urllib.request
import urllib.error
import json

# Config
BASE_URL = "http://localhost:8000"
VIDEO_URL = "https://www.youtube.com/watch?v=IX-ydXPvQqQ"
MAX_CLIPS = 1


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
        try:
            error_data = json.loads(e.read().decode('utf-8'))
        except:
            error_data = {"error": e.reason}
        return e.code, error_data
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
                print(f"✅ Serveur actif: {BASE_URL}")
                return True
    except Exception as e:
        print(f"❌ Serveur inaccessible: {e}")
        return False
    
    return False


def test_without_subtitles():
    """Test: Générer UN clip SANS sous-titres"""
    print("\n" + "="*80)
    print("🔴 TEST 1: CLIP SANS SOUS-TITRES")
    print("="*80)
    print(f"URL: {VIDEO_URL}")
    print(f"Paramètre: include_subtitles = false")
    print("Attente: Pas d'emoji/text overlay\n")
    
    try:
        payload = {
            "youtube_url": VIDEO_URL,
            "max_clips": MAX_CLIPS,
            "include_subtitles": False
        }
        
        print("📤 Envoi requête à /api/test/generate-subtitles...")
        status, response = make_request("/api/test/generate-subtitles", payload)
        
        print(f"📥 Réponse: HTTP {status}")
        
        if status == 200:
            print("✅ Génération lancée!")
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
    print(f"Paramètre: include_subtitles = true")
    print("Attente: Emojis + captions visibles\n")
    
    try:
        payload = {
            "youtube_url": VIDEO_URL,
            "max_clips": MAX_CLIPS,
            "include_subtitles": True
        }
        
        print("📤 Envoi requête à /api/test/generate-subtitles...")
        status, response = make_request("/api/test/generate-subtitles", payload)
        
        print(f"📥 Réponse: HTTP {status}")
        
        if status == 200:
            print("✅ Génération lancée!")
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
    print("║" + " "*12 + "TEST FEATURE SOUS-TITRES - ENDPOINT TEST (EN DIRECT)" + " "*11 + "║")
    print("╚" + "="*78 + "╝")
    
    # Vérifier serveur
    server_ok = check_server()
    
    if not server_ok:
        print("\n⚠️  Serveur n'est pas accessible.")
        print("   Démarrez le serveur avec: cd ai-shorts-generator && make back")
        return 1
    
    # Test 1: Sans sous-titres
    print("\n⏳ Test 1: Génération SANS sous-titres...")
    test1_ok, data1 = test_without_subtitles()
    
    # Test 2: Avec sous-titres
    print("\n⏳ Test 2: Génération AVEC sous-titres...")
    test2_ok, data2 = test_with_subtitles()
    
    # Résumé
    print("\n" + "="*80)
    print("📊 RÉSUMÉ")
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
        print("   1. Les clips se génèrent en arrière-plan (peut prendre quelques minutes)")
        print("   2. Vérifiez le statut:")
        if data1:
            print(f"      • SANS subtitles: GET /api/status/{data1.get('job_id')}")
        if data2:
            print(f"      • AVEC subtitles:  GET /api/status/{data2.get('job_id')}")
        print("\n   3. Regardez les clips générés dans: data/videos/")
        print("   4. Comparez visuellement:")
        print("      • Clip SANS subtitles → MOINS de texte/emoji overlay")
        print("      • Clip AVEC subtitles → PLUS de captions")
    else:
        print("⚠️  Certains tests ont échoué.")
    print("="*80 + "\n")
    
    return 0 if all_pass else 1


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
