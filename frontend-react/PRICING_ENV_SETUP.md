# Frontend Pricing Environment Setup

## Overview

Le frontend affiche maintenant **trois catégories de plans** : YouTube, Twitch et Combo Pack. Pour que les boutons "Upgrade" fonctionnent, il faut configurer les **Stripe Price IDs** dans le fichier `.env` du frontend.

## Setup Instructions

1. **Copier le fichier exemple** :
   ```bash
   cp frontend-react/.env.example frontend-react/.env.local
   ```

2. **Remplir les Price IDs YouTube** (déjà présents, vérifiez qu'ils correspondent) :
   ```
   REACT_APP_STRIPE_YOUTUBE_STANDARD_MONTHLY=price_1T9TOzEjLhnJfUeo7r6bk5H3
   REACT_APP_STRIPE_YOUTUBE_STANDARD_YEARLY=price_1T9TOzEjLhnJfUeoOd4Q6vIw
   REACT_APP_STRIPE_YOUTUBE_PRO_MONTHLY=price_1T9TPOEjLhnJfUeo8wr3XuPa
   REACT_APP_STRIPE_YOUTUBE_PRO_YEARLY=price_1T9TPxEjLhnJfUeoHQmyDdNT
   REACT_APP_STRIPE_YOUTUBE_PROPLUS_MONTHLY=price_1T9TQsEjLhnJfUeohPBAd8wD
   REACT_APP_STRIPE_YOUTUBE_PROPLUS_YEARLY=price_1T9TREEjLhnJfUeoY8RkeQqG
   ```

3. **Ajouter les Price IDs Twitch** (récupérez-les depuis votre dashboard Stripe ou le backend `.env`) :
   ```
   REACT_APP_STRIPE_TWITCH_STANDARD_MONTHLY=<Price ID from Stripe>
   REACT_APP_STRIPE_TWITCH_STANDARD_YEARLY=<Price ID from Stripe>
   REACT_APP_STRIPE_TWITCH_PRO_MONTHLY=<Price ID from Stripe>
   REACT_APP_STRIPE_TWITCH_PRO_YEARLY=<Price ID from Stripe>
   ```

4. **Ajouter les Price IDs Combo Pack** (récupérez-les depuis votre dashboard Stripe) :
   ```
   REACT_APP_STRIPE_COMBO_PRO_MONTHLY=<Price ID from Stripe>
   REACT_APP_STRIPE_COMBO_PRO_YEARLY=<Price ID from Stripe>
   ```

## Finding Price IDs in Stripe

1. Allez sur **Stripe Dashboard** → **Products**
2. Trouvez chaque produit (YouTube Standard, YouTube Pro, Twitch Standard, Twitch Pro, Combo Pro)
3. Cliquez sur le produit → voir les **Prices**
4. Copiez le **Price ID** pour chaque variante (Monthly/Yearly)

## Testing

- Lancez le frontend en dev : `npm run dev`
- Allez à **http://localhost:5173/#pricing**
- Testez les onglets **YouTube** / **Twitch** / **Combo Pack**
- Vérifiez que les prix s'affichent correctement
- Testez les boutons "Upgrade" (si vous êtes logged in, vous devez être redirigé vers Stripe Checkout)

## Notes

- Les variables d'env frontend doivent commencer par `REACT_APP_` pour que Vite les expose
- Si une Price ID est vide/manquante, l'app affichera une alerte lors du clic sur "Upgrade"
- Vérifiez que les Price IDs du frontend correspondent exactement avec ceux du backend `.env` pour la cohérence

## Backend Mapping

Le backend a les mêmes price IDs dans son `.env` :
- `STRIPE_YOUTUBE_STANDARD_MONTHLY_PRICE_ID`
- `STRIPE_TWITCH_PRO_MONTHLY_PRICE_ID`
- `STRIPE_COMBO_PRO_MONTHLY_PRICE_ID`
- etc.

Assurez-vous que les IDs sont **identiques** partout (backend + frontend) pour éviter les erreurs lors du webhook.
