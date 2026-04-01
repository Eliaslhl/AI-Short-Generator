# 🎬 Configuration Twitch Locale - Guide Complet

## Problème Identifié

Lors de l'utilisation du générateur de shorts localement avec des vidéos Twitch, vous recevez l'erreur:

```
ERROR: Twitch API credentials not configured on server 
(TWITCH_CLIENT_ID / TWITCH_CLIENT_SECRET)
```

## Cause

Les credentials Twitch ne sont pas configurés dans le fichier `.env` local. 
En production sur Railway, ils sont présents, mais en local, il faut les ajouter manuellement.

---

## 🚀 Solution RAPIDE (Recommandé) - Sync depuis Railway

Si vous avez accès à Railway, la façon la plus simple est de synchroniser les credentials existants:

```bash
chmod +x sync_twitch_from_railway.sh
./sync_twitch_from_railway.sh
```

C'est tout! Les credentials de Railway seront copiés dans votre `.env` local.

**Prérequis:**
- Railway CLI installé (`npm i -g @railway/cli` ou `brew install railway`)
- Connecté à Railway (`railway login`)

---

## 📝 Solution MANUELLE - Étape par étape

### 1️⃣ Obtenir vos credentials Twitch

1. Allez sur: https://dev.twitch.tv/console/apps
2. Connectez-vous avec votre compte Twitch
3. Cliquez sur "Create Application"
4. Remplissez le formulaire:
   - **Name**: "AI Shorts Generator (Local)"
   - **OAuth Redirect URLs**: `http://localhost:8000/auth/twitch/callback`
   - **Category**: Desktop Application
5. Acceptez les conditions et créez l'app
6. Cliquez sur "Manage" pour voir vos credentials
7. **Copiez**:
   - Client ID
   - Client Secret

### 2️⃣ Configuration automatique (recommandé)

```bash
cd /Users/elias/Documents/projet/VideoToShortFree/ai-shorts-generator
chmod +x setup_twitch_local.sh
./setup_twitch_local.sh
```

Suivez les prompts et entrez vos credentials.

**OU**

### 2️⃣ Configuration manuelle

Ouvrez `.env` et ajoutez à la fin:

```env
# ── Twitch API ────────────────────────────────────────────────
TWITCH_CLIENT_ID=your_client_id_here
TWITCH_CLIENT_SECRET=your_client_secret_here
```

### 3️⃣ Redémarrer le backend

```bash
# Arrêtez le backend courant (Ctrl+C si en cours)

# Redémarrez:
make backend
# ou
.venv/bin/python -m uvicorn backend.main:app --reload
```

## ✅ Vérification

1. Ouvrez http://localhost:5173 (frontend)
2. Allez à "Twitch"
3. Entrez un channel Twitch (ex: "eliaslhl" ou "twitchdev")
4. Vous devriez voir la liste des VODs

Si vous voyez une liste de vidéos → ✅ **Ça fonctionne!**

## 🔍 Dépannage

### Erreur: "Twitch API credentials not configured"
- ✓ Vérifiez que le `.env` a bien les deux lignes
- ✓ Redémarrez le backend après modification du `.env`
- ✓ Vérifiez les credentials sont corrects

### Erreur: "Invalid Client ID"
- ✓ Vérifiez que vous avez le bon Client ID (pas le Secret!)
- ✓ Vérifiez pas d'espaces avant/après

### Erreur: "No VODs found for channel"
- ✓ Vérifiez que le channel existe
- ✓ Vérifiez que le channel a des VODs (vidéos archivées)
- ✓ Certains channels privés ne montrent pas leurs VODs

### Erreur: "Rate limit exceeded"
- ✓ Attendez quelques minutes
- ✓ La limite Twitch est ~120 requêtes/minute pour les credentials

## 📝 Note de Sécurité

**NE COMMITEZ JAMAIS** votre `TWITCH_CLIENT_SECRET` dans Git!

- Le `.env` est déjà dans `.gitignore`
- Mais faites attention en copiant/collant
- En production, utilisez des variables d'environnement Railway

## 🚀 En Production

Pour Railway:

1. Allez à votre projet Railway
2. Allez à "Variables"
3. Ajoutez:
   ```
   TWITCH_CLIENT_ID=your_client_id
   TWITCH_CLIENT_SECRET=your_client_secret
   ```
4. Redéployez

## 📚 Ressources

- [Twitch Developer Console](https://dev.twitch.tv/console/apps)
- [Twitch API Documentation](https://dev.twitch.tv/docs/api)
- [OAuth 2.0](https://dev.twitch.tv/docs/authentication/oauth-2)

## ✨ Ce que ça permet

Avec cette configuration, vous pouvez maintenant:

✓ Chercher des vidéos Twitch  
✓ Voir la liste complète des VODs d'un channel  
✓ Télécharger des VODs pour générer des shorts  
✓ Tester l'optimisation de téléchargement localement  

---

**Besoin d'aide?** Consultez les logs du backend:
```
tail -f uvicorn.log
```
