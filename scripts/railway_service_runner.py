#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Railway Service Runner - Runs both scanner and web dashboard
"""

import os
import subprocess
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run_scanner():
    """Run the scanner service"""
    scanner_script = ROOT / "scripts" / "railway_scanner_service.py"
    subprocess.run([sys.executable, str(scanner_script)])


def run_web_dashboard():
    """Run the web dashboard"""
    web_script = ROOT / "scripts" / "web_dashboard.py"
    subprocess.run([sys.executable, str(web_script)])


if __name__ == "__main__":
    # Start scanner in background thread
    scanner_thread = threading.Thread(target=run_scanner, daemon=True)
    scanner_thread.start()

    # Run web dashboard in main thread (Railway needs this for PORT binding)
    run_web_dashboard()
