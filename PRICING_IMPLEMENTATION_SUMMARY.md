# ✅ Résumé final : Structure tarifaire YouTube + Twitch

## 📌 Situation actuelle

✅ **Complété** :
- Modèle User : champs `plan_youtube`, `plan_twitch`, quotas séparés
- Logique d'accès : `require_can_generate_youtube()` et `require_can_generate_twitch()`
- Configuration Stripe : mapping smart `stripe_pricing.py`
- `.env` : préparé avec placeholders pour tous les price IDs
- Documentation complète : `PRICING_STRUCTURE.md`, `STRIPE_QUICK_SETUP.md`
- Script de vérification : `check_stripe_config.py`

🔴 **À faire** :
1. Créer les 6 produits Stripe (Twitch + Combo)
2. Récupérer les 12 price IDs
3. Les ajouter à `.env`
4. Vérifier avec `check_stripe_config.py`
5. Redémarrer le backend
6. Tester les endpoints

---

## 💰 Grille tarifaire finale

```
┌────────────────────────────────────────────────────────────┐
│                    PLAN COMPARISON                         │
├──────────────┬──────────────┬──────────────┬──────────────┤
│ YOUTUBE ONLY │ TWITCH ONLY  │ COMBO        │ FREE         │
├──────────────┼──────────────┼──────────────┼──────────────┤
│ Standard     │ Standard     │ Standard     │ -            │
│ 9.99€/mo     │ 12.99€/mo    │ 19.99€/mo    │ Gratuit      │
│              │              │ (Save 2.99€) │              │
├──────────────┼──────────────┼──────────────┼──────────────┤
│ Pro          │ Pro          │ Pro          │ 2 gen/month  │
│ 19.99€/mo    │ 24.99€/mo    │ 39.99€/mo    │ 1x concurrent│
│              │              │ (Save 4.99€) │              │
├──────────────┼──────────────┼──────────────┼──────────────┤
│ Pro+         │ Pro+         │ Pro+         │ Unlimited    │
│ 29.99€/mo    │ 34.99€/mo    │ 54.99€/mo    │ features!    │
│              │              │ (Save 9.99€) │              │
└──────────────┴──────────────┴──────────────┴──────────────┘

Generations par mois:
- FREE : 2
- STANDARD : 20
- PRO : 50
- PRO+ : 100
```

---

## 🔑 Règles d'accès (logique backend)

```
Utilisateur A : YouTube Pro + Twitch Free
  → plan_youtube = "pro" (50 gen/mois)
  → plan_twitch = "free" (2 gen/mois)

Utilisateur B : YouTube Free + Twitch Standard
  → plan_youtube = "free" (2 gen/mois)
  → plan_twitch = "standard" (20 gen/mois)

Utilisateur C : Combo Pro (YouTube + Twitch)
  → plan_youtube = "pro" (50 gen/mois)
  → plan_twitch = "pro" (50 gen/mois)
  → subscription_type = "combo"
```

---

## 📂 Fichiers importants

```
backend/
  models/
    user.py                    ← User model avec dual plans
  auth/
    platform_dependencies.py   ← require_can_generate_youtube/twitch
    stripe_pricing.py          ← Mapping smart des price IDs
  migrations/
    versions/
      002_add_platform_plans.py ← Migration BD (à appliquer)

.env                           ← Prix Twitch + Combo à remplir

Docs:
  PRICING_STRUCTURE.md         ← Vue d'ensemble complète
  STRIPE_QUICK_SETUP.md        ← Copier-coller pour Stripe
  STRIPE_SETUP_INSTRUCTIONS.md ← Guide détaillé

Scripts:
  check_stripe_config.py       ← Vérifier la config
```

---

## 🚀 Prochaines étapes en ordre

### Phase 1 : Stripe (30 min)
```bash
1. Va sur https://dashboard.stripe.com/products
2. Crée 6 produits (voir STRIPE_QUICK_SETUP.md)
3. Copie les 12 price IDs (format: price_xxx)
4. Ajoute-les à .env dans les bonnes variables
5. Lance check_stripe_config.py pour vérifier
```

### Phase 2 : Base de données (5 min)
```bash
# Appliquer la migration
alembic upgrade head

# Vérifier les colonnes (SQLite)
sqlite3 database.db ".schema users"
```

