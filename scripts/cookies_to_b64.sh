#!/usr/bin/env bash
# Petit utilitaire pour convertir cookies.txt en exportable YOUTUBE_COOKIES_B64
# Usage: ./scripts/cookies_to_b64.sh /chemin/vers/cookies.txt
set -euo pipefail
if [ "$#" -ne 1 ]; then
  echo "Usage: $0 /path/to/cookies.txt"
  exit 2
fi
FILE="$1"
if [ ! -f "$FILE" ]; then
  echo "Fichier introuvable: $FILE"
  exit 2
fi
if command -v base64 >/dev/null 2>&1; then
  # -w0 to avoid line wraps; on macOS use -b0 is not available, so fallback to python
  if base64 --help 2>&1 | grep -q -- '-w'; then
    B64=$(base64 -w0 "$FILE")
  else
    B64=$(python3 -c 'import base64,sys;print(base64.b64encode(open(sys.argv[1],"rb").read()).decode())' "$FILE")
  fi
  echo "Exportez ensuite dans votre shell:"
  echo
  echo "export YOUTUBE_COOKIES_B64=\"$B64\""
else
  echo "La commande base64 n'est pas disponible." >&2
  exit 1
fi
