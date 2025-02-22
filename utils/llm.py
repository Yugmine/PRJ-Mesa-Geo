"""Handles calls to the large language model"""
from openai import OpenAI

client = OpenAI(
    base_url = 'http://localhost:1234/v1/',
    api_key = 'foo'
)

def generate_response(content: str) -> str:
    """Generates a response for the given prompt"""
    chat_completion = client.chat.completions.create(
        messages=[
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
