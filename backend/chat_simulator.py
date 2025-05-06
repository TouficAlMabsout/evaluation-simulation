import os
os.environ["LANGCHAIN_TRACING_V2"] = "false"  # ✅ Prevents LangSmith from injecting `proxies`

from dotenv import load_dotenv
from langsmith import Client
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

def simulate_chat(messages, prompt_id, model_name, langsmith_api_key, extra_vars=None):
    client = Client(api_key=langsmith_api_key)
    prompt = client.pull_prompt(prompt_id)

    if ":" in model_name:
        family, submodel = model_name.split(":", 1)
    else:
        family, submodel = "claude", model_name

    if family == "claude":
        llm = ChatAnthropic(
            model=submodel,
            api_key=os.environ.get("ANTHROPIC_API_KEY")
        )
    elif family == "openai":
        llm = ChatOpenAI(
            model=submodel,
            api_key=os.environ.get("OPENAI_API_KEY")
        )
    elif family == "gemini":
        llm = ChatGoogleGenerativeAI(
            model=submodel,
            google_api_key=os.environ.get("GEMINI_API_KEY"),
            convert_system_message_to_human=True
        )
    else:
        raise ValueError(f"Unsupported model family: {family}")

    chain = prompt | llm
    history = []
    new_responses = []

    for msg in messages:
        if msg["role"] == "human":
            history.append({"role": "human", "content": msg["content"]})
            inputs = {"chat_history": history, "question": msg["content"]}
            if extra_vars:
                inputs.update(extra_vars)
            result = chain.invoke(inputs)
            history.append({"role": "ai", "content": result.content})
            new_responses.append({"role": "ai", "content": result.content})

    return history
