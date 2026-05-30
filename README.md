# time-tracker

A macOS menu bar app that watches what you're working on throughout the day and reminds you to log your timesheet at a set time.

It captures the active app and window title every 2 seconds, buckets them into categories (dev, meeting, comms, docs), and optionally reads your git commits. At your configured reminder time, it fires a macOS notification. You can also pull up the summary any time from the menu bar icon.

```
⏱
├─ Tracking: Cursor  (dev)
├─ ─────────────────────────
├─ Show Today's Summary
├─ Open Config
├─ ─────────────────────────
└─ Quit
```

---

## Requirements

- macOS
- Python 3.9+

---

## Setup

### 1. Install dependencies

```bash
pip install rumps py2app
```

### 2. Build the app

```bash
python3 setup.py py2app
```

This creates `dist/Time Tracker.app`. Drag it to `/Applications`.

### 3. Grant Accessibility permission

The tracker uses AppleScript to read the active window title. macOS requires you to allow this once:

1. Open **System Settings → Privacy & Security → Accessibility**
2. Click the `+` button and add **Time Tracker** (from your `/Applications` folder)

Because you're running it as a standalone app rather than through Terminal, the permission is scoped only to this app.

### 4. Launch it

Open **Time Tracker** from `/Applications`. You'll see the ⏱ icon appear in your menu bar.

---

## Development (no build needed)

If you want to run the tracker directly from the terminal while working on it:

```bash
# 1. Create a virtual environment (one-time setup)
python3 -m venv .venv

# 2. Activate it — you'll see (.venv) in your prompt when it's active
source .venv/bin/activate

# 3. Install dependencies
pip install rumps py2app

# 4. Run the tracker
python3 tracker.py
```

To deactivate the venv when you're done:
```bash
deactivate
```

You need to run `source .venv/bin/activate` each time you open a new terminal session before running the tracker. The `.venv/` folder is already in `.gitignore` so it won't be committed.

Note: in dev mode, macOS will prompt for Accessibility access for your terminal app instead of Time Tracker.

---

## Configuration

Click **⏱ → Open Config** in the menu bar, or edit `~/.time-tracker/config.json` directly. The file is created automatically on first launch.

```json
{
  "reminder_time": "17:30",
  "git_repos": [],
  "min_session_seconds": 15,
  "data_dir": "~/.time-tracker",
  "app_categories": { ... }
}
```

| Key | What it does |
|---|---|
| `reminder_time` | 24h time when the notification fires, e.g. `"17:30"` for 5:30 PM |
| `git_repos` | List of repo paths to scan for today's commits |
| `min_session_seconds` | Ignore app switches shorter than this (filters out quick glances) |
| `data_dir` | Where daily JSON files are saved |
| `app_categories` | Maps app names to categories: `dev`, `meeting`, `comms`, `docs`, `other` |

### Adding your git repos

```json
"git_repos": [
  "~/Documents/projects/my-app",
  "~/Documents/projects/other-repo"
]
```

### Adding an app that isn't listed

If an app isn't in `app_categories` it gets filed under `other`. Add it using the exact name that appears in the menu bar when that app is focused.

```json
"app_categories": {
  "Figma": "design",
  "TablePlus": "dev"
}
```

---

## Usage

### Check what you're tracking

The menu bar item shows the current app and category in real time:
```
Tracking: Cursor  (dev)
```

### Get today's summary

Click **⏱ → Show Today's Summary**. A dialog appears with the full breakdown, and the text is automatically copied to your clipboard so you can paste it straight into your timesheet.

```
=== Fri May 30 — Daily Summary ===

[dev     ]  3h 22m  —  time-tracker — tracker.py, my-app — server.py
[meeting ]  45m     —  Zoom Meeting
[comms   ]  28m

Git commits:
  10:23  [time-tracker] feat: build as menu bar app
  14:41  [my-app] fix: handle empty API response

Total tracked: 4h 35m
```

### End-of-day reminder

At your configured `reminder_time` a macOS notification fires with a short preview. The full summary is also ready via the menu.

### Quit

Click **⏱ → Quit**. The current session is saved before exit.

---

## Data

Each day's activity is saved to `~/.time-tracker/YYYY-MM-DD.json`. The file is written every 30 seconds, so you lose at most 30 seconds of data if the app crashes. The JSON is human-readable if you ever want to inspect or edit it directly.

---

## File overview

```
time-tracker/
├── tracker.py      Menu bar app — timers, menus, session tracking
├── watcher.py      Talks to macOS: active window (AppleScript) + git commits
├── summary.py      Builds the summary text and sends the notification
├── setup.py        Build script for creating the .app bundle
└── requirements.txt  rumps (menu bar), py2app (build)
```
