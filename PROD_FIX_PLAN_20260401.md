# URGENT PROD FIX — Plan d'action complet

## Problème
- La colonne `users.plan` est `NOT NULL` en prod PostgreSQL **sans server default**
- Lors de créations d'users via Google OAuth, l'INSERT omet `plan` → NotNullViolationError
- Alembic signale "Multiple head revisions" → migrations bloquées

## Solution déployée (2 parties)

### Partie 1 : Code hotfix (backend/auth/router.py)
✓ DÉJÀ APPLIQUÉ — L'INSERT brut Google OAuth inclut maintenant `plan='free'`

### Partie 2 : Migration Alembic pour prod (NOUVEAU)
✓ CRÉÉE — File: `alembic/versions/20260401_fix_plan_not_null_and_merge_heads.py`
- Ajoute server default `'free'` à la colonne `plan`
- Fusionne les heads divergents (rev20260330b + la nouvelle)
- Résout "Multiple head revisions" error

---

## Étapes de déploiement EN PROD

### 1. Push le code fixé
```bash
git add backend/auth/router.py alembic/versions/20260401_fix_plan_not_null_and_merge_heads.py
git commit -m "URGENT: Fix plan NOT NULL + resolve Alembic heads"
git push origin main
```

### 2. Dans le conteneur/déploiement prod, exécuter les migrations
```bash
# Vérifier les heads (doit montrer 1 seul: rev20260401_fix_plan)
.venv/bin/alembic heads

# Appliquer les migrations jusqu'au dernier head
.venv/bin/alembic upgrade head
# Ou spécifiquement:
.venv/bin/alembic upgrade rev20260401_fix_plan
```

### 3. Vérifier l'état appliqué
```bash
.venv/bin/alembic current
# Doit afficher: rev20260401_fix_plan
```

### 4. Vérifier le server default en DB
```sql
-- Connexion à prod PostgreSQL
psql "$DATABASE_URL"

-- Vérifier que plan a un server default
\d users
-- Doit afficher: plan | plan | default 'free'::plan | ...

-- Ou interroger directement:
SELECT column_name, column_default, is_nullable
FROM information_schema.columns
WHERE table_name = 'users' AND column_name = 'plan';
-- Doit afficher: plan | 'free'::plan | NO
```

### 5. Test fonctionnel
- Essayer de se connecter via Google OAuth en prod
- Un nouvel utilisateur devrait être créé avec `plan='free'`
- Pas d'erreur 502 ni NotNullViolation

---

## Résumé des changements

| Fichier | Changement |
|---------|-----------|
| `backend/auth/router.py` | INSERT brut inclut `plan='free'` |
| `alembic/versions/20260401_fix_plan_not_null_and_merge_heads.py` | CRÉÉ — migrations Alembic + server default |

---

## Vérification locale (optionnel, pour dev/staging)
Si vous avez un PostgreSQL local, testez:
```bash
# 1. Démarrer un conteneur Postgres local (optionnel)
docker run --rm -e POSTGRES_PASSWORD=test -p 5432:5432 postgres:15

# 2. Modifier .env pour pointer sur le local:
# DATABASE_URL=postgresql://postgres:test@localhost:5432/postgres

# 3. Exécuter les migrations
source .venv/bin/activate
.venv/bin/alembic upgrade head

# 4. Vérifier le résultat
psql postgresql://postgres:test@localhost:5432/postgres -c "\d users"
# ou:
psql postgresql://postgres:test@localhost:5432/postgres -c "SELECT column_default FROM information_schema.columns WHERE table_name='users' AND column_name='plan';"
```

---

## FAQ / Dépannage

**Q: Après `upgrade head`, toujours "Multiple head revisions"?**
A: Vous aviez peut-être des révisions orphelines. Vérifiez `alembic history` et assurez-vous que le HEAD commit inclut la nouvelle migration.

**Q: Erreur "Can't locate revision"?**
A: Vous pointez sur une DB avec un historique Alembic partiellement syndiqué. Faites `alembic stamp rev20260401_fix_plan` une fois pour re-synchroniser.

**Q: Google OAuth crée toujours pas correctement après déploiement?**
A: Redémarrez le conteneur pour recharger les env vars et le code. Vérifiez les logs pour voir si l'INSERT s'exécute maintenant sans erreur.

---

Déployez ces 2 changements (code + migration) et tout devrait être rétabli ! 🚀
