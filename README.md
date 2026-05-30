# time-tracker

A macOS menu bar app that watches what you're working on throughout the day and reminds you to log your timesheet at a set time. Built because I always forget to log my time and struggle keeping my timesheets up-to-date.

**What it does:** It captures the active app and window title every 2 seconds, buckets them into categories (dev, meeting, comms, docs), and optionally reads your git commits. At your configured reminder time, it fires a macOS notification. You can also pull up the summary any time from the menu bar icon.

**Disclaimer:** Initially written in Go, then rewritten in Python as a learning project with the help of Claude Sonnet 4.6. The code works but may not follow all Python best practices. I'm learning as I go.

```
⏱
├─ Tracking: Cursor  (dev)
├─ ─────────────────────────
├─ Show Today's Summary
├─ Open Config
├─ Reload Config
├─ ─────────────────────────
└─ Quit
```

---

## Requirements

- macOS
- Python 3.9+

---

## Setup

All commands below should be run from inside the project folder:

```bash
cd ~/Documents/projects/time-tracker
```

### 1. Create a virtual environment

A virtual environment keeps the app's dependencies isolated from the rest of your system. You only need to do this once.

```bash
python3 -m venv .venv
source .venv/bin/activate
```

You'll see `(.venv)` appear in your terminal prompt — that means it's active.

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Build the app

```bash
python3 setup.py py2app
```

This creates `dist/Time Tracker.app`. Drag it to `/Applications`.

### 4. Grant Accessibility permission

The tracker uses AppleScript to read the active window title. macOS requires you to allow this once:

1. Open **System Settings → Privacy & Security → Accessibility**
2. Click the `+` button and add **Time Tracker** (from your `/Applications` folder)

Because you're running it as a standalone app rather than through Terminal, the permission is scoped only to this app.

### 5. Launch it

Open **Time Tracker** from `/Applications`. You'll see the ⏱ icon appear in your menu bar.

---

## Development (running without building)

If you want to run the tracker directly from the terminal — for example while making changes to the code — use this workflow instead of building the app each time.

```bash
# Navigate to the project folder
cd ~/Documents/projects/time-tracker

# Create a virtual environment (one-time setup)
python3 -m venv .venv

# Activate it — you'll see (.venv) in your prompt when it's active
source .venv/bin/activate

# Install dependencies (one-time setup)
pip install -r requirements.txt

# Run the tracker
python3 tracker.py
```

Each time you open a new terminal window, you'll need to activate the venv again before running the tracker:

```bash
cd ~/Documents/projects/time-tracker
source .venv/bin/activate
python3 tracker.py
```

To deactivate the venv when you're done working on the code:

```bash
deactivate
```

> **Note:** In dev mode, macOS will prompt for Accessibility access for your terminal app instead of Time Tracker.

---

## Configuration

Click **⏱ → Open Config** to open the config file in your default editor. When you're done editing, save the file and click **⏱ → Reload Config** to apply changes without restarting the app.

The config file lives at `~/.time-tracker/config.json` and is created automatically on first launch. It looks like this:

```json
{
  "reminder_time": "17:30",
  "git_repos": [],
  "min_session_seconds": 15,
  "data_dir": "~/.time-tracker",
  "app_categories": {
    "Code": "dev",
    "Cursor": "dev",
    "Xcode": "dev",
    "Terminal": "dev",
    "iTerm2": "dev",
    "Warp": "dev",
    "Ghostty": "dev",
    "Zoom": "meeting",
    "FaceTime": "meeting",
    "Microsoft Teams": "meeting",
    "Slack": "comms",
    "Mail": "comms",
    "Messages": "comms",
    "Notion": "docs",
    "Pages": "docs",
    "Microsoft Word": "docs",
    "Google Chrome": "other",
    "Safari": "other",
    "Firefox": "other",
    "Arc": "other"
  }
}
```

| Key                   | What it does                                                             |
| --------------------- | ------------------------------------------------------------------------ |
| `reminder_time`       | 24h time when the notification fires, e.g. `"17:30"` for 5:30 PM         |
| `git_repos`           | List of repo paths to scan for today's commits                           |
| `min_session_seconds` | Ignore app switches shorter than this (filters out quick glances)        |
| `data_dir`            | Where daily JSON files are saved                                         |
| `app_categories`      | Maps app names to categories: `dev`, `meeting`, `comms`, `docs`, `other` |

### Adding your git repos

Find the `"git_repos"` line in your config file and add the paths to your repos:

```json
"git_repos": [
  "~/Documents/projects/my-app",
  "~/Documents/projects/other-repo"
]
```

### Adding an app that isn't listed

If an app isn't in `app_categories` it gets filed under `other`. To categorize it, add a new line inside the `"app_categories"` section. The name must match exactly what appears in the menu bar when that app is focused.

```json
"app_categories": {
  "Figma": "design",
  "TablePlus": "dev",
  ... (rest of the existing entries)
}
```

---

## Usage

### Check what you're tracking

The menu bar shows the current app and category, updated every 2 seconds:

```
Tracking: Cursor  (dev)
```

### Get today's summary

Click **⏱ → Show Today's Summary**. If you have git repos configured, you'll be asked first whether to include today's commits — yes or no, your choice. A dialog then appears with the full breakdown, and the text is automatically copied to your clipboard so you can paste it straight into your timesheet.

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

If you say no to git commits, or have no repos configured, the summary shows app activity only.

### End-of-day reminder

At your configured `reminder_time` a macOS notification fires with a short preview of your app activity. For the full breakdown including git commits, click **⏱ → Show Today's Summary**.

### Change settings on the fly

1. Click **⏱ → Open Config** — opens `config.json` in your default editor
2. Edit and save the file
3. Click **⏱ → Reload Config** — changes take effect immediately, no restart needed

If you changed `reminder_time` to something still in the future, the reminder is also reset so it fires at the new time.

### Quit

Click **⏱ → Quit**. The current session is saved before exit.

---

## Transferring to another Mac

The `.app` bundle is self-contained — it includes everything it needs to run. To move it to another machine (e.g. your work Mac mini):

1. Copy `dist/Time Tracker.app` to the other Mac (AirDrop, USB, etc.)
2. Drag it into `/Applications`
3. **First launch only:** the app isn't code-signed, so macOS will block it with a warning. To get past this: instead of double-clicking, **right-click → Open** and confirm. macOS remembers this choice and won't ask again.
4. The app launches and creates a fresh `~/.time-tracker/config.json` on that machine
5. Click **⏱ → Open Config** to configure it (reminder time, git repos, etc.)
6. Go to **System Settings → Privacy & Security → Accessibility** and add Time Tracker
7. Optionally add it to **System Settings → General → Login Items** so it starts automatically on login

The other Mac does not need Python installed.

---

## Data

Each day's activity is saved to `~/.time-tracker/YYYY-MM-DD.json`. The file is written every 30 seconds, so you lose at most 30 seconds of data if the app crashes. The JSON is human-readable if you ever want to inspect or edit it directly.

---

## File overview

```
time-tracker/
├── tracker.py       Menu bar app — timers, menus, session tracking
├── watcher.py       Talks to macOS: active window (AppleScript) + git commits
├── summary.py       Builds the summary text and sends the notification
├── setup.py         Build script for creating the .app bundle
└── requirements.txt Dependencies: rumps (menu bar UI), py2app (build tool)
```
