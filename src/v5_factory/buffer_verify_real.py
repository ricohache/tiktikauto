#!/usr/bin/env python3
"""Verification reelle Buffer API — lecture seule, aucune publication.
Ce script utilise la cle deja stockee dans DPAPI (pas de re-import).
Affiche uniquement les statuts, identifiants non secrets et erreurs utiles.
Ne jamais afficher NO lorsqu'une erreur GraphQL empeche la verification.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from secure_credentials import CredentialStore
from buffer_adapter import BufferAdapter


def main():
    print("=== Buffer API Real Verification (Read-Only) ===")
    print("Token source: DPAPI vault (already stored)")
    
    store = CredentialStore()
    token = store.get("buffer_access_token")
    if not token:
        print("ERROR: No token found in DPAPI vault.")
        sys.exit(1)
    print(f"Token retrieved from DPAPI: OK ({len(token)} chars)")
    
    buf = BufferAdapter(token)
    token = None
    
    # 1. AUTH
    print("\n[1/3] GraphQL: account...")
    auth = buf.verify_auth()
    
    if auth.get("status") in ("HTTP_ERROR", "NETWORK_ERROR", "API_ERROR"):
        print(f"AUTH FAILED: {auth.get('status')}")
        print("\n" + "="*50)
        print("SUMMARY")
        print("="*50)
        print("AUTH:               ERROR")
        print("ORGANIZATION:       UNKNOWN")
        print("CHANNEL_COUNT_EXP:  UNKNOWN")
        print("CHANNELS_FOUND:     UNKNOWN")
        print("TIKTOK_CHANNEL_ID:  UNKNOWN")
        print("TIKTOK_CONNECTED:   UNKNOWN")
        print("CHANNEL_DISCONNECTED: UNKNOWN")
        print("CHANNEL_LOCKED:     UNKNOWN")
        print("="*50)
        sys.exit(1)
    
    if "errors" in auth:
        print(f"AUTH GraphQL ERRORS: {auth['errors']}")
        print("\n" + "="*50)
        print("SUMMARY")
        print("="*50)
        print("AUTH:               ERROR")
        print("ORGANIZATION:       UNKNOWN")
        print("CHANNEL_COUNT_EXP:  UNKNOWN")
        print("CHANNELS_FOUND:     UNKNOWN")
        print("TIKTOK_CHANNEL_ID:  UNKNOWN")
        print("TIKTOK_CONNECTED:   UNKNOWN")
        print("CHANNEL_DISCONNECTED: UNKNOWN")
        print("CHANNEL_LOCKED:     UNKNOWN")
        print("="*50)
        sys.exit(1)
    
    account = auth.get("data", {}).get("account", {})
    orgs = account.get("organizations", [])
    print(f"Account ID: {account.get('id', '?')[:8]}...")
    print(f"Organizations: {len(orgs)}")
    
    if not orgs:
        print("ERROR: No organizations found.")
        print("\n" + "="*50)
        print("SUMMARY")
        print("="*50)
        print("AUTH:               OK")
        print("ORGANIZATION:       NONE")
        print("CHANNEL_COUNT_EXP:  N/A")
        print("CHANNELS_FOUND:     N/A")
        print("TIKTOK_CHANNEL_ID:  UNKNOWN")
        print("TIKTOK_CONNECTED:   UNKNOWN")
        print("="*50)
        sys.exit(1)
    
    org = orgs[0]
    org_id = org.get("id")
    org_name = org.get("name", "?")
    channel_count_expected = org.get("channelCount")
    print(f"Organization: {org_name} (id={org_id[:8]}...)")
    print(f"ChannelCount (expected): {channel_count_expected if channel_count_expected is not None else 'N/A'}")
    
    # 2. CHANNELS
    print(f"\n[2/3] GraphQL: channels(input: {{organizationId: ...}})...")
    channels = buf.list_channels(org_id)
    
    channels_error = None
    if channels and channels[0].get("_error"):
        channels_error = channels[0]["_error"]
        print(f"CHANNELS ERROR: {channels_error}")
        channels = []
    else:
        print(f"Channels returned: {len(channels)}")
        for ch in channels:
            svc = ch.get('service', '?')
            name = ch.get('name', '?')
            cid = ch.get('id', '?')
            disc = ch.get('isDisconnected', '?')
            locked = ch.get('isLocked', '?')
            print(f"  - {svc}: {name} (id={cid[:8]}..., disconnected={disc}, locked={locked})")
    
    # 3. TIKTOK CHANNEL
    print("\n[3/3] GraphQL: TikTok channel...")
    tiktok = buf.get_tiktok_channel(org_id)
    
    tiktok_error = None
    tiktok_id = None
    tiktok_connected = "UNKNOWN"
    tiktok_disconnected = "UNKNOWN"
    tiktok_locked = "UNKNOWN"
    
    if tiktok and tiktok.get("_error"):
        tiktok_error = tiktok["_error"]
        print(f"TIKTOK ERROR: {tiktok_error}")
    elif tiktok:
        tiktok_id = tiktok.get("id", "")
        tiktok_disconnected = tiktok.get("isDisconnected")
        tiktok_locked = tiktok.get("isLocked")
        print(f"TikTok channel FOUND: {tiktok.get('name', '?')} (id={tiktok_id[:8]}...)")
        print(f"  Disconnected: {tiktok_disconnected}")
        print(f"  Locked: {tiktok_locked}")
        tiktok_connected = "YES"
    else:
        if channels_error:
            print("TikTok channel: UNKNOWN (channels query failed)")
        else:
            print("TikTok channel: NOT FOUND (no tiktok service in channels)")
            tiktok_connected = "NO"
    
    # FINAL SUMMARY
    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50)
    print(f"AUTH:               OK (account={account.get('id', '?')[:8]}...)")
    print(f"ORGANIZATION:       {org_name} (id={org_id[:8]}...)")
    print(f"CHANNEL_COUNT_EXP:  {channel_count_expected if channel_count_expected is not None else 'N/A'}")
    print(f"CHANNELS_FOUND:     {len(channels) if not channels_error else 'ERROR'}")
    print(f"TIKTOK_CHANNEL_ID:  {tiktok_id[:8] + '...' if tiktok_id else ('ERROR' if tiktok_error else 'NOT FOUND')}")
    print(f"TIKTOK_CONNECTED:   {tiktok_connected}")
    print(f"CHANNEL_DISCONNECTED: {tiktok_disconnected}")
    print(f"CHANNEL_LOCKED:     {tiktok_locked}")
    print("="*50)
    
    # Log to SQLite
    try:
        buf.log_buffer_check("real-verify-run", org_id, {
            "auth": "ok",
            "organization": org_name,
            "org_id_prefix": org_id[:8] if org_id else None,
            "channel_count_expected": channel_count_expected,
            "channels_found": len(channels) if not channels_error else None,
            "channels_error": bool(channels_error),
            "tiktok_found": bool(tiktok_id) and not tiktok_error,
            "tiktok_id_prefix": tiktok_id[:8] if tiktok_id else None,
            "tiktok_connected": tiktok_connected,
            "tiktok_disconnected": tiktok_disconnected,
            "tiktok_locked": tiktok_locked,
        })
        print("SQLite log: OK")
    except Exception as e:
        print(f"SQLite log: FAIL — {e}")


if __name__ == '__main__':
    main()
