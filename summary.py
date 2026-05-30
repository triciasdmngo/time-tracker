"""
summary.py — builds the end-of-day text summary and sends a macOS notification.
"""

import json
import subprocess
from collections import defaultdict
from datetime import datetime


def format_duration(seconds):
    """Turns a raw second count into a readable string like '2h 05m' or '45m'."""
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    if h > 0:
        return f"{h}h {m:02d}m"
    return f"{m}m"


def generate_summary(day_data):
    """
    Builds a copy-pasteable text summary from a day's events and git commits.
    day_data is the dict loaded from (or held in memory as) the daily JSON file.
    """
    events = day_data.get("events", [])
    commits = day_data.get("commits", [])

    if not events and not commits:
        return "No activity tracked today."

    # Aggregate time per category, then per app within each category
    cat_seconds = defaultdict(float)
    cat_app_seconds = defaultdict(lambda: defaultdict(float))
    cat_app_titles = defaultdict(lambda: defaultdict(set))

    for event in events:
        start = datetime.fromisoformat(event["start"])
        end = datetime.fromisoformat(event["end"])
        duration = (end - start).total_seconds()

        cat = event["category"]
        app = event["app"]

        cat_seconds[cat] += duration
        cat_app_seconds[cat][app] += duration

        # Only store the window title if it adds info beyond the app name
        title = event.get("title", "")
        if title and title != app and app.lower() not in title.lower():
            cat_app_titles[cat][app].add(title)

    # Sort categories: most time first
    sorted_cats = sorted(cat_seconds.items(), key=lambda x: x[1], reverse=True)

    date_str = datetime.now().strftime("%A, %B %-d")
    lines = [f"Daily Summary — {date_str}", ""]

    for cat, seconds in sorted_cats:
        lines.append(f"{cat.upper()}  {format_duration(seconds)}")

        # Sort apps within the category by time spent, most first
        sorted_apps = sorted(
            cat_app_seconds[cat].items(), key=lambda x: x[1], reverse=True
        )
        for app, app_seconds in sorted_apps:
            lines.append(f"  • {app}  {format_duration(app_seconds)}")
            # Show up to 2 distinct window titles under each app
            titles = sorted(cat_app_titles[cat][app])[:2]
            for title in titles:
                lines.append(f"    – {title}")

        lines.append("")

    if commits:
        lines.append("\nGit commits:")
        for c in sorted(commits, key=lambda x: x["time"]):
            t = datetime.fromisoformat(c["time"]).strftime("%H:%M")
            location = c["repo"]
            if c.get("branch"):
                location = f"{c['repo']} · {c['branch']}"
            lines.append(f"  {t}  [{location}] {c['message']}")

    total = sum(cat_seconds.values())
    lines.append(f"\nTotal tracked: {format_duration(total)}")

    return "\n".join(lines)


def send_notification(title, body):
    """Fires a macOS notification banner via osascript."""
    # Keep the bubble short — macOS truncates long notification bodies anyway
    if len(body) > 200:
        body = body[:197] + "..."

    script = (
        f"display notification {json.dumps(body)} "
        f'with title {json.dumps(title)} '
        f'sound name "default"'
    )
    subprocess.run(["osascript", "-e", script])
