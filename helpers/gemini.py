# helpers/gemini.py
import os
import time
from google import genai
from google.genai import types
from google.genai.errors import ServerError, APIError

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
        response_mime_type="application/json",
        retries=5,
        backoff=2):
    """
    Sends a HAR file + prompt to Gemini API and returns JSON/text response.
    Retries on 500/503 errors with exponential backoff.
    """
    # Ensure HAR has .json extension
    base, ext = os.path.splitext(file_to_upload)
    if ext.lower() != ".json":
        json_file = base + ".json"
        os.rename(file_to_upload, json_file)
    else:
        json_file = file_to_upload

    client = get_genai_client()

    # Upload file
    uploaded = None
    for attempt in range(1, retries + 1):
        try:
            uploaded = client.files.upload(file=json_file)
            break
        except (ServerError, APIError) as e:
            print(f"Upload attempt {attempt} failed: {e}")
            if attempt < retries:
                time.sleep(backoff)
                backoff *= 2
            else:
                raise

    # Generate content
    delay = backoff
    for attempt in range(1, retries + 1):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=[prompt, uploaded],
                config={"response_mime_type": response_mime_type}
            )
            return response.text
        except (ServerError, APIError) as e:
            print(f"Request attempt {attempt} failed: {e}")
            if attempt < retries:
                time.sleep(delay)
                delay *= 2
            else:
                raise


def get_gemini_agent(prompt: str,
                     model_name="gemini-2.5-flash",
                     sys_instruction="respond within 30 words",
                     retries=5,
                     backoff=2):
    """Send a text-only prompt to Gemini with retry on overload."""
    for attempt in range(1, retries + 1):
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
            print(f"Text request attempt {attempt} failed: {e}")
            if e.status_code in [500, 503] and attempt < retries:
                time.sleep(backoff)
                backoff *= 2
            else:
                raise
