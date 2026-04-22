#!/usr/bin/env python3
"""
Jamf Pro - Bulk rename iPads to iPad-<SerialNumber>
Uses OAuth2 client credentials (Bearer token auth)
"""

import requests
import os
import sys
import time
from dotenv import load_dotenv

load_dotenv()

# Configuration
JAMF_URL    = os.environ["JAMF_URL"]
CLIENT_ID   = os.environ["CLIENT_ID"]
NAME_PREFIX = os.environ.get("NAME_PREFIX", "iPad-")
DRY_RUN     = os.environ.get("DRY_RUN", "false").lower() == "true"


def get_token(client_secret):
    resp = requests.post(
        f"{JAMF_URL}/api/oauth/token",
        data={
            "grant_type":    "client_credentials",
            "client_id":     CLIENT_ID,
            "client_secret": client_secret,
        },
    )
    resp.raise_for_status()
    data = resp.json()
    expires_in = data.get("expires_in", 1800)
    expires_at = time.time() + expires_in - min(60, expires_in // 4)
    return data["access_token"], expires_at


def get_all_devices(token):
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    devices, page, page_size = [], 0, 200
    while True:
        resp = requests.get(
            f"{JAMF_URL}/api/v2/mobile-devices",
            headers=headers,
            params={"page": page, "page-size": page_size},
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        devices.extend(results)
        if len(results) < page_size:
            break
        page += 1
    return devices


def send_rename_command(token, management_id, new_name):
    resp = requests.post(
        f"{JAMF_URL}/api/v2/mdm/commands",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "clientData":  [{"managementId": management_id}],
            "commandData": {"commandType": "SETTINGS", "deviceName": new_name},
        },
    )
    if resp.status_code not in (200, 201):
        try:
            errs = resp.json().get("errors", [])
            detail = errs[0].get("description") if errs else resp.text[:200]
        except Exception:
            detail = resp.text[:200]
        print(f"    HTTP {resp.status_code}: {detail}")
    return resp.status_code in (200, 201)


def main():
    client_secret = os.environ.get("JAMF_CLIENT_SECRET") or input("Enter Client Secret: ").strip()
    if not client_secret:
        print("ERROR: Client secret is required.")
        sys.exit(1)

    print("Authenticating...")
    token, expires_at = get_token(client_secret)
    print("Token acquired.\n")

    print("Fetching device inventory...")
    devices = get_all_devices(token)
    print(f"Found {len(devices)} mobile devices.\n")

    renamed = skipped = errors = no_serial = 0

    for device in devices:
        device_id     = device.get("id")
        management_id = device.get("managementId", "")
        serial        = (device.get("serialNumber") or "").strip()
        current       = (device.get("name") or "").strip()
        model         = (device.get("model") or "").lower()

        # Skip non-iPads
        if "ipad" not in model:
            skipped += 1
            continue

        if not serial:
            print(f"  [SKIP] ID {device_id} - no serial number found")
            no_serial += 1
            continue

        target = f"{NAME_PREFIX}{serial}"

        if current == target:
            print(f"  [OK]   {current} - already correct")
            skipped += 1
            continue

        if time.time() >= expires_at:
            print("  [AUTH] Token expiring, refreshing...")
            token, expires_at = get_token(client_secret)

        if DRY_RUN:
            print(f"  [DRY]  '{current}' -> '{target}'")
            renamed += 1
        else:
            if send_rename_command(token, management_id, target):
                print(f"  [DONE] '{current}' -> '{target}'")
                renamed += 1
            else:
                print(f"  [ERR]  Failed to rename '{current}' (ID: {device_id})")
                errors += 1


    print(f"\n--- Summary ---")
    print(f"Mode:       {'DRY RUN' if DRY_RUN else 'LIVE'}")
    print(f"Renamed:    {renamed}")
    print(f"Skipped:    {skipped}")
    print(f"No serial:  {no_serial}")
    print(f"Errors:     {errors}")
    if DRY_RUN:
        print("\nSet DRY_RUN = False to apply changes.")


if __name__ == "__main__":
    main()