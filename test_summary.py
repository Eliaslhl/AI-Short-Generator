#!/usr/bin/env python3
"""
Résumé du test - Afficher les détails finaux
"""

import urllib.request
import json

BASE_URL = "http://localhost:8000"

JOBS = {
    "8e873241": "🔴 CLIP SANS SOUS-TITRES (include_subtitles=false)",
    "c6c842f5": "🟢 CLIP AVEC SOUS-TITRES (include_subtitles=true)",
}


def get_job_status(job_id):
    """Récupérer le statut du job"""
    try:
        url = f"{BASE_URL}/api/test/status/{job_id}"
        with urllib.request.urlopen(url, timeout=5) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        return {"error": str(e)}


def main():
    print("\n" + "="*80)
    print("✨ TEST FEATURE SOUS-TITRES - RÉSUMÉ FINAL")
    print("="*80)
    
    for job_id, label in JOBS.items():
        print(f"\n{label}")
        print("-"*80)
        
        data = get_job_status(job_id)
        
        if "error" in data:
            print(f"  Status: ❌ {data['error']}")
        else:
            status = data.get("status", "unknown")
            progress = data.get("progress", 0)
            clips = data.get("clips", [])
            
            print(f"  Status: {status.upper()}")
            print(f"  Progress: {progress}%")
            print(f"  Clips générés: {len(clips)}")
            
            if clips:
                print(f"  Fichiers:")
                for clip in clips:
                    filename = clip.get("filename", "unknown")
                    print(f"    - {filename}")
    
    print("\n" + "="*80)
    print("📝 PROCHAINES ÉTAPES:")
    print("="*80)
    print("""
1. ATTENDRE LA GÉNÉRATION (peut prendre 5-15 minutes)
   - Chaque job télécharge la vidéo
   - Transcription et génération de clips
   - Rendu des vidéos finales

2. COMPARER LES DEUX CLIPS:
   
   Dossier: data/videos/
   
   Clip SANS sous-titres (8e873241):
   → Devrait avoir MOINS d'overlay de texte
   → Plus rapide à générer (pas de caption rendering)
   → Fichier plus petit
   
   Clip AVEC sous-titres (c6c842f5):
   → Devrait avoir emojis + captions visibles
   → Prend plus de temps (caption rendering)
   → Fichier plus grand

3. VÉRIFIER LES LOGS:
   tail -f /tmp/server.log

4. VÉRIFIER LA BASE DE DONNÉES:
   sqlite3 data/app.db "SELECT id, status, progress FROM jobs ORDER BY created_at DESC LIMIT 2"
""")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
