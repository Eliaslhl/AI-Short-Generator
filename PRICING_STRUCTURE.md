# 📊 Structure Tarifaire : YouTube + Twitch

## 📋 Vue d'ensemble

Le système de tarification est organisé en **trois catégories** :
1. **Plans YouTube seul** (accès à YouTube uniquement)
2. **Plans Twitch seul** (accès à Twitch uniquement)
3. **Packs combinés** (accès à YouTube + Twitch avec réduction)

Chaque utilisateur a **deux plans indépendants** :
- `plan_youtube` : FREE, STANDARD, PRO, PRO+
- `plan_twitch` : FREE, STANDARD, PRO, PRO+

### 🔑 Règles d'accès

| Situation | Accès YouTube | Accès Twitch |
|-----------|---------------|--------------|
| Abonnement YouTube uniquement | Plan payé | FREE |
| Abonnement Twitch uniquement | FREE | Plan payé |
| Pack combiné | Plan payé (même niveau) | Plan payé (même niveau) |
| Aucun abonnement | FREE | FREE |

---

## 💰 Grille tarifaire détaillée

### 📺 YOUTUBE PLANS

| Plan | Générations/mois | Clips/session | Concurrence | Prix mensuel | Prix annuel | ID Stripe (monthly) |
|------|------------------|--------------|-------------|--------------|------------|---------------------|
| FREE | 2 | Illimité | 1 | Gratuit | - | - |
| STANDARD | 20 | Illimité | 2 | 9.99€ | 99.99€ | price_yt_std_m |
| PRO | 50 | Illimité | 5 | 19.99€ | 199.99€ | price_yt_pro_m |
| PRO+ | 100 | Illimité | 10 | 29.99€ | 299.99€ | price_yt_proplus_m |

*Existants (à conserver et renommer)*
- STRIPE_STANDARD_MONTHLY_PRICE_ID=price_1T9TOzEjLhnJfUeo7r6bk5H3
- STRIPE_PRO_MONTHLY_PRICE_ID=price_1T9TPOEjLhnJfUeo8wr3XuPa
- STRIPE_PROPLUS_MONTHLY_PRICE_ID=price_1T9TQsEjLhnJfUeohPBAd8wD

---

### 🎮 TWITCH PLANS

| Plan | Générations/mois | Clips/session | Concurrence | Prix mensuel | Prix annuel | ID Stripe (monthly) |
|------|------------------|--------------|-------------|--------------|------------|---------------------|
| FREE | 2 | Illimité | 1 | Gratuit | - | - |
| STANDARD | 20 | Illimité | 2 | 9.99€ | 94.99€ | price_tw_std_m |
| PRO | 50 | Illimité | 5 | 29.99€ | 279.99€ | price_tw_pro_m |
| PRO+ | 100 | Illimité | 10 | 54.99€ | 529.99€ | price_tw_proplus_m |

*Variant B : Twitch agressif (prix supérieurs à YouTube pour refléter la valeur de streaming)*

---


### 📦 PACKS COMBINÉS (YouTube + Twitch) - Variant B

| Plan | Générations/mois | Accès | Prix mensuel | Prix annuel | Économie vs séparé | ID Stripe (monthly) |
|------|------------------|-------|--------------|------------|--------------------|---------------------|
| COMBO STANDARD | 20 chaque plateforme | YT + TW | 14.99€ | 129.99€ | ~ (9.99€ + 9.99€ + discount) | price_combo_std_m |
| COMBO PRO | 50 chaque plateforme | YT + TW | 39.99€ | 379.99€ | ~ (YT Pro + TW Pro - discount) | price_combo_pro_m |
| COMBO PRO+ | 100 chaque plateforme | YT + TW | 64.99€ | 649.99€ | ~ (YT Pro+ + TW Pro+ - discount) | price_combo_proplus_m |

