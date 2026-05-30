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

    # Tally up time and window titles per category
    cat_seconds = defaultdict(float)
    cat_titles = defaultdict(set)

    for event in events:
        start = datetime.fromisoformat(event["start"])
        end = datetime.fromisoformat(event["end"])
        duration = (end - start).total_seconds()

        cat = event["category"]
        cat_seconds[cat] += duration

        # Window title is more useful than app name (e.g. "PROJ-42 — Jira" vs "Chrome")
        title = event.get("title", "")
        if title and title != event["app"]:
            cat_titles[cat].add(title)

    # Sort categories: most time first
    sorted_cats = sorted(cat_seconds.items(), key=lambda x: x[1], reverse=True)

    date_str = datetime.now().strftime("%a %b %-d")
    lines = [f"=== {date_str} — Daily Summary ===", ""]

    for cat, seconds in sorted_cats:
        # Cap at 3 titles so the summary stays readable
        titles = sorted(cat_titles[cat])[:3]
        title_str = f"  —  {', '.join(titles)}" if titles else ""
        lines.append(f"[{cat:<8}]  {format_duration(seconds)}{title_str}")

    if commits:
        lines.append("\nGit commits:")
        for c in sorted(commits, key=lambda x: x["time"]):
            t = datetime.fromisoformat(c["time"]).strftime("%H:%M")
            lines.append(f"  {t}  [{c['repo']}] {c['message']}")

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
