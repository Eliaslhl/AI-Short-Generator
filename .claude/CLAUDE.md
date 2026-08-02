# AI Shorts Generator — notes pour l'assistant

## Graphify

`/graphify` utilise le skill Graphify installé globalement (`~/.claude/skills/graphify/SKILL.md`, package PyPI `graphifyy`). Il transforme le projet courant en graphe de connaissances interrogeable (`graphify query "..."`) plutôt que de relire le dépôt en entier. Deux hooks `PreToolUse` dans `.claude/settings.json` (`graphify hook-guard search` sur `Bash|Grep`, `graphify hook-guard read` sur `Read|Glob`) suggèrent d'utiliser le graphe existant quand il est disponible et à jour ; ils ne bloquent jamais un appel légitime (fail-open).