**Exemples (approx) :**
- COMBO STANDARD ≈ 9.99€ (YT Standard) + 9.99€ (TW Standard) - 5.99€ (réduction) = 14.99€
- COMBO PRO ≈ 19.99€ (YT Pro) + 29.99€ (TW Pro) - 10.00€ (réduction) = 39.99€
- COMBO PRO+ ≈ 29.99€ (YT Pro+) + 54.99€ (TW Pro+) - 20.00€ (réduction) = 64.99€

---

## 🗂️ Modèle de données

### User Model (modifications)

```python
class User(Base):
    # EXISTING
    id: str
    email: str
    ...
    
    # ANCIEN MODELE (à remplacer)
    # plan: Plan = "free"  # YouTube par défaut
    
    # NOUVEAU MODELE
    plan_youtube: Plan = "free"      # Plan YouTube
    plan_twitch: Plan = "free"       # Plan Twitch
    subscription_type: str = "none"  # "none" | "youtube" | "twitch" | "combo"
    
    # Quotas mensuels (séparés par plateforme)
    youtube_generations_month: int = 0
    twitch_generations_month: int = 0
    
    youtube_reset_date: datetime = now()
    twitch_reset_date: datetime = now()
    
    # Stripe
    stripe_subscription_id: str | None  # Pour youtube
    stripe_subscription_id_twitch: str | None  # Pour twitch
```

### Mapping Stripe (nouveau)

```python
# YouTube plans
PRICE_TO_PLAN_YOUTUBE = {
    "price_1T9TOzEjLhnJfUeo7r6bk5H3": Plan.STANDARD,      # Existing
    "price_1T9TOzEjLhnJfUeoOd4Q6vIw": Plan.STANDARD,      # Yearly
    "price_1T9TPOEjLhnJfUeo8wr3XuPa": Plan.PRO,           # Existing
    "price_1T9TPxEjLhnJfUeoHQmyDdNT": Plan.PRO,           # Yearly
    "price_1T9TQsEjLhnJfUeohPBAd8wD": Plan.PROPLUS,       # Existing
    "price_1T9TREEjLhnJfUeoY8RkeQqG": Plan.PROPLUS,       # Yearly
}

# Twitch plans (à créer dans Stripe)
PRICE_TO_PLAN_TWITCH = {
    "price_tw_std_m": Plan.STANDARD,
    "price_tw_std_y": Plan.STANDARD,
    "price_tw_pro_m": Plan.PRO,
    "price_tw_pro_y": Plan.PRO,
    "price_tw_proplus_m": Plan.PROPLUS,
    "price_tw_proplus_y": Plan.PROPLUS,
}

# Packs combinés (à créer dans Stripe)
PRICE_TO_PLAN_COMBO = {
    "price_combo_std_m": (Plan.STANDARD, Plan.STANDARD),  # (YouTube, Twitch)
    "price_combo_std_y": (Plan.STANDARD, Plan.STANDARD),
    "price_combo_pro_m": (Plan.PRO, Plan.PRO),
    "price_combo_pro_y": (Plan.PRO, Plan.PRO),
    "price_combo_proplus_m": (Plan.PROPLUS, Plan.PROPLUS),
    "price_combo_proplus_y": (Plan.PROPLUS, Plan.PROPLUS),
}
```

---

## 🔐 Logique de vérification d'accès

### Vérifier si un utilisateur peut générer sur YouTube

```python
def can_generate_youtube(user: User) -> bool:
    # Reset du quota si nouveau mois
    if needs_monthly_reset(user.youtube_reset_date):
        user.youtube_generations_month = 0
        user.youtube_reset_date = now()
    
    limit = PLAN_LIMITS[user.plan_youtube]
    return user.youtube_generations_month < limit
```

### Vérifier si un utilisateur peut générer sur Twitch

```python
def can_generate_twitch(user: User) -> bool:
    # Reset du quota si nouveau mois
    if needs_monthly_reset(user.twitch_reset_date):
        user.twitch_generations_month = 0
        user.twitch_reset_date = now()
    
    limit = PLAN_LIMITS[user.plan_twitch]
    return user.twitch_generations_month < limit
```

