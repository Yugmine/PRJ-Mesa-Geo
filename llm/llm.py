"""Handles calls to the large language model"""
import os
import sqlite3
from sqlite3 import Connection, Cursor
from openai import OpenAI

client = OpenAI(
    base_url = 'http://localhost:1234/v1/',
    api_key = 'foo'
)

def create_db_connection() -> tuple[Connection, Cursor]:
    """ 
    Returns:
        Connection to the cache database
        Cursor to the database
    """
    con = sqlite3.connect("./llm/cache.db")
    cur = con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS cache (system_prompt, content, response)")
    return con, cur

def query_cache(cur: Cursor, system_prompt: str, content: str) -> str | None:
    """Queries the cache for a response to the given prompt"""
    params = (system_prompt, content)
    res = cur.execute("SELECT * FROM cache WHERE system_prompt=? AND content=?", params)
    entry = res.fetchone()
    if entry is not None:
        return entry[2]
    return None

def query_llm(system_prompt: str, content: str) -> str:
    """Gets a response from the LLM for the given prompt"""
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

def generate_response(system_prompt: str, content: str) -> str:
    """Generates a response for the given prompt"""
    con, cur = create_db_connection()
    response = query_cache(cur, system_prompt, content)
    if response is None:
        response = query_llm(system_prompt, content)
        data = (system_prompt, content, response)
        cur.execute("INSERT INTO cache VALUES (?, ?, ?)", data)
        con.commit()
    con.close()
    return response

def drop_cache(system_prompt: str, content: str) -> None:
    """
    Drops the given entry from the cache,
    so that it can be re-generated on the next call.
    """
    con, cur = create_db_connection()
    params = (system_prompt, content)
    cur.execute("DELETE FROM cache WHERE system_prompt=? AND content=?", params)
    con.commit()
    con.close()

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
        prompt = prompt.replace(f"<INPUT {idx}>", str(input_val))
    if "<END COMMENT>" in prompt:
        prompt = prompt.split("<END COMMENT>")[1]
    return prompt.strip()
