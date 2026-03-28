# 📌 Instructions : Créer les produits Stripe pour Twitch et Combo

## 📍 Vue d'ensemble

Tu dois créer **6 nouveaux produits** dans Stripe :
1. **Twitch Standard** (STANDARD, PRO, PRO+) = 3 produits
2. **Twitch Pro et Pro+** 
3. **Packs Combo** (STANDARD, PRO, PRO+) = 3 produits

Chaque produit aura **2 prix** : mensuel et annuel.

---

## 🔑 Accès Stripe Dashboard

1. Va sur https://dashboard.stripe.com
2. Authentifie-toi avec tes identifiants
3. Navigue vers **Products** (dans le menu latéral)

---

## 🎮 Créer les produits TWITCH

### 1️⃣ Produit : Twitch Standard

**Détails du produit :**
- Nom : `Twitch Standard`
- Description : `20 generations/month - Unlimited clips per session - Single concurrent generation`
- Type : `Recurring`
- Taxable : `Oui` (si applicable)

**Prix mensuels :**
- **Price 1 (mensuel)** :
  - Billing period : Monthly
  - Price : 12.99€ (ou $12.99 selon ta devise)
  - Recurring : Oui
  - Lookup key (optionnel) : `price_tw_std_m`

- **Price 2 (annuel)** :
  - Billing period : Yearly
  - Price : 129.99€ (ou $129.99)
  - Recurring : Oui
  - Lookup key (optionnel) : `price_tw_std_y`

**Après création :**
- Copie les deux price IDs (ex : `price_xxx` et `price_yyy`)
- Ajoute-les à `.env` :
  ```bash
  STRIPE_TWITCH_STANDARD_MONTHLY_PRICE_ID=price_xxx
  STRIPE_TWITCH_STANDARD_YEARLY_PRICE_ID=price_yyy
  ```

---

### 2️⃣ Produit : Twitch Pro

**Détails du produit :**
- Nom : `Twitch Pro`
- Description : `50 generations/month - Unlimited clips per session - 5 concurrent generations`
- Type : `Recurring`

**Prix :**
- **Mensuel** : 24.99€ → Lookup key : `price_tw_pro_m`
- **Annuel** : 249.99€ → Lookup key : `price_tw_pro_y`

**Ajoute à `.env` :**
```bash
STRIPE_TWITCH_PRO_MONTHLY_PRICE_ID=price_xxx
STRIPE_TWITCH_PRO_YEARLY_PRICE_ID=price_yyy
```

---

### 3️⃣ Produit : Twitch Pro+

**Détails du produit :**
- Nom : `Twitch Pro+`
- Description : `100 generations/month - Unlimited clips per session - 10 concurrent generations`
- Type : `Recurring`

**Prix :**
- **Mensuel** : 34.99€ → Lookup key : `price_tw_proplus_m`
- **Annuel** : 349.99€ → Lookup key : `price_tw_proplus_y`

**Ajoute à `.env` :**
```bash
STRIPE_TWITCH_PROPLUS_MONTHLY_PRICE_ID=price_xxx
STRIPE_TWITCH_PROPLUS_YEARLY_PRICE_ID=price_yyy
```

---

## 📦 Créer les produits COMBO (YouTube + Twitch)

### 4️⃣ Produit : Combo Standard

**Détails du produit :**
- Nom : `Combo Standard (YouTube + Twitch)`
- Description : `YouTube + Twitch - 20 generations/month each platform - Save 2.99€/month!`
- Type : `Recurring`

**Prix :**
- **Mensuel** : 19.99€ → Lookup key : `price_combo_std_m`
- **Annuel** : 199.99€ → Lookup key : `price_combo_std_y`

**Ajoute à `.env` :**
```bash
STRIPE_COMBO_STANDARD_MONTHLY_PRICE_ID=price_xxx
STRIPE_COMBO_STANDARD_YEARLY_PRICE_ID=price_yyy
```

---

### 5️⃣ Produit : Combo Pro

**Détails du produit :**
- Nom : `Combo Pro (YouTube + Twitch)`
- Description : `YouTube + Twitch - 50 generations/month each platform - Save 4.99€/month!`
- Type : `Recurring`

**Prix :**
- **Mensuel** : 39.99€ → Lookup key : `price_combo_pro_m`
- **Annuel** : 399.99€ → Lookup key : `price_combo_pro_y`

**Ajoute à `.env` :**
```bash
STRIPE_COMBO_PRO_MONTHLY_PRICE_ID=price_xxx
STRIPE_COMBO_PRO_YEARLY_PRICE_ID=price_yyy
```

---

### 6️⃣ Produit : Combo Pro+

**Détails du produit :**
- Nom : `Combo Pro+ (YouTube + Twitch)`
- Description : `YouTube + Twitch - 100 generations/month each platform - Save 9.99€/month!`
- Type : `Recurring`

**Prix :**
- **Mensuel** : 54.99€ → Lookup key : `price_combo_proplus_m`
- **Annuel** : 549.99€ → Lookup key : `price_combo_proplus_y`

**Ajoute à `.env` :**
```bash
STRIPE_COMBO_PROPLUS_MONTHLY_PRICE_ID=price_xxx
STRIPE_COMBO_PROPLUS_YEARLY_PRICE_ID=price_yyy
```

---

## 📊 Récapitulatif des price IDs à récupérer

| Produit | Mensuel | Annuel |
|---------|---------|--------|
| Twitch Standard | `price_tw_std_m` | `price_tw_std_y` |
| Twitch Pro | `price_tw_pro_m` | `price_tw_pro_y` |
| Twitch Pro+ | `price_tw_proplus_m` | `price_tw_proplus_y` |
| Combo Standard | `price_combo_std_m` | `price_combo_std_y` |
| Combo Pro | `price_combo_pro_m` | `price_combo_pro_y` |
| Combo Pro+ | `price_combo_proplus_m` | `price_combo_proplus_y` |

**À remplacer dans `.env`** par les vrais price IDs de Stripe (format : `price_xxx`).

---

## ✅ Après avoir créé les produits

1. **Mets à jour `.env`** avec tous les price IDs
2. **Redémarre le backend** pour charger les nouvelles configurations
3. **Teste** : appelle les endpoints de checkout pour vérifier que Stripe accepte les nouveaux prix
4. **Mets à jour le frontend** pour afficher les 3 catégories (YouTube, Twitch, Combo) dans la page pricing

---

## 🔗 Ressources

- Stripe Dashboard: https://dashboard.stripe.com
- Docs Stripe Products: https://stripe.com/docs/products-prices
- Docs Stripe Python SDK: https://stripe.com/docs/libraries/python
