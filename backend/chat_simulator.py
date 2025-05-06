import os
from dotenv import load_dotenv

load_dotenv()

def simulate_chat(messages, prompt_id, model_name, langsmith_api_key, extra_vars=None):
    from langsmith import Client

    # 🔐 Set env vars *before* importing SDKs
    if "claude" in model_name:
        os.environ["ANTHROPIC_API_KEY"] = os.environ.get("ANTHROPIC_API_KEY")
    elif "openai" in model_name:
        os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY")
    elif "gemini" in model_name:
        os.environ["GOOGLE_API_KEY"] = os.environ.get("GEMINI_API_KEY")

    from langchain_anthropic import ChatAnthropic
    from langchain_openai import ChatOpenAI
    from langchain_google_genai import ChatGoogleGenerativeAI

    client = Client(api_key=langsmith_api_key)
    prompt = client.pull_prompt(prompt_id)

    if ":" in model_name:
        family, submodel = model_name.split(":", 1)
    else:
        family, submodel = "claude", model_name

    if family == "claude":
        llm = ChatAnthropic(model=submodel)

    elif family == "openai":
        llm = ChatOpenAI(model=submodel)

    elif family == "gemini":
        llm = ChatGoogleGenerativeAI(
            model=submodel,
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
