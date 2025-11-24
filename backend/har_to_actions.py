import json
from helpers.gemini import get_gemini_agent, gemini_with_file_structuredResp
from helpers.utils import change_extension
from pydantic import BaseModel, Field
from typing import List, Dict

class Action(BaseModel):
    name: str = Field(..., description="Business-action name, e.g., Login, Search")
    method: str = Field(..., description="HTTP method, either GET or POST")
    path: str = Field(..., description="Canonical path for the action")
    params: List[str] = Field(default_factory=list, description="List of parameter names")



def createActions(har_file_path:str):
    
    har_txt_file = change_extension(har_file_path)

    har_to_actions_prompt='''You are a HAR-to-ACTION extractor.  
Input: a HAR file (JSON) containing HTTP request entries (the standard Browser HAR structure under "log.entries").  
Output: a single JSON object with a top-level array field named "ACTIONS". **Return ONLY valid JSON** (no explanation, no commentary).

GOALS
1. Identify meaningful user/business actions.
2. Filter out static assets.
3. For each action produce a single representative entry containing name, canonical HTTP method, canonical path, list of parameter names, and optional metadata (sample_paths and detected_param_sources).

PROCESS (apply in this exact order)
A. Parse HAR:
   - Use `har["log"]["entries"]` as the input list. Each entry has a "request" object with fields: "method", "url", "headers", "postData" (optional).
B. Filter out static assets and known tracking domains:
   - Discard requests whose path ends with extensions: `.css .js .jpg .jpeg .png .gif .svg .ico .map .webmanifest .woff .woff2 .ttf .eot .otf .json` (case-insensitive).
   - Discard requests whose host/domain belongs to common analytics/third-party systems (examples to treat as noise): domains containing `googletagmanager`, `google-analytics.com`, `gtag`, `g/collect`, `cloudflareinsights`, `ads`, `doubleclick`, `facebook.net`, `googlesyndication` or `cdn-cgi`. (If hostname matches any of these substrings, skip.)
C. Normalize path:
   - Use `urlparse(url).path`. Remove trailing slash unless it's the root `/`.
   - Keep path only (exclude query string) for canonical "path" field, except you will still inspect the query string to collect parameter names.
D. Extract parameter names:
   - From query string: parse `?a=1&b=2` and collect parameter keys.
   - From `postData`: handle both `postData.params` (form data array), raw urlencoded bodies (`k=v&x=y`) and raw JSON bodies. Collect keys:
     • If `postData.params` exists, use those `name` fields.
     • Else if `postData.mimeType` contains `application/x-www-form-urlencoded` or the `postData.text` contains `=` parse as urlencoded form and collect keys.
     • Else try to parse `postData.text` as JSON; if root is object, collect its keys.
   - Normalize `__RequestVerificationToken` → `csrf_token`.
   - Trim whitespace from parameter names, discard empty names.
G. Canonical method and path selection:
   - If the group includes `POST`, choose canonical method `"POST"`. Otherwise use the most common method, or `"GET"` by default.
   - Choose a representative path: the shortest path observed for the action (ties broken lexicographically).
H. Produce final ACTION entry fields:
   For each grouped action produce:
   {
     "name": <string, CamelCase business name, e.g. "AddToCart">,
     "method": <"GET" or "POST">,
     "path": <canonical path string, exactly the path portion, e.g. "/addproducttocart/catalog/17/1/1">,
     "params": <array of strings, sorted alphabetically, unique>,
     "sample_paths": <array of up to 5 example paths observed for the action>,
     "detected_param_sources": <object mapping paramName -> array of sources: one or more of ["query", "form", "json", "header"]>
   }
I. Output rules:
   - The output MUST be a single JSON object exactly: `{ "ACTIONS": [ ... ] }`
   - Do not output any additional text, commentary, or markdown.
   - Ensure JSON is well-formed and UTF-8 encoded.
   - Limit `params` to unique parameter names. If an action has no params, return an empty array `[]`.
   - For `detected_param_sources`, provide only the sources you actually detected for that param across the HAR entries (e.g. `{"csrf_token":["form"]}`).
   - Use `csrf_token` instead of `__RequestVerificationToken` (normalization applied).
   - Make names unique; if two actions would have identical names append a numeric suffix like `AddToCart2`.
J. Additional constraints and quality checks:
   - Exclude any action whose only sample_paths are blacklisted analytics/tracker endpoints.
   - If an action looks like purely static assets or 3rd-party tracking, do not include it.

If the input HAR is extremely large, process entries and return action groups based on observed data. Produce only the final JSON object.
'''
    res = gemini_with_file_structuredResp(prompt=har_to_actions_prompt, file_to_upload=har_txt_file,Structured_class=Action)
    print(res)
    return res


    
if __name__=='__main__':
    createActions("har_files/demo.har")
