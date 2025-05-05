# data_store.py using Firestore with dataset support

import firebase_admin
from firebase_admin import credentials, firestore
import os

# Firebase Admin Init
SERVICE_KEY_PATH = os.path.join(
    os.path.dirname(__file__),
    "service_keys",
    "chatcc-evaluation-firebase-adminsdk-fbsvc-9ed0aadefe.json"
)
if not firebase_admin._apps:
    cred = credentials.Certificate(SERVICE_KEY_PATH)
    firebase_admin.initialize_app(cred)

db = firestore.client()
ROOT_COLLECTION = "chat_reports"

# ------------------------------
# 🔹 New: Load available dataset names
# ------------------------------
def load_dataset_names():
    collections = db.collection(ROOT_COLLECTION).list_documents()
    return [doc.id for doc in collections]

# ------------------------------
# 🔹 Load conversations from a specific dataset
# ------------------------------
def load_conversations(dataset_name):
    if not dataset_name:
        return []

    conv_path = f"{ROOT_COLLECTION}/{dataset_name}/conversations"
    docs = db.collection(conv_path).stream()

    conversations = []
    for doc in docs:
        data = doc.to_dict()
        conversations.append(data)

    conversations.sort(key=lambda c: c.get("date_of_report", ""), reverse=True)
    return conversations

# ------------------------------
# 🔹 Save single conversation to a dataset
# ------------------------------
def save_single_conversation(convo, dataset_name):
    if not dataset_name:
        raise ValueError("dataset_name is required to save conversation")

    doc_ref = db.collection(ROOT_COLLECTION).document(dataset_name).collection("conversations").document(convo["conversation_id"])
    doc_ref.set(convo)

# ------------------------------
# 🔹 Optional: Save multiple conversations
# ------------------------------
def save_conversations(convos, dataset_name):
    for convo in convos:
        save_single_conversation(convo, dataset_name)
