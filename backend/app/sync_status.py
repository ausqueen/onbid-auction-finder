import json
import os

STATUS_FILE = os.path.join(os.path.dirname(__file__), "sync_status.json")

def get_status():
    if not os.path.exists(STATUS_FILE):
        return {"phase": None, "message": ""}
    try:
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"phase": None, "message": ""}

def set_status(phase, message=""):
    try:
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump({"phase": phase, "message": message}, f, ensure_ascii=False)
    except Exception:
        pass
