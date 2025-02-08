"""
This file utilize Ollama as the second layer of our scam detection.
"""

import requests
from ollama import chat
from ollama import ChatResponse
from pydantic import BaseModel


class GuardianResponse(BaseModel):
    sentiment: str
    alert_needed: bool
    explanation: str


def second_guardian(model: str, prompt: str, first_output: str):
    full_prompt = (
        prompt + "\n\n" + "Here is the first guardian's reasoning:\n" + first_output
    )
    response: ChatResponse = chat(
        model=model,
        messages=[{"role": "user", "content": full_prompt, "temperature": 0.0}],
        format=GuardianResponse.model_json_schema(),
        stream=False,
    )
    output = GuardianResponse.model_validate_json(response.message.content)
    return output


def first_guardian(
    model: str,
    prompt: str = None,
):
    full_prompt = prompt
    response: ChatResponse = chat(
        model=model,
        messages=[{"role": "user", "content": full_prompt, "temperature": 0.0}],
        format=GuardianResponse.model_json_schema(),
        stream=False,
    )
    output = GuardianResponse.model_validate_json(response.message.content)
    output = output.model_dump_json()
    return output


if __name__ == "__main__":
    model = "deepseek-r1:8b"
    prompt = f"""[INST] <<SYS>>
        You are a helpful assistant. Please analyze the user's messages in a concise manner.
        Classify each conversation as "SCAM", "SUSPICIOUS", or "SAFE" based on its content.
        Return valid JSON with keys: "sentiment", "alert_needed" (true/false), and "explanation".
        <</SYS>>
        Analyze these chat messages briefly and respond *only* with JSON.
        
        Messages:
        yoyoyo
        [/INST]
        """
    response = first_guardian(model, prompt)
    print(response)
