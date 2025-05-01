import json
import os

DATA_FILE = os.path.join(os.path.dirname(__file__), "conversations.json")

def load_conversations():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data

def save_conversations(convos):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(convos, f, indent=2)
