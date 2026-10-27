#!/usr/bin/env python3
"""CLI securisee pour configurer la cle API Buffer.
Ne passe jamais le secret dans les arguments du processus.
"""
import argparse
import getpass
import sys
from pathlib import Path

# Path setup
sys.path.insert(0, str(Path(__file__).resolve().parent))
from secure_credentials import CredentialStore


def main():
    parser = argparse.ArgumentParser(description="Configuration cle API Buffer (securisee)")
    parser.add_argument("--import-file", metavar="PATH", default=None,
                        help="Importer la cle depuis un fichier local (la ligne de commande ne contient pas le secret)")
    parser.add_argument("--test-only", action="store_true",
                        help="Tester uniquement le DPAPI roundtrip sans stocker de cle reelle")
    args = parser.parse_args()

    print("=== Configuration cle API Buffer (securisee) ===")
    print("La cle sera chiffree avec DPAPI Windows (compte utilisateur courant).")
    print("Aucun fichier texte, aucun log, aucun argument de processus.")
    print("")

    store = CredentialStore()

    # If --import-file is used, read the key from the file securely
    if args.import_file:
        token_path = Path(args.import_file).resolve()
        if not token_path.exists():
            print(f"ERREUR: fichier non trouve: {token_path}")
            sys.exit(1)
        token = token_path.read_text(encoding="utf-8").strip()
        if len(token) < 10:
            print("ERREUR: cle trop courte.")
            sys.exit(1)
        print(f"Cle importee depuis fichier: {token_path}")
        print("Le secret n'a PAS transite par les arguments du processus Python.")
    elif args.test_only:
        token = None
        print("Mode TEST uniquement — aucune cle reelle ne sera stockee.")
    else:
        token = getpass.getpass("Cle API Buffer: ")
        if len(token) < 10:
            print("ERREUR: cle trop courte.")
            sys.exit(1)

    # If a vault already exists, verify it can be decrypted before overwriting
    if store.has("buffer_access_token"):
        print("Coffre existant detecte. Verification du dechiffrement...")
        try:
            existing = store.get("buffer_access_token")
            if existing:
                print(f"Coffre existant lisible. Longueur cle: {len(existing)} caracteres.")
                confirm = input("Ecraser le coffre existant ? (oui/NON): ")
                if confirm.lower() != "oui":
                    print("Annule.")
                    sys.exit(0)
            else:
                print("AVERTISSEMENT: coffre existant illisible (valeur vide).")
                confirm = input("Ecraser le coffre existant ? (oui/NON): ")
                if confirm.lower() != "oui":
                    print("Annule.")
                    sys.exit(0)
        except RuntimeError as e:
            print(f"AVERTISSEMENT: erreur de dechiffrement du coffre existant: {e}")
            confirm = input("Ecraser le coffre existant ? (oui/NON): ")
            if confirm.lower() != "oui":
                print("Annule.")
                sys.exit(0)
        except Exception as e:
            print(f"AVERTISSEMENT: erreur inattendue lors du dechiffrement: {e}")
            confirm = input("Ecraser le coffre existant ? (oui/NON): ")
            if confirm.lower() != "oui":
                print("Annule.")
                sys.exit(0)

    # Test roundtrip with a dummy value first
    test_key = "__dpapi_test__"
    test_value = "buffer_test_roundtrip_12345"
    try:
        store.set(test_key, test_value)
        retrieved = store.get(test_key)
        if retrieved != test_value:
            print("ERREUR: echec du test DPAPI roundtrip.")
            sys.exit(1)
        store.delete(test_key)
        print("Test DPAPI: PASS")
    except RuntimeError as e:
        print(f"ERREUR: test DPAPI echoue: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERREUR: test DPAPI echoue: {e}")
        sys.exit(1)

    if args.test_only:
        print("Mode test uniquement: aucune cle reelle stockee.")
        sys.exit(0)

    # Store the real token
    store.set("buffer_access_token", token)

    # Verify immediately
    verify = store.get("buffer_access_token")
    if verify == token:
        print("Cle stockee avec succes (chiffree DPAPI).")
        print(f"Longueur verifiee: {len(token)} caracteres.")
    else:
        print("ERREUR: verification du stockage echouee.")
        sys.exit(1)

    # Clear local variable
    token = None
    verify = None


if __name__ == '__main__':
    main()
