from langsmith import Client
import os
from dotenv import load_dotenv

load_dotenv()
client = Client(api_key=os.getenv("LANGSMITH_API_KEY"))

prompt_names = []
offset = 0
limit = 100

while True:
    response = client.list_prompts(limit=limit, offset=offset,is_public=False)
    if not response.repos:
        break

    for id, p in response:
        if id == "repos":
            for prompt in p:
                prompt_names.append(prompt.full_name)

    offset += limit

    print(len(prompt_names))
    print(prompt_names[-1])


