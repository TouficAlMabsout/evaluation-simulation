from fastapi import FastAPI, UploadFile, Form, HTTPException
from chat_simulator import simulate_chat
from langsmith import Client
import json
from dotenv import load_dotenv
import os

load_dotenv()

LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or use ["http://localhost:8501"] to restrict to Streamlit only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/simulate")
async def simulate(file: UploadFile = None, prompt_id: str = Form(None), model_name: str = Form(None)):
    if file is None:
        raise HTTPException(status_code=400, detail="No file uploaded. Please upload a chat JSON file.")
    if not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Only .json files are accepted. Please upload a valid JSON file.")
    if prompt_id is None or prompt_id.strip() == "":
        raise HTTPException(status_code=400, detail="Prompt ID is missing. Please enter a LangSmith prompt ID.")
    if model_name is None or model_name.strip() == "":
        raise HTTPException(status_code=400, detail="Claude model is not selected.")

    try:
        content = await file.read()
        chat = json.loads(content)
        if not isinstance(chat, list) or not all(isinstance(m, dict) and "role" in m and m["role"] in ["human", "ai"] and "content" in m and isinstance(m["content"], str) and m["content"].strip() != "" for m in chat):
            raise HTTPException(
                status_code=400,
                detail="Uploaded JSON must be a list of messages with 'role' ('human' or 'ai') and non-empty 'content'."
            )

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Uploaded file is not valid JSON. Error: {str(e)}")

    try:
        result = simulate_chat(chat, prompt_id, model_name, LANGSMITH_API_KEY, ANTHROPIC_API_KEY)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")

@app.get("/prompts")
def list_prompts():
    try:
        client = Client(api_key=LANGSMITH_API_KEY)
        offset = 0
        limit = 100
        prompt_names = []

        while True:
            response = client.list_prompts(limit=limit, offset=offset, is_public=False)

            if not response.repos:
                break

            for id, p in response:
                if id == "repos":
                    for prompt in p:
                        prompt_names.append(prompt.full_name)

            offset += limit
        return prompt_names

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch prompts: {str(e)}")

    try:
        client = Client(api_key=LANGSMITH_API_KEY)
        offset = 0
        limit = 100
        prompt_entries = []

        while True:
            response = client.list_prompts(limit=limit, offset=offset, is_public=False)

            if not response.repos:
                break

            for id, p in response:
                if id == "repos":
                    for prompt in p:
                        prompt_entries.append({
                            "id": prompt.full_name,
                            "name": prompt.name,
                            "project": prompt.repo_handle or "unknown"
                        })

            offset += limit

        return prompt_entries

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch prompts: {str(e)}")

    try:
        client = Client(api_key=LANGSMITH_API_KEY)
        prompts = client.list_prompts()
        return [
            {
                "id": f"{p.project_id}/{p.name}" if p.project_id else p.name,
                "name": p.name,
                "project": p.project_id or "personal"
            }
            for p in prompts
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch prompts: {str(e)}")