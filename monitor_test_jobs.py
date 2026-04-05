#!/usr/bin/env python3
"""
Surveiller la progression des jobs de génération
"""

import urllib.request
import json
import sys
import time

BASE_URL = "http://localhost:8000"

# Les IDs des jobs générés par le test précédent
JOB_IDS = [
    "fc8c3783",  # SANS sous-titres
    "7bd9d557",  # AVEC sous-titres
]

JOB_LABELS = {
    "fc8c3783": "🔴 SANS sous-titres",
    "7bd9d557": "🟢 AVEC sous-titres",
}


def get_status(job_id):
    """Récupérer le statut d'un job"""
    try:
        url = f"{BASE_URL}/api/test/status/{job_id}"
        with urllib.request.urlopen(url, timeout=5) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        return {"error": str(e)}


def print_status(job_id, status_data):
    """Afficher le statut formaté"""
    label = JOB_LABELS.get(job_id, job_id)
    
    if "error" in status_data:
        print(f"  {label}: ❌ {status_data['error']}")
        return False
    
    status = status_data.get("status", "unknown")
    progress = status_data.get("progress", 0)
    message = status_data.get("message", "")
    
    if status == "complete":
        print(f"  {label}: ✅ TERMINÉ ({progress}%)")
        if message:
            print(f"     → {message}")
        return True
    elif status == "failed":
        print(f"  {label}: ❌ ERREUR ({progress}%)")
        if message:
            print(f"     → {message}")
        return False
    else:
        print(f"  {label}: ⏳ {status.upper()} ({progress}%)")
        if message:
            print(f"     → {message}")
        return None


def main():
    print("\n" + "="*80)
    print("📊 SURVEILLANCE DE LA GÉNÉRATION DES CLIPS")
    print("="*80)
    print(f"\nJobs à surveiller:")
    for job_id, label in JOB_LABELS.items():
        print(f"  {label}")
    
    print("\n" + "-"*80)
    
    all_done = False
    iteration = 0
    
    while not all_done:
        iteration += 1
        print(f"\n[Vérification {iteration}] {time.strftime('%H:%M:%S')}")
        print("-"*80)
        
        all_complete = True
        
        for job_id in JOB_IDS:
            status_data = get_status(job_id)
            result = print_status(job_id, status_data)
            
            if result is not True:  # None ou False
                all_complete = False
        
        if all_complete:
            print("\n" + "="*80)
            print("🎉 TOUS LES CLIPS SONT GÉNÉRÉS!")
            print("="*80)
            all_done = True
        else:
            print("\nProchaine vérification dans 30 secondes... (Ctrl+C pour arrêter)")
            try:
                time.sleep(30)
            except KeyboardInterrupt:
                print("\n\n⏸️  Surveillance arrêtée")
                break
    
    print("\n✅ Parcourez les vidéos générées dans: data/videos/\n")
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
