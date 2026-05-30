"""
Build script for creating the Time Tracker .app bundle.

Usage:
    pip install rumps py2app
    python3 setup.py py2app

The finished app will be at dist/Time Tracker.app.
Drag it to /Applications, then launch it from there.
"""

from setuptools import setup

APP = ["tracker.py"]

OPTIONS = {
    # argv_emulation must be False for menu bar (LSUIElement) apps
    "argv_emulation": False,
    "packages": ["rumps"],
    "plist": {
        # Hides the app from the Dock — it lives in the menu bar only
        "LSUIElement": True,
        "CFBundleName": "Time Tracker",
        "CFBundleDisplayName": "Time Tracker",
        # Unique identifier macOS uses to track app permissions
        "CFBundleIdentifier": "com.timetracker.app",
        "CFBundleVersion": "1.0.0",
        # Shown by macOS when prompting for Accessibility access
        "NSAccessibilityUsageDescription": (
            "Time Tracker reads the active window title to log what you work on."
        ),
        "NSAppleEventsUsageDescription": (
            "Time Tracker uses AppleScript to get the name of the frontmost window."
        ),
    },
}

setup(
    name="Time Tracker",
    app=APP,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
