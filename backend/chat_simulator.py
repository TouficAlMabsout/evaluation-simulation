import os

# Prevent LangSmith from injecting `proxies`
os.environ["LANGCHAIN_TRACING_V2"] = "false"

from dotenv import load_dotenv
from langsmith import Client
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

def simulate_chat(messages, prompt_id, model_name, langsmith_api_key, extra_vars=None):
    # Set LangSmith API key
    client = Client(api_key=langsmith_api_key)
    prompt = client.pull_prompt(prompt_id)

    # Parse model family
    if ":" in model_name:
        family, submodel = model_name.split(":", 1)
    else:
        family, submodel = "claude", model_name

    # ✅ Set API keys via env vars only, NOT as constructor args
    if family == "claude":
        os.environ["ANTHROPIC_API_KEY"] = os.environ.get("ANTHROPIC_API_KEY")
        llm = ChatAnthropic(model=submodel)

    elif family == "openai":
        os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY")
        llm = ChatOpenAI(model=submodel)

    elif family == "gemini":
        os.environ["GOOGLE_API_KEY"] = os.environ.get("GEMINI_API_KEY")
        llm = ChatGoogleGenerativeAI(
            model=submodel,
            convert_system_message_to_human=True
        )

    else:
        raise ValueError(f"Unsupported model family: {family}")

    # Run the simulation
    chain = prompt | llm
    history = []
    new_responses = []

    for msg in messages:
        if msg["role"] == "human":
            history.append({"role": "human", "content": msg["content"]})
            inputs = {
                "chat_history": history,
                "question": msg["content"]
            }
            if extra_vars:
                inputs.update(extra_vars)
            result = chain.invoke(inputs)
            history.append({"role": "ai", "content": result.content})
            new_responses.append({"role": "ai", "content": result.content})

    return history
