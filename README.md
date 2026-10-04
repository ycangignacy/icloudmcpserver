# iCloud Calendar MCP Server

A local MCP server for reading and managing iCloud calendars through CalDAV. It uses stdio and runs on Windows, macOS, and Linux.

## Requirements

- Python 3.12 or newer.
- An Apple Account with two-factor authentication enabled.
- An app-specific password created at [account.apple.com](https://account.apple.com/) under **Sign-In and Security → App-Specific Passwords**. Do not use your main Apple Account password.

## Installation

1. Clone the repository and enter its directory:

   ```sh
   git clone https://github.com/ycangignacy/icloudmcpserver.git
   cd icloudmcpserver
   ```

2. Create a virtual environment and install the dependencies:

   **Windows (PowerShell)**

   ```powershell
   py -3.12 -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   Copy-Item .env.example .env.local
   ```

   **macOS / Linux**

   ```sh
   python3 -m venv .venv
   .venv/bin/python -m pip install -r requirements.txt
   cp .env.example .env.local
   ```

3. Open `.env.local` and enter your Apple Account email address and app-specific password. The default `APPLE_CALDAV_URL` normally does not need to change.

## Connect an MCP client

Add a stdio server to your MCP client's configuration. Set `command` to the absolute path of the Python executable inside `.venv`, and pass the absolute path of `server.py` as an argument. For a client that uses JSON:

```json
{
  "mcpServers": {
    "icloud-calendar": {
      "command": "/absolute/path/to/icloudmcpserver/.venv/bin/python",
      "args": ["/absolute/path/to/icloudmcpserver/server.py"]
    }
  }
}
```

On Windows, use the absolute path to `.venv\Scripts\python.exe`. Escape backslashes in JSON paths. Configuration formats vary by MCP client. The server loads `.env.local` from the directory containing `server.py`, so the password does not need to appear in your client configuration. Call `list_calendars` after connecting to obtain calendar IDs.

On Windows, you can also launch the server with `start.ps1` from the project directory. It waits for MCP messages on standard input; it does not display a text menu.

## Tools

| Tool | Purpose |
| --- | --- |
| `list_calendars` | List calendar names and IDs. |
| `list_events` | List event occurrences in a date range; the end is exclusive. |
| `get_event` | Get event details and its complete ICS by UID. |
| `create_event` | Create an event. |
| `update_event` | Update the master event or a recurring series. |
| `delete_event` | Delete an event or an entire recurring series. |

Use `YYYY-MM-DD` for all-day events. Timed events require ISO 8601 with a UTC offset, for example `2026-10-04T14:00:00+02:00`. All-day end dates are exclusive: a one-day event ends on the following date. Updating a recurring series changes its master component; existing exceptions may retain their own times and descriptions. Deleting by UID removes the whole series.

## Backups and privacy

The server saves complete ICS files before updates and deletions, and after creations and updates, in `kopie zapasowe/wydarzenia`. These files may contain private meeting details. `.env.local`, backups, and `.venv` are ignored by Git. Do not upload or share them.

made by ycangignacy
