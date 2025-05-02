# data_store.py using Firestore

import firebase_admin
from firebase_admin import credentials, firestore
import os
SERVICE_KEY_PATH = os.path.join(
    os.path.dirname(__file__),
    "service_keys",
    "chatcc-evaluation-firebase-adminsdk-fbsvc-9ed0aadefe.json"
)
# Init Firebase Admin
if not firebase_admin._apps:
    cred = credentials.Certificate(SERVICE_KEY_PATH)  # Replace with your correct path
    firebase_admin.initialize_app(cred)

db = firestore.client()
collection_name = "chat_reports"  # name of your Firestore collection


def load_conversations():
    docs = db.collection(collection_name).stream()
    conversations = []
    for doc in docs:
        data = doc.to_dict()
        conversations.append(data)
     # Sort descending by date_of_report (most recent first)
    conversations.sort(key=lambda c: c.get("date_of_report", ""), reverse=True)
    return conversations


def save_conversations(convos):
    for convo in convos:
        save_single_conversation(convo)

def save_single_conversation(convo):
  doc_ref = db.collection(collection_name).document(convo["conversation_id"])
  doc_ref.set(convo)
