import openai
import os

openai.api_key = os.getenv("OPENAI_API_KEY")

def generate_structured_note(query: str, context: str) -> str:
    """Generate a structured concept note from query and context"""
    prompt = f"""
    You are an instructor generating a concise, structured note for a Data Science student.
    Concept: {query}
    Context: {context}
    Format the note as:
    - Definition
    - Key Ideas
    - Real-world Examples
    - Summary
    """

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an expert instructor writing study notes."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.4,
    )

    return response["choices"][0]["message"]["content"].strip()
