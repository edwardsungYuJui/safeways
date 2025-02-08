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


class Guardian2Response(BaseModel):
    valid: bool


def second_guardian(
    model: str, prompt: str = None, first_output: str = None, status: str = None
):
    full_prompt = prompt
    response: ChatResponse = chat(
        model=model,
        messages=[{"role": "user", "content": full_prompt, "temperature": 0.0}],
        format=Guardian2Response.model_json_schema(),
        stream=False,
    )
    output = Guardian2Response.model_validate_json(response.message.content)
    output = output.model_dump()
    return output["valid"]


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


# model = "deepseek-r1:1.5b"
# # prompt = f"""[INST] <<SYS>>
# #     You are a helpful assistant. Please analyze the user's messages in a concise manner.
# #     Classify each conversation as "SCAM", "SUSPICIOUS", or "SAFE" based on its content.
# #     Return valid JSON with keys: "sentiment", "alert_needed" (true/false), and "explanation".
# #     <</SYS>>
# #     Analyze these chat messages briefly and respond *only* with JSON.

# #     Messages:
# #     yoyoyo
# #     [/INST]
# #     """
# response = second_guardian(model, first_output="SCAM", status="SCAM")
# print(response)
