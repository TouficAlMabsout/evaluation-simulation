from langsmith import Client
from langchain_anthropic import ChatAnthropic

def simulate_chat(messages, prompt_id, model_name, langsmith_api_key, anthropic_api_key, extra_vars=None):
    client = Client(api_key=langsmith_api_key)
    prompt = client.pull_prompt(prompt_id)

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

            inputs = {
                "chat_history": history,
                "question": msg["content"]
            }

            # Merge dynamic variables
            if extra_vars:
                inputs.update(extra_vars)

            result = chain.invoke(inputs)
            history.append({"role": "ai", "content": result.content})
            new_responses.append({"role": "ai", "content": result.content})

    return history