### Obtenir le plan valide selon la plateforme

```python
def get_platform_plan(user: User, platform: str) -> Plan:
    if platform == "youtube":
        return user.plan_youtube  # Peut être "free" s'il n'a que Twitch payant
    elif platform == "twitch":
        return user.plan_twitch   # Peut être "free" s'il n'a que YouTube payant
    else:
        return Plan.FREE
```

---

## 🔄 Migration et transitions

### Pour les utilisateurs existants

**Option 1 : Duplication automatique**
- Utilisateurs avec YouTube payant → `plan_youtube = leur_plan_actuel` + `plan_twitch = FREE`
- Utilisateurs avec YouTube FREE → `plan_youtube = FREE` + `plan_twitch = FREE`

**Option 2 : Proposition de migration**
- Notification : "Twitch est disponible ! Voulez-vous ajouter Twitch à votre abonnement ?"
- Proposer les packs combinés avec économies

---

## 📝 Variables d'environnement (.env)

```bash
# YouTube Plans
STRIPE_YOUTUBE_STANDARD_MONTHLY_PRICE_ID=price_1T9TOzEjLhnJfUeo7r6bk5H3
STRIPE_YOUTUBE_STANDARD_YEARLY_PRICE_ID=price_1T9TOzEjLhnJfUeoOd4Q6vIw
STRIPE_YOUTUBE_PRO_MONTHLY_PRICE_ID=price_1T9TPOEjLhnJfUeo8wr3XuPa
STRIPE_YOUTUBE_PRO_YEARLY_PRICE_ID=price_1T9TPxEjLhnJfUeoHQmyDdNT
STRIPE_YOUTUBE_PROPLUS_MONTHLY_PRICE_ID=price_1T9TQsEjLhnJfUeohPBAd8wD
STRIPE_YOUTUBE_PROPLUS_YEARLY_PRICE_ID=price_1T9TREEjLhnJfUeoY8RkeQqG

# Twitch Plans (à créer)
STRIPE_TWITCH_STANDARD_MONTHLY_PRICE_ID=price_tw_std_m
STRIPE_TWITCH_STANDARD_YEARLY_PRICE_ID=price_tw_std_y
STRIPE_TWITCH_PRO_MONTHLY_PRICE_ID=price_tw_pro_m
STRIPE_TWITCH_PRO_YEARLY_PRICE_ID=price_tw_pro_y
STRIPE_TWITCH_PROPLUS_MONTHLY_PRICE_ID=price_tw_proplus_m
STRIPE_TWITCH_PROPLUS_YEARLY_PRICE_ID=price_tw_proplus_y

# Combo Packs (à créer)
STRIPE_COMBO_STANDARD_MONTHLY_PRICE_ID=price_combo_std_m
STRIPE_COMBO_STANDARD_YEARLY_PRICE_ID=price_combo_std_y
STRIPE_COMBO_PRO_MONTHLY_PRICE_ID=price_combo_pro_m
STRIPE_COMBO_PRO_YEARLY_PRICE_ID=price_combo_pro_y
STRIPE_COMBO_PROPLUS_MONTHLY_PRICE_ID=price_combo_proplus_m
STRIPE_COMBO_PROPLUS_YEARLY_PRICE_ID=price_combo_proplus_y
```

---

## ✅ À faire

- [ ] Créer les produits et prix dans Stripe (Twitch + Packs)
- [ ] Ajouter les nouveaux prix ID à `.env`
- [ ] Migrer le modèle User (YouTube + Twitch)
- [ ] Créer une migration BD (alembic)
- [ ] Mettre à jour la logique de vérification d'accès (`require_can_generate` → `require_can_generate_youtube/twitch`)
- [ ] Mettre à jour le webhook Stripe (gérer deux subscriptions)
- [ ] Frontend : afficher les deux plans séparément
- [ ] Tests : vérifier les quotas et accès par plateforme
