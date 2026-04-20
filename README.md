# Jamf iPad Bulk Rename

Bulk renames all iPad devices in Jamf Pro to `iPad-<SerialNumber>` using the Jamf Pro API with OAuth2 client credentials.

## What it does

1. Authenticates via OAuth2 client credentials to get a Bearer token
2. Pages through all mobile devices in `GET /api/v2/mobile-devices`
3. Filters to iPads only (by checking the `model` field for "ipad")
4. For each iPad not already named `iPad-<serial>`, sends a `SETTINGS` MDM command via `POST /api/v2/mdm/commands` to set the device name
5. Prints a summary of renamed, skipped, and errored devices

A `DRY_RUN` env var lets you preview changes without sending any commands.

The script automatically refreshes the Bearer token mid-run if it is about to expire, so runs covering large device counts (500+) complete without authentication failures.

## Setup

**Requirements:** Python 3, `requests`, `python-dotenv` (`pip install requests python-dotenv`)

**Configuration:** copy `.env.example` to `.env` and fill in your values:

| Variable | Description |
|---|---|
| `JAMF_URL` | Your Jamf Pro URL |
| `CLIENT_ID` | OAuth API client ID |
| `NAME_PREFIX` | Prefix for renamed devices (default: `iPad-`) |
| `DRY_RUN` | `true` to preview only, `false` to apply |

`JAMF_CLIENT_SECRET` is never stored in `.env` — it is prompted at runtime or supplied via environment variable.

**Running:**

```
# Supply secret interactively
python jamf_rename_ipads.py
```

Or set `JAMF_CLIENT_SECRET` in your shell before running:

```bash
# Linux / macOS
export JAMF_CLIENT_SECRET=your_secret
python jamf_rename_ipads.py
```

```powershell
# Windows (PowerShell)
$env:JAMF_CLIENT_SECRET = "your_secret"
python jamf_rename_ipads.py
```

## Jamf API role privileges required

The API client role needs all three of these privileges:

- **Read Mobile Devices** — to fetch device inventory
- **Send Mobile Device Set Device Name Command** — for the rename MDM command
- **View MDM command information in Jamf Pro API** — required to POST to `/api/v2/mdm/commands` (counterintuitively named; this is the send privilege for the v2 MDM commands endpoint)