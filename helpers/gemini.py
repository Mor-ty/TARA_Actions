# helpers/gemini.py
import os
import time
from typing import Any, Dict
from google import genai
from google.genai import types
from google.genai.errors import ServerError


def get_genai_client():
    """Return a genai.Client instance using GOOGLE_API_KEY from env."""
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("Missing GOOGLE_API_KEY environment variable!")
    return genai.Client(api_key=api_key)


def gemini_with_file_structuredResp(
        prompt: str,
        file_to_upload: str,
        model_name="gemini-2.5-flash",
        response_mime_type="application/json"):
    """
    Sends a HAR file + prompt to Gemini API and returns JSON/text response.
    Retries up to 3 times on failure.
    """
    client = get_genai_client()

    # Upload HAR file with explicit MIME type
    uploaded = client.files.upload(
        file=file_to_upload,
        mime_type="application/json"
    )

    max_retries = 3
    delay = 2

    for attempt in range(1, max_retries + 1):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=[prompt, uploaded],
                config={"response_mime_type": response_mime_type}
            )
            return response.text  # JSON as string
        except Exception as e:
            print(f"Attempt {attempt} failed: {e}")
            if attempt < max_retries:
                time.sleep(delay)
                delay *= 2
            else:
                raise


def get_gemini_agent(prompt: str,
                     model_name="gemini-2.5-flash",
                     sys_instruction="respond within 30 words"):
    """Send a text-only prompt to Gemini with retry on overload."""
    try:
        client = get_genai_client()
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


def gemini_retry(prompt: str, model_name: str, sys_instruction: str,
                 retries=5, backoff=2):
    """Retry wrapper for get_gemini_agent on 503 errors."""
    for attempt in range(retries):
        try:
            client = get_genai_client()
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
                print(f"Model overloaded. Retrying in {backoff}s...")
                time.sleep(backoff)
                backoff *= 2
            else:
                raise
    raise Exception("Failed after multiple retries.")