### Phase 3 : Backend (30 min)
```bash
1. Redémarre le serveur (il recharge .env)
2. Teste avec curl:
   
   # Obtenir un token
   TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"user@example.com","password":"pass"}' \
     | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
   
   # Vérifier les générations YouTube
   curl -s http://localhost:8000/auth/me \
     -H "Authorization: Bearer $TOKEN" | python -m json.tool

3. Modifier manuellement un user pour tester:
   - user.plan_youtube = "standard"
   - user.plan_twitch = "pro"
   - user.youtube_generations_month = 0
   - user.twitch_generations_month = 0
```

### Phase 4 : Frontend (1-2h)
```
1. Créer une page /pricing avec 3 colonnes (YouTube | Twitch | Combo)
2. Boutons "Subscribe to [Plan]" → call /auth/stripe/checkout
3. Dashboard utilisateur :
   - Afficher "YouTube: Pro (50/50) | Twitch: Standard (10/20)"
4. Modifier l'abonnement :
   - "Switch to Combo Pro" (proration automatique Stripe)
```

### Phase 5 : Tests & déploiement
```
1. Tests unitaires pour les dépendances
2. Tests E2E : workflow complet (register → subscribe → generate)
3. Déployer sur Railway avec les nouvelles env vars
```

---

## 🎯 Détails techniques clés

### 1️⃣ Vérification d'accès (exemple)

```python
# Dans un endpoint qui nécessite de générer sur YouTube
@router.post("/generate/youtube")
async def generate_youtube(
    user: User = Depends(require_can_generate_youtube),  # ← Nouvelle dépendance
    db: AsyncSession = Depends(get_db)
):
    # Si user n'a pas accès → HTTP 402 auto
    # Sinon → génération normale
    user.youtube_generations_month += 1
    await db.commit()
```

### 2️⃣ Stripe checkout (sera à adapter)

```python
# Avant : simple, 1 seul plan
def checkout(plan_name: str):
    price_id = PRICE_TO_PLAN[plan_name]  # ❌ Ancien code
    
# Après : 3 catégories
def checkout(platform: str, plan: str, cycle: str):  # youtube | twitch | combo
    price_id = get_price_id(platform, plan, cycle)  # ✅ Nouveau code
```

### 3️⃣ Webhook Stripe (à adapter)

Actuellement : met à jour `user.plan` et `user.stripe_subscription_id`

À faire : gérer aussi `user.plan_twitch` et `user.stripe_subscription_id_twitch`

---

## 📊 Vérifications post-déploiement

✅ Checklist finale :

- [ ] Tous les 12 price IDs configurés dans Stripe
- [ ] `.env` contient tous les price IDs réels
- [ ] Migration BD appliquée (colonnes plan_youtube, plan_twitch, etc.)
- [ ] `check_stripe_config.py` retourne ✅
- [ ] Backend redémarré et recharge `.env`
- [ ] Test de génération YouTube avec un utilisateur
- [ ] Test de génération Twitch avec un autre utilisateur
- [ ] Test de subscription Combo (génération sur les deux)
- [ ] Frontend affiche les 3 catégories de plans
- [ ] Utilisateur peut switcher d'abonnement
- [ ] Webhook Stripe met à jour les deux plans correctement

---

## 💬 Questions courantes

**Q: Qu'arrive-t-il à un utilisateur YouTube payant s'il ajoute Twitch?**
A: Son `plan_youtube` reste identique, son `plan_twitch` passe à la valeur sélectionnée, son `subscription_type` = "combo".

**Q: Comment gérer la proration (paiement partiel)?**
A: Stripe gère ça automatiquement si tu utilises `proration_behavior="create_prorations"` lors du changement de subscription.

**Q: Les quotas se réinitialisent comment?**
A: Via les dépendances `require_can_generate_youtube/twitch` qui vérifient `youtube_plan_reset_date` et `twitch_plan_reset_date` (lazy reset chaque mois).

**Q: Comment migrer les utilisateurs existants?**
A: Ils gardent leur `plan` YouTube et `plan_twitch` = FREE. Le script `migrate_users_to_dual_plans.py` peut le faire automatiquement.

---

## 📞 Support

Si tu as des questions :
1. Relis `PRICING_STRUCTURE.md` (complet)
2. Relis `STRIPE_QUICK_SETUP.md` (pratique)
3. Lance `check_stripe_config.py` (diagnostic)

Bonne chance! 🚀
