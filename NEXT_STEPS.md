# 🎯 PROCHAINES ÉTAPES : Finaliser l'intégration Twitch + Tarification

## 📋 Vue d'ensemble

Le backend **Twitch** et la **nouvelle structure tarifaire** sont en place. Voici ce qui reste à faire.

---

## 🔄 Phase immédiate (1-2 jours)

### 1. Créer les produits Stripe ✅ [TU ES ICI]

**Fichier guide :** `STRIPE_QUICK_SETUP.md`

Étapes :
```bash
1. Va sur https://dashboard.stripe.com/products
2. Crée 6 produits (3 Twitch + 3 Combo)
   - Twitch Standard : 12.99€/mo, 129.99€/year
   - Twitch Pro : 24.99€/mo, 249.99€/year
   - Twitch Pro+ : 34.99€/mo, 349.99€/year
   - Combo Standard : 19.99€/mo, 199.99€/year
   - Combo Pro : 39.99€/mo, 399.99€/year
   - Combo Pro+ : 54.99€/mo, 549.99€/year

3. Copie les 12 price IDs (format: price_xxx)
4. Ajoute-les à .env dans STRIPE_TWITCH_* et STRIPE_COMBO_*
5. Lance : python check_stripe_config.py
```

**Output attendu :**
```
✅ STRIPE_YOUTUBE_STANDARD_MONTHLY_PRICE_ID
✅ STRIPE_YOUTUBE_STANDARD_YEARLY_PRICE_ID
...
✅ STRIPE_TWITCH_STANDARD_MONTHLY_PRICE_ID
...
✅ All Stripe prices are configured!
```

### 2. Appliquer la migration BD

```bash
cd backend
alembic upgrade head
```

**Vérify :**
```bash
sqlite3 ../database.db ".schema users" | grep plan_youtube
```

### 3. Redémarrer le backend

```bash
kill %1  # Si encore running
cd ai-shorts-generator
nohup .venv/bin/python -m uvicorn backend.main:app --reload > uvicorn.log 2>&1 &
```

---

## 🎨 Phase court terme (2-5 jours)

### 4. Frontend : Page Pricing

**Créer :** `frontend-react/src/pages/PricingPage.tsx`

Affiche 3 colonnes :
- **YouTube Plans** : Free, Standard (9.99€), Pro (19.99€), Pro+ (29.99€)
- **Twitch Plans** : Free, Standard (12.99€), Pro (24.99€), Pro+ (34.99€)
- **Combo Packs** : Standard (19.99€), Pro (39.99€), Pro+ (54.99€)

Boutons : "Subscribe" → call `/auth/stripe/checkout` avec params

```typescript
// Pseudo-code
const checkout = async (platform: "youtube" | "twitch" | "combo", plan: "standard" | "pro" | "proplus") => {
  const response = await fetch("/auth/stripe/checkout", {
    method: "POST",
    body: JSON.stringify({ 
      platform,      // "youtube", "twitch", ou "combo"
      plan,
      billing_cycle: "monthly"  // ou "yearly"
    })
  });
  // Redirect à Stripe Checkout
};
```

### 5. Backend : Adapter checkout endpoint

**Fichier :** `backend/auth/router.py` → `create_checkout()`

Modifications :
```python
class CheckoutRequest(BaseModel):
    platform: str  # "youtube", "twitch", "combo"
    plan: str      # "standard", "pro", "proplus"
    billing_cycle: str = "monthly"  # "monthly", "yearly"

async def create_checkout(body: CheckoutRequest, user: User = Depends(get_current_user)):
    from backend.auth.stripe_pricing import get_price_id, PlatformType, BillingCycle
    
    platform = PlatformType(body.platform)
    billing = BillingCycle(body.billing_cycle)
    plan = Plan(body.plan)
    
    price_id = get_price_id(platform, plan, billing)
    
    # Crée la session Stripe (reste pareil)
    session = stripe.checkout.Session.create(
        price=price_id,
        ...
    )
```

### 6. Adapter webhook Stripe

**Fichier :** `backend/auth/router.py` → `stripe_webhook()`

Modifications :
```python
async def stripe_webhook(request):
    event = stripe.Event.construct_from(json.loads(body), stripe.api_key)
    
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        line_items = stripe.checkout.Session.list_line_items(session.id)
        
        # Identifier le produit
        price_id = line_items.data[0].price.id
        from backend.auth.stripe_pricing import parse_price_id
        result = parse_price_id(price_id)
        
        if result:
            platform, plan, billing_cycle = result
            
            if platform.value == "youtube":
                user.plan_youtube = plan
                user.stripe_subscription_id = subscription_id
                user.subscription_type = "youtube"
                
            elif platform.value == "twitch":
                user.plan_twitch = plan
                user.stripe_subscription_id_twitch = subscription_id
                user.subscription_type = "twitch"
                
            elif platform.value == "combo":
                user.plan_youtube = plan
                user.plan_twitch = plan
                user.stripe_subscription_id = subscription_id
                user.stripe_subscription_id_twitch = subscription_id
                user.subscription_type = "combo"
```

### 7. Dashboard utilisateur

**Modifier :** `frontend-react/src/pages/DashboardPage.tsx`

Afficher :
```
Your plans:
├─ YouTube: Pro (50/50 generations used this month)
├─ Twitch: Standard (15/20 generations used this month)
└─ Next reset: April 1st
```

Bouton : "Manage subscriptions" → page de modification

---

