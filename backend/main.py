from fastapi import FastAPI, UploadFile, Form, HTTPException
from chat_simulator import simulate_chat
from langsmith import Client
import json
from dotenv import load_dotenv
import os
import re
from fastapi import Query
from fastapi.responses import JSONResponse

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
async def simulate(
    file: UploadFile = None,
    prompt_id: str = Form(...),
    model_name: str = Form(...),
    variables_json: str = Form("{}", description="User-provided variables as JSON string")
):
    if file is None:
        raise HTTPException(status_code=400, detail="No file uploaded. Please upload a chat JSON file.")
    if not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Only .json files are accepted. Please upload a valid JSON file.")
    if prompt_id.strip() == "":
        raise HTTPException(status_code=400, detail="Prompt ID is missing. Please enter a LangSmith prompt ID.")
    if model_name.strip() == "":
        raise HTTPException(status_code=400, detail="Model name is missing. Please select a model.")

    # Load uploaded JSON content
    try:
        content = await file.read()
        chat = json.loads(content)
        if not isinstance(chat, list) or not all(
            isinstance(m, dict)
            and "role" in m
            and m["role"] in ["human", "ai"]
            and "content" in m
            and isinstance(m["content"], str)
            for m in chat
        ):
            raise HTTPException(
                status_code=400,
                detail="Uploaded JSON must be a list of messages with 'role' ('human' or 'ai') and non-empty 'content'."
            )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Uploaded file is not valid JSON. Error: {str(e)}")

    # Parse dynamic variables from frontend
    try:
        user_vars = json.loads(variables_json)
        assert isinstance(user_vars, dict)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid variables JSON: {str(e)}")

    # Simulate conversation
    try:
        result = simulate_chat(chat, prompt_id, model_name, LANGSMITH_API_KEY, user_vars)
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Model or prompt error: {str(e)}")

    except Exception as e:
        err_msg = str(e).lower()
        if "quota" in err_msg or "rate limit" in err_msg or "exceeded" in err_msg or "overloaded" in err_msg:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit or quota exceeded for this model. Please try again later or switch models."}
            )
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

@app.get("/")
def read_root():
    return JSONResponse({"message": "Evaluation Simulation backend is live!"})

@app.get("/prompt-variables")
def get_prompt_variables(prompt_id: str = Query(...)):
    try:
        client = Client(api_key=os.getenv("LANGSMITH_API_KEY"))
        prompt = client.pull_prompt(prompt_id)

        # Remove fields you handle internally
        ignored = {"chat_history", "question"}
        user_vars = sorted(var for var in prompt.input_variables if var not in ignored)

        return {"variables": user_vars}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract variables: {str(e)}")
