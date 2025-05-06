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

# 🔹 Create an empty dataset
def create_dataset(dataset_name):
    if not dataset_name:
        raise ValueError("Dataset name cannot be empty.")
    db.collection(ROOT_COLLECTION).document(dataset_name).set({})

# 🔹 Delete a dataset (including its conversations)
def delete_dataset(dataset_name):
    if not dataset_name:
        raise ValueError("Dataset name cannot be empty.")
    dataset_ref = db.collection(ROOT_COLLECTION).document(dataset_name)
    # Delete all subcollection documents first
    conversations = dataset_ref.collection("conversations").list_documents()
    for convo in conversations:
        convo.delete()
    dataset_ref.delete()

def delete_conversation(dataset_name, conversation_id):
    if not dataset_name or not conversation_id:
        raise ValueError("Both dataset_name and conversation_id are required")
    db.collection(ROOT_COLLECTION).document(dataset_name).collection("conversations").document(conversation_id).delete()

def duplicate_conversation(source_convo, target_dataset, clear_results=False):
    convo_copy = dict(source_convo)
    if clear_results:
        convo_copy["results"] = []

    doc_ref = (
        db.collection("chat_reports")
        .document(target_dataset)
        .collection("conversations")
        .document(convo_copy["conversation_id"])
    )
    doc_ref.set(convo_copy)

def rename_dataset(old_name, new_name):
    if not old_name or not new_name:
        raise ValueError("Both old and new names are required.")

    # Check for conflict
    existing = load_dataset_names()
    if new_name in existing:
        raise ValueError("A dataset with the new name already exists.")

    # Copy conversations to new dataset
    old_ref = db.collection(ROOT_COLLECTION).document(old_name).collection("conversations")
    new_ref = db.collection(ROOT_COLLECTION).document(new_name).collection("conversations")

    for doc in old_ref.stream():
        new_ref.document(doc.id).set(doc.to_dict())

    # Delete old dataset
    delete_dataset(old_name)
    # Create metadata entry for new dataset
    db.collection(ROOT_COLLECTION).document(new_name).set({})


