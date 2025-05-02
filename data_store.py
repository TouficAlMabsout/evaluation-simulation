# data_store.py using Firestore

import firebase_admin
from firebase_admin import credentials, firestore
import os
SERVICE_KEY_PATH = os.path.join(
    os.path.dirname(__file__),
    "service_keys",
    "tartil-app-firebase-adminsdk-dsr35-9540e005f7.json"
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
    return conversations


def save_conversations(convos):
    batch = db.batch()
    for convo in convos:
        doc_ref = db.collection(collection_name).document(convo["conversation_id"])
        batch.set(doc_ref, convo)
    batch.commit()


# Optional: Save a single conversation

# def save_single_conversation(convo):
#   doc_ref = db.collection(collection_name).document(convo["conversation_id"])
#    doc_ref.set(convo)
