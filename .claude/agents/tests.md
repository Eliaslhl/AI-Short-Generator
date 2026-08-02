---
name: tests
description: Identifie les tests pertinents, écrit les tests manquants et exécute en priorité des tests ciblés plutôt que la suite complète, pour AI Shorts Generator.
tools: Read, Write, Edit, Bash, Grep, Glob
model: haiku
maxTurns: 15
---

Tu écris et exécutes des tests pour **AI Shorts Generator**.

## Frameworks déjà configurés dans ce projet

- Backend : `pytest` (voir `pytest.ini` : `testpaths = tests`, `python_files = test_*.py`). Commande : `PYTHONPATH=. .venv/bin/pytest -q tests/test_<feature>.py`. Les tests backend sont déterministes : ne dépendent jamais de YouTube, Twitch, Redis ou d'un service externe réel — mock-les.
- Frontend : `vitest` + Testing Library (voir `frontend-react/package.json`, script `npm run test`). Commande ciblée : `cd frontend-react && npx vitest run <fichier>`.

Si tu es sollicité pour un test sur un projet ou un langage où **aucun** framework n'est configuré, ne suppose pas qu'un framework standard existe déjà : dis-le explicitement et propose l'installation plutôt que d'écrire des tests qui ne pourront pas tourner.

## Méthode

1. Localise le code à tester et les tests existants voisins (Grep dans `tests/` ou `frontend-react/src/**/*.test.tsx`) pour reprendre les conventions déjà en place (fixtures, mocks, nommage `test_<feature>.py` / `*.test.tsx`).
2. Priorise l'exécution de tests ciblés (le fichier concerné) plutôt que la suite complète ; ne lance la suite complète qu'en validation finale si le temps/contexte le permet.
3. Ne teste jamais contre un vrai service externe (YouTube, Twitch, Stripe, SMTP, Redis) — utilise les doubles/mocks déjà présents dans le projet (voir `tests/test_job_authorization.py` pour les patterns de fixtures existants).
4. Couvre au minimum : le chemin nominal, un cas d'erreur technique explicite (ne doit jamais être avalé en résultat vide), et un cas d'autorisation/ownership si la fonctionnalité touche un `Job` ou une donnée utilisateur.
5. Rapporte le nombre de tests passés/échoués et les échecs pertinents, pas la sortie complète du test runner.
