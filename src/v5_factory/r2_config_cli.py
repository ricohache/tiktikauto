#!/usr/bin/env python3
"""CLI securisee pour configurer les credentials Cloudflare R2.
Ne passe jamais les secrets dans les arguments du processus.
Ne jamais afficher les secrets, meme partiellement.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from secure_credentials import CredentialStore


def _next_non_empty(lines: list, start_idx: int) -> tuple:
    """Retourne (index, valeur) de la prochaine ligne non vide."""
    for i in range(start_idx, len(lines)):
        val = lines[i].strip()
        if val and not val.startswith("Click"):
            return i, val
    return -1, ""


def parse_r2_token_file(token_path: Path) -> dict:
    """Parse le fichier de token Cloudflare R2 et extrait les credentials S3.
    Ne retourne jamais de valeurs vides sans lever une exception.
    """
    content = token_path.read_text(encoding="utf-8")
    lines = [l.rstrip() for l in content.splitlines()]
    
    result = {
        "access_key_id": None,
        "secret_access_key": None,
        "endpoint_url": None,
        "bucket_name": None,
    }
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("tiktokhistoryfactory"):
            result["bucket_name"] = stripped
            break
    
    for i, line in enumerate(lines):
        if "Access Key ID" in line:
            _, candidate = _next_non_empty(lines, i + 1)
            if candidate:
                result["access_key_id"] = candidate
                break
    
    for i, line in enumerate(lines):
        if "Secret Access Key" in line:
            _, candidate = _next_non_empty(lines, i + 1)
            if candidate:
                result["secret_access_key"] = candidate
                break
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("https://") and "r2.cloudflarestorage" in stripped:
            result["endpoint_url"] = stripped
            break
    
    missing = [k for k, v in result.items() if v is None]
    if missing:
        raise ValueError(f"Champs manquants dans le fichier token: {missing}")
    
    return result


def _validate_credentials(creds: dict) -> list:
    """Valide les credentials sans divulguer leur contenu.
    Retourne une liste d'erreurs (vide si tout est valide).
    """
    errors = []
    if not creds.get("access_key_id") or len(creds["access_key_id"]) < 10:
        errors.append("Access Key ID invalide (trop court ou absent)")
    if not creds.get("secret_access_key") or len(creds["secret_access_key"]) < 10:
        errors.append("Secret Access Key invalide (trop court ou absent)")
    if not creds.get("endpoint_url") or "r2.cloudflarestorage" not in creds["endpoint_url"]:
        errors.append("Endpoint URL invalide (doit contenir r2.cloudflarestorage)")
    if not creds.get("bucket_name"):
        errors.append("Bucket name invalide (absent)")
    return errors


def main():
    parser = argparse.ArgumentParser(description="Configuration credentials Cloudflare R2 (securisee)")
    parser.add_argument("--import-file", metavar="PATH", default=None,
                        help="Importer les credentials depuis un fichier local")
    parser.add_argument("--test-only", action="store_true",
                        help="Tester uniquement le parsing sans stocker")
    args = parser.parse_args()

    print("=== Configuration Cloudflare R2 (securisee) ===")
    print("Les credentials seront chiffres avec DPAPI Windows.")
    print("Aucun secret dans les arguments, logs ou rapports.")
    print("")

    if not args.import_file:
        print("ERREUR: utilisez --import-file PATH pour specifier le fichier token R2.")
        sys.exit(1)

    token_path = Path(args.import_file).resolve()
    if not token_path.exists():
        print(f"ERREUR: fichier non trouve: {token_path}")
        sys.exit(1)

    # Parse token file
    try:
        creds = parse_r2_token_file(token_path)
    except ValueError as e:
        print(f"ERREUR: {e}")
        sys.exit(1)

    # Validate without exposing values
    validation_errors = _validate_credentials(creds)
    if validation_errors:
        print(f"ERREUR: validation echouee:")
        for err in validation_errors:
            print(f"  - {err}")
        sys.exit(1)

    print(f"Fichier parse: {token_path}")
    print("Validation: OK")
    print("Aucun secret affiche.")

    if args.test_only:
        print("\nMode TEST uniquement: aucun credential stocke.")
        sys.exit(0)

    # Store in DPAPI
    store = CredentialStore()
    
    # DPAPI roundtrip test first (dummy value, not real secret)
    test_key = "__dpapi_r2_test__"
    test_val = "r2_test_roundtrip_12345"
    try:
        store.set(test_key, test_val)
        retrieved = store.get(test_key)
        if retrieved != test_val:
            print("ERREUR: echec du test DPAPI roundtrip.")
            sys.exit(1)
        store.delete(test_key)
        print("\nTest DPAPI: PASS")
    except Exception as e:
        print(f"ERREUR: test DPAPI echoue: {e}")
        sys.exit(1)

    # Store R2 credentials
    store.set("r2_access_key_id", creds["access_key_id"])
    store.set("r2_secret_access_key", creds["secret_access_key"])
    store.set("r2_endpoint_url", creds["endpoint_url"])
    store.set("r2_bucket_name", creds["bucket_name"])

    # Verify persistence (compare without exposing values)
    key_map = {
        "r2_access_key_id": "access_key_id",
        "r2_secret_access_key": "secret_access_key",
        "r2_endpoint_url": "endpoint_url",
        "r2_bucket_name": "bucket_name",
    }
    errors = []
    for r2_key, cred_key in key_map.items():
        val = store.get(r2_key)
        expected = creds[cred_key]
        if val != expected:
            errors.append(r2_key)
    
    if errors:
        print(f"ERREUR: verification echouee pour: {errors}")
        sys.exit(1)
    
    print("\nCredentials R2 stockes avec succes (chiffres DPAPI).")
    print("  r2_access_key_id:     OK (hidden)")
    print("  r2_secret_access_key: OK (hidden)")
    print("  r2_endpoint_url:      OK (hidden)")
    print(f"  r2_bucket_name:       OK ({creds['bucket_name']})")
    print("\nAucun conflit avec la cle Buffer existante.")

    # Clear local variables
    creds = None


if __name__ == '__main__':
    main()
