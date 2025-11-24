# helpers/gemini.py
from google import genai
from google.genai import types
from google.genai.errors import ServerError
import time
from typing import Any, Dict, Optional


def gemini_with_file_structuredResp(
        prompt: str,
        file_to_upload: str,
        model_name="gemini-2.5-flash",
        response_mime_type="application/json"):

    # Create client (GOOGLE_API_KEY must exist in env for GitHub Actions)
    client = genai.Client()

    # Upload HAR directly (NO extension change)
    uploaded = client.files.upload(file=file_to_upload)

    max_retries = 3
    delay = 2

    for attempt in range(1, max_retries + 1):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=[prompt, uploaded],
                config={
                    "response_mime_type": response_mime_type
                }
            )
            return response.text  # Already JSON
        except Exception as e:
            print(f"Attempt {attempt} failed: {e}")
            if attempt < max_retries:
                time.sleep(delay)
                delay *= 2
            else:
                raise


def get_gemini_agent(prompt, model_name="gemini-2.5-flash",
                     sys_instruction="respond within 30 words"):
    try:
        client = genai.Client()
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=sys_instruction,
                temperature=0.1
            )
        )
        return response
    except ServerError as e:
        if e.status_code == 503:
            return gemini_retry(prompt, model_name, sys_instruction)
        else:
            raise


def gemini_retry(prompt, model_name, sys_instruction,
                 retries=5, backoff=2):
    for attempt in range(retries):
        try:
            client = genai.Client()
            return client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=sys_instruction,
                    temperature=0.1
                )
            )
        except ServerError as e:
            if e.status_code == 503:
                print(f"Retrying in {backoff}s...")
                time.sleep(backoff)
                backoff *= 2
            else:
                raise

    raise Exception("Failed after multiple retries")
