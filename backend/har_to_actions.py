import json
from helpers.gemini import get_gemini_agent, gemini_with_file_structuredResp
from helpers.utils import change_extension
from pydantic import BaseModel, Field
from typing import List


class Action(BaseModel):
    name: str = Field(..., description="Business-action name, e.g., Login, Search")
    method: str = Field(..., description="HTTP method, either GET or POST")
    path: str = Field(..., description="Canonical path for the action")
    params: List[str] = Field(default_factory=list, description="List of parameter names")


def createActions(har_file_path: str):

    # Convert HAR → TXT (your helper)
    har_txt_file = change_extension(har_file_path)

    har_to_actions_prompt = '''
    You are a HAR-to-ACTION extractor.  
    Input: a HAR file (JSON) containing HTTP request entries (the standard Browser HAR structure under "log.entries").  
    Output: a single JSON object with a top-level array field named "ACTIONS". **Return ONLY valid JSON** (no explanation, no commentary).

    GOALS
    1. Identify meaningful user/business actions.
    2. Filter out static assets.
    3. For each action produce a single representative entry containing name, canonical HTTP method, canonical path, list of parameter names, and optional metadata (sample_paths and detected_param_sources).

    PROCESS (apply in this exact order)
    A. Parse HAR:
      - Use `har["log"]["entries"]` as the input list.
    B. Filter out static assets and tracking.
    C. Normalize path.
    D. Extract parameter names.
    G. Canonical method & path.
    H. Produce final ACTION entries.

    I. Output rules:
      - Output ONLY: { "ACTIONS": [...] }
      - No commentary.
      - Valid JSON.

    If input HAR is large, summarize patterns but still output full ACTION objects.
    '''

    # Call Gemini with file + structured response model
    res = gemini_with_file_structuredResp(
        prompt=har_to_actions_prompt,
        file_to_upload=har_txt_file,
        Structured_class=Action
    )

    print(res)

    # Save result for CI/CD workflows
    with open("actions_output.json", "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)

    return res


if __name__ == '__main__':
    createActions("har_files/demo.har")
