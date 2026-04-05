#!/usr/bin/env python3
"""
Test en DIRECT de la feature sous-titres
Génère 2 clips: UN SANS sous-titres, UN AVEC sous-titres
"""

import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

import asyncio
from backend.config import settings
from backend.api.routes import run_pipeline

# Config
VIDEO_URL = "https://www.youtube.com/watch?v=IX-ydXPvQqQ"
MAX_CLIPS = 1  # Générer juste 1 clip pour chaque test

async def test_without_subtitles():
    """Test: Générer UN clip SANS sous-titres"""
    print("\n" + "="*80)
    print("🔴 TEST 1: CLIP SANS SOUS-TITRES (mode par défaut)")
    print("="*80)
    print(f"URL: {VIDEO_URL}")
    print(f"Config: include_subtitles = False (par défaut)")
    print(f"Attente: Pas d'emoji/captions dans le clip\n")
    
    try:
        # Appel SANS le paramètre include_subtitles (= False par défaut)
        clips = await run_pipeline(
            url=VIDEO_URL,
            max_clips=MAX_CLIPS,
            include_subtitles=False  # EXPLICITE: pas de sous-titres
        )
        
        print(f"✅ Génération réussie!")
        print(f"   Clips générés: {len(clips)}")
        for i, clip in enumerate(clips, 1):
            print(f"   Clip {i}: {clip}")
            
        return True
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_with_subtitles():
    """Test: Générer UN clip AVEC sous-titres"""
    print("\n" + "="*80)
    print("🟢 TEST 2: CLIP AVEC SOUS-TITRES")
    print("="*80)
    print(f"URL: {VIDEO_URL}")
    print(f"Config: include_subtitles = True")
    print(f"Attente: Emojis + captions visibles dans le clip\n")
    
    try:
        # Appel AVEC le paramètre include_subtitles = True
        clips = await run_pipeline(
            url=VIDEO_URL,
            max_clips=MAX_CLIPS,
            include_subtitles=True  # EXPLICITE: avec sous-titres
        )
        
        print(f"✅ Génération réussie!")
        print(f"   Clips générés: {len(clips)}")
        for i, clip in enumerate(clips, 1):
            print(f"   Clip {i}: {clip}")
            
        return True
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_config_default():
    """Test: Vérifier la config par défaut"""
    print("\n" + "="*80)
    print("📋 TEST 3: VÉRIFIER CONFIG PAR DÉFAUT")
    print("="*80)
    
    default_value = settings.include_subtitles_by_default
    print(f"INCLUDE_SUBTITLES_BY_DEFAULT = {default_value}")
    
    if default_value == False:
        print("✅ Config correcte: sous-titres DÉSACTIVÉS par défaut")
        return True
    else:
        print("⚠️  Config inattendue: sous-titres ACTIVÉS par défaut")
        return False


async def main():
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*20 + "TEST FEATURE SOUS-TITRES (EN DIRECT)" + " "*22 + "║")
    print("╚" + "="*78 + "╝")
    
    # Vérifier config
    print("\n🔍 Vérification config...")
    config_ok = await test_config_default()
    
    if not config_ok:
        print("\n⚠️  Config problématique, mais on continue...")
    
    # Test 1: Sans sous-titres
    print("\n⏳ Génération clip SANS sous-titres...")
    test1_ok = await test_without_subtitles()
    
    # Test 2: Avec sous-titres
    print("\n⏳ Génération clip AVEC sous-titres...")
    test2_ok = await test_with_subtitles()
    
    # Résumé
    print("\n" + "="*80)
    print("📊 RÉSUMÉ DES TESTS")
    print("="*80)
    
    results = {
        "Config par défaut": "✅" if config_ok else "❌",
        "Clip SANS sous-titres": "✅" if test1_ok else "❌",
        "Clip AVEC sous-titres": "✅" if test2_ok else "❌",
    }
    
    for test_name, status in results.items():
        print(f"{status} {test_name}")
    
    all_pass = all(status == "✅" for status in results.values())
    
    print("\n" + "="*80)
    if all_pass:
        print("🎉 TOUS LES TESTS PASSENT! La feature fonctionne!")
    else:
        print("⚠️  Certains tests ont échoué. Voir détails ci-dessus.")
    print("="*80 + "\n")
    
    return 0 if all_pass else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
