"""Handles calls to the large language model"""
import os
from openai import OpenAI

client = OpenAI(
    base_url = 'http://localhost:1234/v1/',
    api_key = 'foo'
)

def generate_response(system_prompt: str, content: str) -> str:
    """Generates a response for the given prompt"""
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": content,
            }
        ],
        model='meta-llama-3-8b-instruct',
        max_tokens=1024,
        temperature=0.7
    )
    return chat_completion.choices[0].message.content

def generate_prompt(inputs: list, prompt_file: str) -> str:
    """
    Fills in the chosen prompt template with the provided inputs.

    Code + template format partially taken from:
    https://github.com/joonspk-research/generative_agents/
    """
    path = os.path.join("./prompt_templates", prompt_file + ".txt")
    with open(path, "r", encoding="utf-8") as f:
        prompt = f.read()
    for idx, input_val in enumerate(inputs):
        prompt = prompt.replace(f"<INPUT {idx}>", input_val)
    if "<END COMMENT>" in prompt:
        prompt = prompt.split("<END COMMENT>")[1]
    return prompt.strip()
