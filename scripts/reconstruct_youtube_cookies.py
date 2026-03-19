#!/usr/bin/env python3
"""
Reconstruire un fichier de cookies YouTube à partir des variables d'environnement
ou d'un fichier base64 de secours. Écrit le fichier décodé et affiche size + sha256.

Usage:
  python3 scripts/reconstruct_youtube_cookies.py [--output /tmp/youtube_cookies.txt]

Comportement:
 - Cherche les variables d'env YOUTUBE_COOKIES_B64_PART_1..N
 - Si aucune, utilise YOUTUBE_COOKIES_B64
 - Si aucune, tente de lire `secrets/youtube_cookies.b64` dans le repo
 - Nettoie chaque part (trim, supprime guillemets et préfixe base64:)
 - Détecte les chaînes hex (probable hachage) et échoue proprement
 - Écrit le fichier décodé et imprime size + sha256
"""

import os
import sys
import argparse
import base64
import hashlib


def gather_parts_from_env():
    # Collecte les variables YOUTUBE_COOKIES_B64_PART_<n> triées numériquement
    parts = []
    keys = [k for k in os.environ.keys() if k.startswith("YOUTUBE_COOKIES_B64_PART_")]
    if not keys:
        return None
    try:
        keys_sorted = sorted(keys, key=lambda x: int(x.rsplit("_", 1)[1]))
    except Exception:
        keys_sorted = sorted(keys)
    for k in keys_sorted:
        v = os.environ.get(k, "")
        parts.append(v)
    return parts


def sanitize_part(s: str) -> str:
    if s is None:
        return ""
    s = s.strip()
    # retire guillemets entourants
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        s = s[1:-1]
    # retire prefixe optionnel
    if s.startswith("base64:"):
        s = s.split(":", 1)[1]
    # supprime whitespace/newlines intérieurs
    return "".join(s.split())


def looks_like_hex(s: str) -> bool:
    # considère hex si longueur > 16 et uniquement [0-9a-fA-F]
    ss = s.strip().replace(" ", "")
    if len(ss) < 16:
        return False
    try:
        int(ss, 16)
        return True
    except Exception:
        return False


def decode_base64_concat(parts):
    concat = "".join(sanitize_part(p) for p in parts if p)
    if not concat:
        return None, "NO_PARTS"
    # early hex detection
    if looks_like_hex(concat):
        return None, "PROBABLY_HEX"
    try:
        data = base64.b64decode(concat, validate=True)
        return data, None
    except Exception:
        # fallback: try to be permissive (ignore padding/newline issues)
        try:
            data = base64.b64decode(concat + "=", validate=False)
            return data, None
        except Exception as e:
            return None, str(e)


def read_fallback_b64_file(path: str):
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        raw = f.read()
    # convert bytes to str and strip
    try:
        s = raw.decode('utf-8')
    except Exception:
        # if already binary b64 with newlines, try to base64-decode directly
        s = None
    if s is not None:
        s = "".join(s.split())
    return s


def write_output(path: str, data: bytes):
    with open(path, "wb") as f:
        f.write(data)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description="Reconstruire youtube cookies depuis env parts or fallback file")
    parser.add_argument("--output", "-o", default="/tmp/youtube_cookies.txt",
                        help="Chemin de sortie pour le fichier de cookies décodé")
    parser.add_argument("--fallback", "-f", default="secrets/youtube_cookies.b64",
                        help="Fichier fallback .b64 à lire si pas de variables d'env")
    args = parser.parse_args()

    parts = gather_parts_from_env()
    data = None
    reason = None

    if parts:
        data, reason = decode_base64_concat(parts)
        if data is None:
            print(f"ERROR: décodage depuis variables d'env failed: {reason}")
    else:
        # try single env var
        single = os.environ.get("YOUTUBE_COOKIES_B64")
        if single:
            data, reason = decode_base64_concat([single])
            if data is None:
                print(f"ERROR: décodage depuis YOUTUBE_COOKIES_B64 failed: {reason}")
        else:
            # fallback file
            fb = read_fallback_b64_file(args.fallback)
            if fb:
                try:
                    data = base64.b64decode(fb)
                except Exception as e:
                    print(f"ERROR: décodage fallback file failed: {e}")
                    data = None
            else:
                print("ERROR: aucune variable d'environnement trouvée et fallback file introuvable")

    if data is None:
        print("Aucun fichier de cookies écrit.")
        sys.exit(2)

    write_output(args.output, data)
    print(f"WROTE {args.output} size= {len(data)} sha256= {sha256_hex(data)}")


if __name__ == '__main__':
    main()
