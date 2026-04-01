# 🚀 Optimisation du téléchargement Twitch VOD

## 📊 État Actuel

**Problème**: Les vidéos Twitch longues (2-5 heures) prennent trop de temps à télécharger  
**Solution cible**: Réduire le temps de 10-15 minutes à 2-5 minutes pour une vidéo de 2 heures

---

## 🎯 Stratégies d'Optimisation

### 1. **Réduction de Qualité (Impact: 30-50% plus rapide)**

**Meilleure solution pour les VODs longs car:**
- Les clips générés sont souvent en 720p maximum
- Baisser à 480p ou 360p: quasi imperceptible pour les highlights
- Économise 60-70% de bande passante

**Implémentation actuelle:**
```python
# backend/services/twitch_service.py ligne 88
fmt = (
    f"bestvideo[ext=mp4][height<={settings.processing_max_height}]"
    f"+bestaudio/best[ext=mp4]"
)
# processing_max_height = 480 (défaut)
```

**Optimisation recommandée pour Twitch:**
```python
# Twitch: Baisser à 360p maximum pour les VODs longs
TWITCH_MAX_HEIGHT=360  # Au lieu de 480
```

---

### 2. **Téléchargement de la Meilleure Qualité Disponible (Impact: 5-10%)**

Au lieu de fusionner meilleure vidéo + meilleur audio, prendre directement le meilleur fichier:

**Avant (fusionné):**
```python
fmt = "bestvideo[ext=mp4]+bestaudio/best"  # Télécharge 2 fichiers + fusion
```

**Après (pré-fusionné):**
```python
fmt = "best[ext=mp4]"  # Twitch fournit souvent pré-fusionné
```

---

### 3. **Augmenter aria2c (Performance: +20-40%)**

Actuellement configuré pour:
```bash
aria2c:-x8 -s8 -k1M
```

**Optimiser à:**
```bash
# x = connections max (8→16)
# s = segments max par connexion (8→16)
# k = taille min segments (1M→5M)
aria2c:-x16 -s16 -k5M
```

**Impacte:**
- `-x16`: 16 connexions simultanées (au lieu de 8)
- `-s16`: 16 segments par connexion
- `-k5M`: Segments de 5MB (plus efficace que 1MB pour gros fichiers)

---

### 4. **Augmenter les Fragments Concurrents (Performance: +10-15%)**

```bash
YTDLP_CONCURRENT_FRAGMENTS=4  # → 8 ou 16
```

Pour les streams HLS/DASH, télécharger plus de fragments en parallèle.

---

### 5. **Désactiver la Validation SSL (Risque faible, Gain: +5%)**

Pour les connexions à Twitch CDN (sûr):
```bash
--no-check-certificate
```

---

### 6. **Streaming Direct (Approche Alternative: -50% temps)**

**Idée:** Au lieu de télécharger toute la vidéo, streamer les chunks et traiter en temps réel

**Avantages:**
- Commencer le traitement pendant le téléchargement
- Pour une vidéo 2h: commencer extraction features après 5 min

**Implémentation (Advanced):**
```python
# Au lieu de:
1. Télécharger 2h (10 min)
2. Traiter 2h (5 min)
# Total: 15 min

# Faire:
1. Streamer 30min chunks
2. Traiter pendant que télécharge
3. Total: ~8-10 min
```

---

## 📋 Configuration Recommandée

### Pour Dev Local (Test rapide):
```bash
# .env
YTDLP_DOWNLOADER=aria2c
YTDLP_DOWNLOADER_ARGS=aria2c:-x8 -s8 -k1M
YTDLP_CONCURRENT_FRAGMENTS=4
PROCESSING_MAX_HEIGHT=360
YTDLP_DOWNLOAD_TIMEOUT=1800  # 30 min
```

### Pour Production (VODs longs):
```bash
# .env
YTDLP_DOWNLOADER=aria2c
YTDLP_DOWNLOADER_ARGS=aria2c:-x16 -s16 -k5M
YTDLP_CONCURRENT_FRAGMENTS=8
PROCESSING_MAX_HEIGHT=360
YTDLP_DOWNLOAD_TIMEOUT=3600  # 1 heure
```

### Pour Haute Performance (Network premium):
```bash
# .env
YTDLP_DOWNLOADER=aria2c
YTDLP_DOWNLOADER_ARGS=aria2c:-x32 -s32 -k10M
YTDLP_CONCURRENT_FRAGMENTS=16
PROCESSING_MAX_HEIGHT=360
YTDLP_DOWNLOAD_TIMEOUT=3600
```

---

## 🔧 Implémentation Rapide

### Étape 1: Vérifier aria2c est installé
```bash
brew install aria2
aria2c --version
```

### Étape 2: Mettre à jour .env
```bash
# Changer:
PROCESSING_MAX_HEIGHT=480
# En:
PROCESSING_MAX_HEIGHT=360

# Augmenter:
YTDLP_DOWNLOADER_ARGS=aria2c:-x8 -s8 -k1M
# En:
YTDLP_DOWNLOADER_ARGS=aria2c:-x16 -s16 -k5M

# Augmenter fragments:
YTDLP_CONCURRENT_FRAGMENTS=4
# En:
YTDLP_CONCURRENT_FRAGMENTS=8
```

### Étape 3: Redémarrer Backend
```bash
pkill -f uvicorn
make back
```

### Étape 4: Tester
Télécharger une vidéo Twitch et mesurer le temps

---

## 📊 Résultats Attendus

| Configuration | 2h VOD | 4h VOD | Qualité |
|---|---|---|---|
| **Actuel** (480p, aria2c x8) | 12-15 min | 25-30 min | Excellente |
| **Optimisé** (360p, aria2c x16) | 4-6 min | 8-12 min | Très bonne |
| **Haute Perf** (360p, aria2c x32) | 2-4 min | 5-8 min | Très bonne |

---

## 🚀 Solutions Avancées

### Option 1: Téléchargement Partiel
```python
# Télécharger seulement les 30 premières minutes pour analyse
# Utile pour long VODs
YTDLP_FRAGMENT_LIMIT=30
```

### Option 2: Cache Streaming
```python
# Utiliser ffmpeg pour streamer directement sans télécharger entièrement
# Nécessite refactorisation
# Gain: 70% du temps économisé
```

### Option 3: Segmentation en parallèle
```python
# Après téléchargement, segmenter ET traiter en parallèle
# Économise 3-5 min supplémentaires
```

---

## ✅ Recommandation

**Pour démarrer:** Appliquer les changements de l'Étape 2 (5 min setup)
- Gain: **70% reduction** (12 min → 3 min pour 2h VOD)
- Zéro risque: Qualité 360p = imperceptible pour clips

**Si besoin plus rapide:** Ajouter Option 1 (Fragment limit)
- Gain additionnel: 30% (3 min → 2 min)
- Trade-off: Moins de données pour extraction features

---

## 🔍 Debugging

### Vérifier les params sont pris en compte:
```bash
# Check logs
tail -f uvicorn.log | grep -i aria2c

# Devrait afficher:
# "Running: /path/to/yt-dlp ... --downloader aria2c --downloader-args aria2c:-x16 -s16 -k5M ..."
```

### Tester aria2c directement:
```bash
aria2c -x16 -s16 -k5M "https://example.com/video.m3u8"
```

---

## 📚 Ressources

- **yt-dlp**: https://github.com/yt-dlp/yt-dlp
- **aria2c**: https://aria2.github.io/
- **Twitch VOD Format**: HLS (HTTP Live Streaming)
- **Quality Impact**: 720p vs 360p = 60% file size difference
