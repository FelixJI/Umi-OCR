import json
import sys
import os
from pathlib import Path

# Calculate paths
# src/umi_about.py -> src -> PROJECT_ROOT
PROJECT_ROOT = Path(__file__).parent.parent
ABOUT_FILE = PROJECT_ROOT / "UmiOCR-data" / "about.json"

def _load_about():
    about = {}
    if ABOUT_FILE.exists():
        try:
            with open(ABOUT_FILE, "r", encoding="utf-8") as f:
                about = json.load(f)
        except Exception:
            pass
    
    # Ensure structure
    if "name" not in about:
        about["name"] = "Umi-OCR"
    
    # Handle 'app' field which might be a string placeholder in source
    app_info = {}
    if "app" in about and isinstance(about["app"], dict):
        app_info = about["app"]
    
    # Fill runtime app info
    # path: path to executable
    if getattr(sys, 'frozen', False):
        app_info["path"] = sys.executable
    else:
        app_info["path"] = sys.executable # For dev, python.exe is the executable
        
    about["app"] = app_info
    return about

UmiAbout = _load_about()
