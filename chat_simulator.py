from langsmith import Client
from langchain_anthropic import ChatAnthropic

def simulate_chat(messages, prompt_id, model_name, langsmith_api_key, anthropic_api_key):
    client = Client(api_key=langsmith_api_key)
    prompt_id = "mv_retention_testing"
    prompt = client.pull_prompt(prompt_id)  # THIS WILL NOW WORK

    llm = ChatAnthropic(
        model=model_name,
        api_key=anthropic_api_key
    )

    chain = prompt | llm

    history = []
    new_responses = []

    for msg in messages:
        if msg["role"] == "human":
            history.append({"role": "human", "content": msg["content"]})
            result = chain.invoke({
                "chat_history": history,
                "question": msg["content"],
                "VisaExpiryDate": "missing",
                "ContractExpiryDate": "missing",
                "MaidBasicSalary": "missing"
            })
            history.append({"role": "ai", "content": result.content})
            new_responses.append({"role": "ai", "content": result.content})
        else:
            continue

    return history
