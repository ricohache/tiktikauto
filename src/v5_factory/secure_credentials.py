#!/usr/bin/env python3
"""Stockage securise de credentials via Windows DPAPI (CryptProtectData).
Aucune cle ne sort en clair dans les logs, les scripts ou les rapports.
"""
import ctypes
import ctypes.wintypes
import json
import os
import shutil
from pathlib import Path

# Windows DPAPI constants
CRYPTPROTECT_UI_FORBIDDEN = 0x01

class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", ctypes.wintypes.DWORD),
                ("pbData", ctypes.POINTER(ctypes.c_byte))]

def _encrypt_bytes(plaintext: bytes) -> bytes:
    """Chiffre des bytes avec DPAPI (compte utilisateur courant)."""
    blob_in = DATA_BLOB(len(plaintext), ctypes.cast(plaintext, ctypes.POINTER(ctypes.c_byte)))
    blob_out = DATA_BLOB()
    if not ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(blob_in), None, None, None, None, CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(blob_out)
    ):
        raise RuntimeError("CryptProtectData failed")
    size = blob_out.cbData
    data = bytes(ctypes.cast(blob_out.pbData, ctypes.POINTER(ctypes.c_byte * size)).contents)
    ctypes.windll.kernel32.LocalFree(blob_out.pbData)
    return data

def _decrypt_bytes(ciphertext: bytes) -> bytes:
    """Dechiffre des bytes avec DPAPI (compte utilisateur courant)."""
    blob_in = DATA_BLOB(len(ciphertext), ctypes.cast(ciphertext, ctypes.POINTER(ctypes.c_byte)))
    blob_out = DATA_BLOB()
    if not ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(blob_in), None, None, None, None, CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(blob_out)
    ):
        raise RuntimeError("CryptUnprotectData failed — le coffre est illisible pour ce compte utilisateur")
    size = blob_out.cbData
    data = bytes(ctypes.cast(blob_out.pbData, ctypes.POINTER(ctypes.c_byte * size)).contents)
    ctypes.windll.kernel32.LocalFree(blob_out.pbData)
    return data

class CredentialStore:
    """Stockage local chiffre pour le compte Windows courant."""

    def __init__(self, app_name: str = "TikTokHistoryFactory"):
        self.app_name = app_name
        self._store_dir = Path(os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))) / app_name
        self._store_dir.mkdir(parents=True, exist_ok=True)
        self._cred_file = self._store_dir / "credentials.bin"
        self._backup_file = self._store_dir / "credentials.bin.bak"
        self._tmp_file = self._store_dir / "credentials.bin.tmp"

    def _atomic_write(self, data: bytes) -> None:
        """Ecriture atomique avec backup."""
        # Backup existing vault before overwriting
        if self._cred_file.exists():
            shutil.copy2(str(self._cred_file), str(self._backup_file))
        # Write to temp then move
        self._tmp_file.write_bytes(data)
        shutil.move(str(self._tmp_file), str(self._cred_file))

    def _load_existing(self) -> dict:
        """Charge le coffre existant. En cas d'echec, leve une exception
        au lieu d'ecraser silencieusement."""
        if not self._cred_file.exists():
            return {}
        try:
            return json.loads(_decrypt_bytes(self._cred_file.read_bytes()).decode("utf-8"))
        except Exception as decrypt_err:
            # If a backup exists, try restoring it first
            if self._backup_file.exists():
                try:
                    backup_data = json.loads(_decrypt_bytes(self._backup_file.read_bytes()).decode("utf-8"))
                    # Restore backup to main vault
                    shutil.copy2(str(self._backup_file), str(self._cred_file))
                    return backup_data
                except Exception as backup_err:
                    raise RuntimeError(
                        f"Impossible de dechiffrer le coffre existant ({decrypt_err}) "
                        f"et le backup est egalement illisible ({backup_err}). "
                        "Restaurez manuellement depuis une sauvegarde externe ou supprimez les fichiers."
                    )
            raise RuntimeError(
                f"Impossible de dechiffrer le coffre existant ({decrypt_err}). "
                "Aucun backup disponible. Restaurez manuellement ou supprimez le fichier."
            )

    def set(self, key: str, value: str) -> None:
        """Stocke une valeur chiffree. Preserve les entrees existantes."""
        data = self._load_existing()
        data[key] = value
        encrypted = _encrypt_bytes(json.dumps(data).encode("utf-8"))
        self._atomic_write(encrypted)

    def get(self, key: str) -> str:
        """Recupere une valeur. Retourne chaine vide si absente."""
        if not self._cred_file.exists():
            return ""
        try:
            data = json.loads(_decrypt_bytes(self._cred_file.read_bytes()).decode("utf-8"))
            return data.get(key, "")
        except Exception:
            return ""

    def delete(self, key: str) -> None:
        """Supprime une entree."""
        if not self._cred_file.exists():
            return
        try:
            data = json.loads(_decrypt_bytes(self._cred_file.read_bytes()).decode("utf-8"))
        except Exception:
            return
        data.pop(key, None)
        if data:
            encrypted = _encrypt_bytes(json.dumps(data).encode("utf-8"))
            self._atomic_write(encrypted)
        else:
            self._cred_file.unlink(missing_ok=True)
            self._backup_file.unlink(missing_ok=True)
            self._tmp_file.unlink(missing_ok=True)

    def has(self, key: str) -> bool:
        return bool(self.get(key))

    def restore_backup(self) -> bool:
        """Restaure le coffre depuis le backup."""
        if self._backup_file.exists():
            shutil.copy2(str(self._backup_file), str(self._cred_file))
            return True
        return False

if __name__ == '__main__':
    store = CredentialStore()
    store.set("buffer_token_demo", "demo_value_12345")
    retrieved = store.get("buffer_token_demo")
    assert retrieved == "demo_value_12345", f"DPAPI roundtrip failed: {retrieved}"
    store.delete("buffer_token_demo")
    print("CredentialStore DPAPI roundtrip: PASS")
