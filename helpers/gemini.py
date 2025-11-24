from google import genai
from google.genai import types
import time
from google.genai.errors import ServerError
import json
from typing import List, Dict
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional


class GeminiGenericResponse(BaseModel):
    text: Optional[str] = None
    tokens: Dict[str, Any] = {}
    model: Optional[str] = None
    metadata: Dict[str, Any] = {}
    error: Optional[str] = None


def gemini_with_file_structuredResp(prompt:str,file_to_upload:str,model_name="gemini-2.5-flash",Structured_class=GeminiGenericResponse,response_mime_type="application/json"):
    client = genai.Client()

    # json/har file is not supported in gemini (changed its extention)
    uploaded_file = client.files.upload(file=file_to_upload)

    model_name = model_name
    max_retries = 3
    delay = 2  # seconds


    for attempt in range(1, max_retries+1):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=[ prompt, uploaded_file ],
                config ={
                "response_mime_type": response_mime_type,
                "response_schema": list[Structured_class]
            }
                # config=genai.types.GenerateContentConfig(
                #     system_instruction="You are a HAR-to-ACTION extractor. Your output must be a single JSON object with a top-level array field named 'ACTIONS'. Return ONLY valid JSON, no explanations, no commentary."
                # ) if hasattr(genai.types, 'GenerateContentConfig') else {}
            )
            print("Response:", response.text)
            return response.text
        
        except Exception as e:
            print(f"Attempt {attempt} failed with error: {e}")
            if attempt < max_retries:
                time.sleep(delay)
                delay *= 2  # Exponential backoff
            else:
                raise Exception("Failed after all retries.")

def get_gemini_agent(prompt,model_name="gemini-2.5-flash", sys_instruction = "response should be within 30 words"):
    try:
        genclient = genai.Client()
        response = genclient.models.generate_content(
            model = model_name,
            contents = prompt,
            config = types.GenerateContentConfig(
                system_instruction = sys_instruction,
                temperature=0.1
                )
        )

        return response
    except ServerError as e:
        if e.status_code == 503:
            print(f"==================Model overloaded. Retrying...===========================")
            gemini_retry(prompt, model_name,sys_instruction=sys_instruction)
        else:
            raise



def gemini_retry(prompt, model_name, sys_instruction, retries=5, backoff=2, ):
    for attempt in range(retries):
        try:
            genclient = genai.Client()
            response = genclient.models.generate_content(
                model = model_name,
                contents = prompt,
                config = types.GenerateContentConfig(
                    system_instruction = sys_instruction,
                    temperature=0.1
                    )
            )

            return response
        except ServerError as e:
            if e.status_code == 503:
                print(f"Model overloaded. Retrying in {backoff} seconds...")
                time.sleep(backoff)
                backoff *= 2  # Exponential backoff
            else:
                raise
    raise Exception("Failed after multiple retries.")



if __name__=="__main__":
    prompt='explain gen ai api'
    res = get_gemini_agent(prompt,"gemini-2.5-flash")

    print(res.text)
