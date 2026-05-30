#!/usr/bin/env python3
"""
tracker.py — Menu bar app entry point.

Development:  python3 tracker.py
Build .app:   python3 setup.py py2app
              Then drag dist/Time Tracker.app to /Applications.
"""

import json
import os
import subprocess
import tempfile
from datetime import date, datetime
from pathlib import Path


def resource_path(filename):
    """Returns the correct path to a resource file in both dev and bundled modes."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

import rumps

from watcher import get_active_window, poll_git_commits
from summary import generate_summary, send_notification


# ── Config ────────────────────────────────────────────────────────────────────

CONFIG_DIR = Path.home() / ".time-tracker"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "reminder_time": "17:30",       # 24h, e.g. "17:30" for 5:30 PM
    "git_repos": [],                # e.g. ["~/code/my-app", "~/code/other-repo"]
    "min_session_seconds": 15,      # ignore app switches shorter than this
    "data_dir": "~/.time-tracker",  # where daily JSON files are saved
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
        "Arc": "other",
    },
}


def load_config():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(json.dumps(DEFAULT_CONFIG, indent=2))
    with open(CONFIG_FILE) as f:
        config = json.load(f)
    for key, value in DEFAULT_CONFIG.items():
        config.setdefault(key, value)
    return config


def day_file(config, date_str):
    data_dir = Path(os.path.expanduser(config["data_dir"]))
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / f"{date_str}.json"


def load_day(path):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {"date": date.today().isoformat(), "events": [], "commits": []}


def save_day(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


# ── Menu bar app ───────────────────────────────────────────────────────────────

class TimeTrackerApp(rumps.App):

    def __init__(self):
        super().__init__("Time Tracker", icon=resource_path("clock_menubar.png"), template=False, quit_button=None)

        self.config = load_config()
        self._today = date.today().isoformat()
        self._day_path = day_file(self.config, self._today)
        self.day_data = load_day(self._day_path)

        # Current session state
        self._current_app = None
        self._current_title = None
        self._session_start = None
        self._reminder_sent = False

        # If we launch after the reminder time, don't fire a stale notification
        reminder_str = self.config.get("reminder_time", "")
        if reminder_str:
            reminder_dt = datetime.strptime(
                f"{self._today} {reminder_str}", "%Y-%m-%d %H:%M"
            )
            if datetime.now() >= reminder_dt:
                self._reminder_sent = True

        # Keep a direct reference to the status item so we can update its title
        self._status_item = rumps.MenuItem("Tracking: starting…")

        self.menu = [
            self._status_item,
            None,
            rumps.MenuItem("Show Today's Summary", callback=self.show_summary),
            rumps.MenuItem("Open Config", callback=self.open_config),
            rumps.MenuItem("Reload Config", callback=self.reload_config),
            None,
            rumps.MenuItem("Quit", callback=self.on_quit),
        ]


    # ── Timers ────────────────────────────────────────────────────────────────
    # rumps.timer runs the method on a background thread at the given interval.

    @rumps.timer(2)
    def on_track_tick(self, _):
        """Poll the active window every 2 seconds."""
        try:
            app, title = get_active_window()
        except Exception:
            return  # permissions not granted yet — keep waiting

        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")

        # Handle midnight rollover — save yesterday, start fresh
        if today_str != self._today:
            self._flush()
            save_day(self._day_path, self.day_data)
            self._today = today_str
            self._day_path = day_file(self.config, today_str)
            self.day_data = load_day(self._day_path)
            self._reminder_sent = False

        if self._current_app is None:
            # First successful poll — initialise state
            self._current_app = app
            self._current_title = title
            self._session_start = now
        elif app != self._current_app or title != self._current_title:
            # App or window changed — commit the finished session
            self._commit_session(now)
            self._current_app = app
            self._current_title = title
            self._session_start = now

        category = self.config["app_categories"].get(app, "other")
        self._status_item.title = f"Tracking: {app}  ({category})"

    @rumps.timer(30)
    def on_save_tick(self, _):
        """Flush and save to disk every 30 seconds."""
        self._flush()
        save_day(self._day_path, self.day_data)

    @rumps.timer(60)
    def on_reminder_tick(self, _):
        """Check once a minute whether it's time to send the reminder."""
        if self._reminder_sent:
            return
        reminder_str = self.config.get("reminder_time", "")
        if not reminder_str:
            return
        now = datetime.now()
        reminder_dt = datetime.strptime(
            f"{now.strftime('%Y-%m-%d')} {reminder_str}", "%Y-%m-%d %H:%M"
        )
        if now >= reminder_dt:
            self._flush()
            summary = generate_summary(self.day_data)
            preview = [
                line for line in summary.splitlines()
                if line and not line.startswith("===")
            ][:4]
            send_notification("Time to log your timesheet!", "\n".join(preview))
            self._reminder_sent = True

    # ── Menu callbacks ─────────────────────────────────────────────────────────

    def show_summary(self, _):
        self._flush()

        # Only offer git commits if repos are configured
        if self.config["git_repos"]:
            response = rumps.alert(
                title="Include git commits?",
                message="Fetch today's commits from your configured repos and add them to the summary?",
                ok="Yes",
                cancel="No",
            )
            if response == 1:
                self._add_commits(poll_git_commits(self.config["git_repos"]))

        try:
            text = generate_summary(self.day_data)

            # Copy to clipboard so it's ready to paste into the timesheet
            subprocess.run(["pbcopy"], input=text.encode("utf-8"))

            # Write to a temp file and open in the default text editor
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".txt",
                prefix="time-tracker-",
                delete=False,
                encoding="utf-8",
            ) as f:
                f.write(text)
                f.write("\n\n(Copied to clipboard ✓)")
                tmp_path = f.name

            subprocess.run(["open", "-t", tmp_path])

        except Exception as e:
            rumps.alert(title="Error", message=str(e), ok="Close")

    def open_config(self, _):
        """Open config.json in the default text editor."""
        subprocess.run(["open", "-t", str(CONFIG_FILE)])

    def reload_config(self, _):
        """Re-read config.json without restarting the app."""
        self.config = load_config()
        # Re-evaluate reminder state in case reminder_time changed
        reminder_str = self.config.get("reminder_time", "")
        if reminder_str:
            today = date.today().isoformat()
            reminder_dt = datetime.strptime(
                f"{today} {reminder_str}", "%Y-%m-%d %H:%M"
            )
            if datetime.now() < reminder_dt:
                self._reminder_sent = False  # reset so it fires at the new time
        rumps.notification("Time Tracker", "", "Config reloaded.")

    def on_quit(self, _):
        self._flush()
        save_day(self._day_path, self.day_data)
        rumps.quit_application()

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _commit_session(self, end):
        """Save the current session to day_data if it lasted long enough."""
        elapsed = (end - self._session_start).total_seconds()
        if elapsed < self.config["min_session_seconds"]:
            return
        self.day_data["events"].append({
            "start": self._session_start.isoformat(),
            "end": end.isoformat(),
            "app": self._current_app,
            "title": self._current_title,
            "category": self.config["app_categories"].get(self._current_app, "other"),
        })

    def _flush(self):
        """Commit the in-progress session without switching the current app."""
        if self._current_app:
            now = datetime.now()
            self._commit_session(now)
            self._session_start = now  # reset so next flush doesn't double-count

    def _add_commits(self, commits):
        existing = {c["hash"] for c in self.day_data["commits"]}
        for c in commits:
            if c["hash"] not in existing:
                self.day_data["commits"].append(c)
                existing.add(c["hash"])


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    TimeTrackerApp().run()
