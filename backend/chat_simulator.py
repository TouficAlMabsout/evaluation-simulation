from langsmith import Client
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import os

load_dotenv()

def simulate_chat(messages, prompt_id, model_name, langsmith_api_key, anthropic_api_key=None, extra_vars=None):
    client = Client(api_key=langsmith_api_key)
    prompt = client.pull_prompt(prompt_id)

    # Parse model family
    if ":" in model_name:
        family, submodel = model_name.split(":", 1)
    else:
        family, submodel = "claude", model_name  # default

    # Select correct LLM
    if family == "claude":
        os.environ["ANTHROPIC_API_KEY"] = anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")
        llm = ChatAnthropic(model=submodel)

    elif family == "openai":
        os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY")
        llm = ChatOpenAI(model=submodel)

    elif family == "gemini":
        os.environ["GOOGLE_API_KEY"] = os.environ.get("GEMINI_API_KEY")
        llm = ChatGoogleGenerativeAI(
            model=submodel,
            convert_system_message_to_human=True  # ✅ Gemini system message fix
        )
    else:
        raise ValueError(f"Unsupported model family: {family}")

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