## 🧪 Phase test (1-2 jours)

### 8. Tests unitaires

**Créer :** `backend/tests/test_platform_dependencies.py`

```python
import pytest
from backend.auth.platform_dependencies import require_can_generate_youtube, require_can_generate_twitch

@pytest.mark.asyncio
async def test_can_generate_youtube():
    # User avec plan_youtube = "pro"
    # youtube_generations_month = 49
    # Assert: can_generate_youtube = True
    
@pytest.mark.asyncio
async def test_cannot_generate_youtube():
    # User avec plan_youtube = "free"
    # youtube_generations_month = 2
    # Assert: dependency raises HTTP 402
```

### 9. Tests E2E

**Scénario 1 : Subscribe YouTube**
```
1. Register user
2. POST /auth/stripe/checkout { platform: "youtube", plan: "standard", billing: "monthly" }
3. Simule webhook Stripe (checkout.session.completed)
4. Vérify: user.plan_youtube = "standard"
5. POST /api/generate/youtube → OK
6. Vérifiy: user.youtube_generations_month = 1
```

**Scénario 2 : Subscribe Combo**
```
1. Register user
2. POST /auth/stripe/checkout { platform: "combo", plan: "pro", billing: "monthly" }
3. Simule webhook Stripe
4. Vérify: user.plan_youtube = "pro" ET user.plan_twitch = "pro"
5. POST /api/generate/youtube → OK
6. POST /api/twitch/vods → OK
```

**Scénario 3 : Quota exceeded**
```
1. User avec plan_twitch = "free", twitch_generations_month = 2
2. POST /api/twitch/vods → HTTP 402 Payment Required
3. Vérify: error message mentionné "Twitch" et upgrade link
```

---

## 🚀 Phase production (2-5 jours)

### 10. Déployer sur Railway

**Ajouter variables à Railway :**
```bash
STRIPE_YOUTUBE_STANDARD_MONTHLY_PRICE_ID=price_xxx
STRIPE_YOUTUBE_STANDARD_YEARLY_PRICE_ID=price_xxx
... (tous les autres)
```

**Commandes :**
```bash
# Build
git push origin main

# Railway redéploie auto
# Vérify logs : `railway logs -f`
```

### 11. Tester en production

```bash
# Register test user
curl -X POST https://app.railway.app/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"testprod@example.com","password":"testpass123"}'

# Subscribe Twitch
curl -X POST https://app.railway.app/auth/stripe/checkout \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"platform":"twitch","plan":"standard","billing_cycle":"monthly"}'
```

---

## 📊 Documentation à mettre à jour

| Doc | Update |
|-----|--------|
| `README.md` | Ajouter section "Pricing & Subscription" |
| `docs/API.md` | Documenter les nouveaux endpoints `/auth/stripe/checkout` (adapté) |
| `docs/ARCHITECTURE.md` | Décrire le flow YouTube + Twitch |
| `docs/DEPLOYMENT.md` | Lister les env vars Stripe à configurer |

---

## 📱 Fonctionnalités bonus (phase ultérieure)

- [ ] Admin panel : voir les stats de subscription par plan/plateforme
- [ ] Email de bienvenue après subscription (segmenté YouTube/Twitch/Combo)
- [ ] Promo codes Stripe intégrés
- [ ] Dunning management (récupération de cartes expirées)
- [ ] Usage alerts : "You've used 80% of your YouTube quota"
- [ ] Upgrade/downgrade fluide (proration Stripe)

---

## ✅ Checklist final avant prod

- [ ] Tous les price IDs Stripe dans `.env`
- [ ] Migration BD appliquée
- [ ] Frontend page pricing créée
- [ ] Checkout endpoint adapté
- [ ] Webhook gérant les deux subscriptions
- [ ] Dashboard affichant les deux plans
- [ ] Tests unitaires passing
- [ ] Tests E2E passing
- [ ] Variables Railway configurées
- [ ] Production URL testée (curl)

---

## 💡 Quick ref : Fichiers clés

```
📦 Structure critique
├── backend/models/user.py                        ← Dual plans
├── backend/auth/platform_dependencies.py         ← Access control
├── backend/auth/stripe_pricing.py                ← Price mapping
├── backend/auth/router.py                        ← Checkout + webhook (à adapter)
├── backend/api/routes.py                         ← Endpoints generate (utiliser les dépendances)
├── frontend/src/pages/PricingPage.tsx            ← À créer
├── frontend/src/pages/DashboardPage.tsx          ← À adapter
├── .env                                          ← Price IDs à remplir
├── PRICING_STRUCTURE.md                          ← Référence complète
├── STRIPE_QUICK_SETUP.md                         ← Copy-paste pour Stripe
└── check_stripe_config.py                        ← Diagnostic
```

---

## 🎯 Roadmap visuelle

```
NOW          WEEK 1          WEEK 2           WEEK 3
│            │               │                │
├─ Stripe    ├─ Frontend      ├─ Tests        ├─ Production
│  Products  │  (Pricing +    │  (E2E)        │  (Deploy +
│            │   Dashboard)   │                │   Validate)
│            │                │                │
│            ├─ Backend       ├─ Ad-hoc fixes │
│            │  (Checkout +   │  (if needed)  │
│            │   Webhook)     │                │
│            │                │                │
└────────────┴────────────────┴────────────────┴─────
              ~2-3 weeks total
```

---

Bon courage! 🚀 N'hésite pas si tu as des questions ou si tu veux que je détaille une étape spécifique.
