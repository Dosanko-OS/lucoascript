from __future__ import annotations

import ollama as py_ollama


def ask(
    model: str,
    prompt: str,
):
    return py_ollama.chat(
        model=model,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )


EXPORTS = {
    "ask": ask
}