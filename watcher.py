"""
watcher.py — reads the active macOS window and polls git repos for commits.
"""

import os
import subprocess
from datetime import date, datetime


def get_active_window():
    """
    Returns (app_name, window_title) of the frontmost macOS app.
    Uses AppleScript via osascript. Raises PermissionError if Accessibility
    access hasn't been granted.
    """
    script = """
tell application "System Events"
    set frontApp to first application process whose frontmost is true
    set appName to displayed name of frontApp
    set winTitle to ""
    try
        set winTitle to name of front window of frontApp
    end try
    return appName & "|||" & winTitle
end tell"""

    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise PermissionError(
            "Could not read the active window.\n"
            "Go to System Settings → Privacy & Security → Accessibility\n"
            "and grant access to your terminal app."
        )

    # AppleScript returns "AppName|||Window Title"
    parts = result.stdout.strip().split("|||", 1)
    app_name = parts[0]
    window_title = parts[1] if len(parts) > 1 else ""
    return app_name, window_title


def poll_git_commits(repo_paths):
    """
    Scans each repo path for git commits made today.
    Returns a list of dicts with keys: hash, time, message, repo.
    """
    since = f"{date.today().isoformat()} 00:00:00"
    commits = []

    for raw_path in repo_paths:
        path = os.path.expanduser(raw_path)
        result = subprocess.run(
            [
                "git", "-C", path,
                "log",
                f"--since={since}",
                "--format=%H|||%aI|||%s|||%D",
                "--no-merges",
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            continue  # not a repo, or no access — skip silently

        repo_name = os.path.basename(path.rstrip("/"))

        for line in result.stdout.strip().splitlines():
            if not line:
                continue
            parts = line.split("|||", 3)
            if len(parts) != 4:
                continue
            hash_, iso_time, message, refs = parts
            try:
                commit_time = datetime.fromisoformat(iso_time)
            except ValueError:
                continue

            # %D gives refs like "HEAD -> feat/user-auth, origin/feat/user-auth"
            # Extract just the local branch name (the part after "HEAD -> ")
            branch = ""
            for ref in refs.split(","):
                ref = ref.strip()
                if ref.startswith("HEAD ->"):
                    branch = ref.replace("HEAD ->", "").strip()
                    break

            commits.append({
                "hash": hash_[:7],
                "time": commit_time.isoformat(),
                "message": message,
                "repo": repo_name,
                "branch": branch,
            })

    return commits
