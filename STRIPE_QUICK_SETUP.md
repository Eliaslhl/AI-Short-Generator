# 🚀 Quick Stripe Setup : Twitch + Combo Products

## ⚡ Résumé ultra-rapide

Tu dois créer **6 produits** dans Stripe Dashboard :
- 3 produits **Twitch** (Standard, Pro, Pro+)
- 3 produits **Combo** (YouTube + Twitch)

Chaque produit = 2 prix (mensuel + annuel).

---

## 📍 URL Stripe Dashboard

👉 https://dashboard.stripe.com/products

---

## 🎮 TWITCH PRODUCTS

### 1️⃣ Twitch Standard

**À copier-coller dans Stripe :**

| Champ | Valeur |
|-------|--------|
| **Product Name** | `Twitch Standard` |
| **Description** | `20 generations/month • Unlimited clips • 1x concurrent` |
| **Type** | Recurring |
| **Price 1** | 9.99€ • Monthly • Lookup: `price_tw_std_m` |
| **Price 2** | 94.99€ • Yearly • Lookup: `price_tw_std_y` |

**Après création → copie les 2 price IDs et ajoute à `.env` :**
```bash
STRIPE_TWITCH_STANDARD_MONTHLY_PRICE_ID=price_xxxxxx
STRIPE_TWITCH_STANDARD_YEARLY_PRICE_ID=price_yyyyyy
```

---

### 2️⃣ Twitch Pro

| Champ | Valeur |
|-------|--------|
| **Product Name** | `Twitch Pro` |
| **Description** | `50 generations/month • Unlimited clips • 5x concurrent` |
| **Type** | Recurring |
| **Price 1** | 29.99€ • Monthly • Lookup: `price_tw_pro_m` |
| **Price 2** | 279.99€ • Yearly • Lookup: `price_tw_pro_y` |

**Ajoute à `.env` :**
```bash
STRIPE_TWITCH_PRO_MONTHLY_PRICE_ID=price_xxxxxx
STRIPE_TWITCH_PRO_YEARLY_PRICE_ID=price_yyyyyy
```

---

### 3️⃣ Twitch Pro+

| Champ | Valeur |
|-------|--------|
| **Product Name** | `Twitch Pro+` |
| **Description** | `100 generations/month • Unlimited clips • 10x concurrent` |
| **Type** | Recurring |
| **Price 1** | 54.99€ • Monthly • Lookup: `price_tw_proplus_m` |
| **Price 2** | 529.99€ • Yearly • Lookup: `price_tw_proplus_y` |

**Ajoute à `.env` :**
```bash
STRIPE_TWITCH_PROPLUS_MONTHLY_PRICE_ID=price_xxxxxx
STRIPE_TWITCH_PROPLUS_YEARLY_PRICE_ID=price_yyyyyy
```

---

## 📦 COMBO PRODUCTS

### 4️⃣ Combo Standard

| Champ | Valeur |
|-------|--------|
| **Product Name** | `Combo Standard` |
| **Description** | `YouTube + Twitch • 20 gen/month each • Pack` |
| **Type** | Recurring |
| **Price 1** | 14.99€ • Monthly • Lookup: `price_combo_std_m` |
| **Price 2** | 129.99€ • Yearly • Lookup: `price_combo_std_y` |

**Ajoute à `.env` :**
```bash
STRIPE_COMBO_STANDARD_MONTHLY_PRICE_ID=price_xxxxxx
STRIPE_COMBO_STANDARD_YEARLY_PRICE_ID=price_yyyyyy
```

---

### 5️⃣ Combo Pro

| Champ | Valeur |
|-------|--------|
| **Product Name** | `Combo Pro` |
| **Description** | `YouTube + Twitch • 50 gen/month each • Pack` |
| **Type** | Recurring |
| **Price 1** | 39.99€ • Monthly • Lookup: `price_combo_pro_m` |
| **Price 2** | 379.99€ • Yearly • Lookup: `price_combo_pro_y` |

**Ajoute à `.env` :**
```bash
STRIPE_COMBO_PRO_MONTHLY_PRICE_ID=price_xxxxxx
STRIPE_COMBO_PRO_YEARLY_PRICE_ID=price_yyyyyy
```

---

### 6️⃣ Combo Pro+

| Champ | Valeur |
|-------|--------|
| **Product Name** | `Combo Pro+` |
| **Description** | `YouTube + Twitch • 100 gen/month each • Pack` |
| **Type** | Recurring |
| **Price 1** | 64.99€ • Monthly • Lookup: `price_combo_proplus_m` |
| **Price 2** | 649.99€ • Yearly • Lookup: `price_combo_proplus_y` |

**Ajoute à `.env` :**
```bash
STRIPE_COMBO_PROPLUS_MONTHLY_PRICE_ID=price_xxxxxx
STRIPE_COMBO_PROPLUS_YEARLY_PRICE_ID=price_yyyyyy
```

---

## ✅ Checklist final

- [ ] Créé 6 produits dans Stripe (3 Twitch + 3 Combo)
- [ ] Copié tous les **12 price IDs** (6 produits × 2 prix)
- [ ] Mis à jour `.env` avec les price IDs réels
- [ ] Redémarré le backend
- [ ] Testé un checkout (curl ou via l'UI)

---

## 💡 Tips

**Pour chaque produit :**
1. Clique sur **"Add product"** dans https://dashboard.stripe.com/products
2. Remplis "Product name" et "Description"
3. Sélectionne **"Recurring"**
4. Ajoute Price 1 (mensuel) avec Lookup key
5. Clique **"Add another price"** → Price 2 (annuel) avec Lookup key
6. Clique **"Save product"**
7. Copy les price IDs générés (format : `price_xxx`)

**Remarque :** Tu peux aussi utiliser le code EUR ou USD selon ta devise.

