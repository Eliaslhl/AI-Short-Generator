# ⚡ CHECKLIST ULTRA-RAPIDE : Du où tu es maintenant à production

## 🎯 Où tu es maintenant
✅ Backend Twitch VOD listing fonctionne  
✅ Modèle User dual-plan (plan_youtube + plan_twitch)  
✅ Logique d'accès platform-spécifique  
✅ Stripe pricing config smart  
✅ Documentation complète  

---

## 📌 IMMEDIATE (1-2h)

- [ ] Ouvre https://dashboard.stripe.com/products
- [ ] Crée 6 produits (voir `STRIPE_QUICK_SETUP.md` - copy-paste)
  - [ ] Twitch Standard (12.99€)
  - [ ] Twitch Pro (24.99€)
  - [ ] Twitch Pro+ (34.99€)
  - [ ] Combo Standard (19.99€)
  - [ ] Combo Pro (39.99€)
  - [ ] Combo Pro+ (54.99€)
- [ ] Copie les 12 price IDs (format: `price_xxx`)
- [ ] Ajoute-les à `.env`
- [ ] Lance: `python check_stripe_config.py` → output doit être ✅
- [ ] Redémarre le backend

---

## 📊 BASE DE DONNÉES (15 min)

- [ ] `cd backend && alembic upgrade head`
- [ ] Vérifie: `sqlite3 ../database.db ".schema users" | grep plan_youtube`

---

## 🎨 FRONTEND (à faire - 1-2 jours)

### Pages à créer/adapter

- [ ] `frontend-react/src/pages/PricingPage.tsx`
  - 3 colonnes (YouTube | Twitch | Combo)
  - Boutons Subscribe → POST /auth/stripe/checkout
  
- [ ] Adapter `frontend-react/src/pages/DashboardPage.tsx`
  - Afficher "YouTube: Pro (50/50) | Twitch: Free (2/2)"
  
- [ ] Adapter `frontend-react/src/pages/HomePage.tsx` (ou landing)
  - Lien vers page pricing

### API client (`frontend-react/src/api/index.ts`)

- [ ] Ajouter:
```typescript
export const checkout = async (platform: "youtube" | "twitch" | "combo", plan: "standard" | "pro" | "proplus") => {
  return fetch("/auth/stripe/checkout", {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ platform, plan, billing_cycle: "monthly" })
  }).then(r => r.json());
};
```

---

## 🔧 BACKEND (à adapter - 1 jour)

### Endpoint checkout

**Fichier:** `backend/auth/router.py`

Adapter `create_checkout()`:
```python
# Ajouter platform + billing_cycle aux params
# Utiliser stripe_pricing.get_price_id(platform, plan, billing_cycle)
```

### Webhook

**Fichier:** `backend/auth/router.py`

Adapter `stripe_webhook()`:
```python
# Identifier le produit via price_id
# Si platform = "youtube" → update plan_youtube + stripe_subscription_id
# Si platform = "twitch" → update plan_twitch + stripe_subscription_id_twitch
# Si platform = "combo" → update BOTH
```

---

## 🧪 TESTS (optional mais recommandé - 1 jour)

- [ ] Tests unitaires : `require_can_generate_youtube()`, `require_can_generate_twitch()`
- [ ] Tests E2E : 
  - Subscribe YouTube → generate YouTube OK
  - Subscribe Twitch → generate Twitch OK
  - Subscribe Combo → both OK
  - Quota exceeded → HTTP 402

---

## 🚀 PRODUCTION (1-2 jours)

- [ ] Ajouter les env vars Stripe à Railway dashboard
- [ ] `git push origin main` → Railway redéploie
- [ ] Test: créer un utilisateur en prod, subscribe, générer
- [ ] Monitor les logs

---

## 🐛 DEBUG rapide

**Le backend ne restart pas après modif de `.env`?**
```bash
kill %1  # kill le processus
nohup .venv/bin/python -m uvicorn backend.main:app --reload > uvicorn.log 2>&1 &
```

**Les price IDs ne sont pas reconnus?**
```bash
python check_stripe_config.py  # Diagnostic
# Vérify: price_id format = price_xxx (pas vide)
```

**Test d'un endpoint rapidement?**
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"pass"}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s http://localhost:8000/auth/me \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

---

## 📖 Docs rapides

| Quand? | Lis |
|--------|-----|
| Créer produits Stripe | `STRIPE_QUICK_SETUP.md` |
| Vue d'ensemble complète | `PRICING_STRUCTURE.md` |
| Comment ça marche? | `PRICING_IMPLEMENTATION_SUMMARY.md` |
| Prochaines étapes détaillées | `NEXT_STEPS.md` |

---

## ✅ Validation final

Avant de dire "fini":

```bash
✅ check_stripe_config.py output = all green
✅ BD migration appliquée
✅ Frontend pricing page créée
✅ Backend checkout endpoint adapté
✅ Webhook gérant les 2 platforms
✅ Test: Subscribe YouTube → generate YouTube
✅ Test: Subscribe Twitch → generate Twitch
✅ Test: Subscribe Combo → generate both
✅ Prod: env vars Railway configurées
✅ Prod: test utilisateur fonctionne
```

---

C'est parti! 🚀
