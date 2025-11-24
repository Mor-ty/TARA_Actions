from langchain.tools import tool
from google import genai
from google.genai import types
from typing import List, Dict, Optional, Literal
from pydantic import BaseModel, Field, conint
import os
from helpers.gemini import gemini_with_file_structuredResp
import pandas as pd


# -----------------------------------------------------
# Pydantic model for LLM structured response
# -----------------------------------------------------
class InsightsJTL(BaseModel):
    id: conint(ge=1)
    title: str = Field(..., min_length=3, max_length=80)
    category: Literal["Test", "Application", "Infra", "Monitoring"]
    priority: Literal["High", "Medium", "Low"]
    description: str = Field(..., max_length=200)
    concrete_changes: Optional[str] = None
    estimated_effort: Literal["small", "medium", "large"]
    expected_impact: Literal["high", "medium", "low"]


# -----------------------------------------------------
# CSV Metrics Extraction
# -----------------------------------------------------
def get_metrics(jtl_path: str):
    try:
        df = pd.read_csv(jtl_path, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(jtl_path, encoding="ISO-8859-1")

    df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]

    time_col = next((c for c in df.columns if "elapsed" in c), None)
    success_col = next((c for c in df.columns if "success" in c), None)
    timestamp_col = next((c for c in df.columns if "time_stamp" in c or "timestamp" in c), None)

    if not all([time_col, success_col, timestamp_col]):
        raise ValueError(f"Missing expected columns. Found columns: {df.columns.tolist()}")

    df[success_col] = df[success_col].astype(str).str.lower().isin(["true", "1"])

    total_requests = len(df)
    failed_requests = len(df[~df[success_col]])
    avg_response = df[time_col].mean()
    p90 = df[time_col].quantile(0.9)
    p95 = df[time_col].quantile(0.95)
    error_rate = (failed_requests / total_requests * 100) if total_requests > 0 else 0

    df[timestamp_col] = pd.to_numeric(df[timestamp_col], errors="coerce")
    test_duration_sec = (df[timestamp_col].max() - df[timestamp_col].min()) / 1000 if df[timestamp_col].max() > df[timestamp_col].min() else 0
    throughput = total_requests / test_duration_sec if test_duration_sec > 0 else 0

    return {
        "average_response_time_ms": round(avg_response, 2),
        "p90_response_time_ms": round(p90, 2),
        "p95_response_time_ms": round(p95, 2),
        "error_rate_percent": round(error_rate, 2),
        "throughput_rps": round(throughput, 2),
        "total_requests": int(total_requests),
        "failed_requests": int(failed_requests),
        "test_duration_sec": round(test_duration_sec, 2)
    }


# -----------------------------------------------------
# LangChain Tool
# -----------------------------------------------------
@tool
def insight_analytic_agent(jtl_file_with_path: str):
    """Insight Agent — Analyzes load test metrics and provides actionable insights."""

    insights = []
    metrics = get_metrics(jtl_file_with_path)

    error_rate = metrics["error_rate_percent"]
    p95 = metrics["p95_response_time_ms"]
    avg_time = metrics["average_response_time_ms"]

    # Local heuristics
    if error_rate > 5:
        insights.append("High error rate detected — check backend stability, error handling, and concurrency limits.")
    if p95 > 2000:
        insights.append("P95 latency exceeds 2 seconds — investigate DB queries, caching, or async processing.")
    if avg_time > 1000 and p95 < 2000:
        insights.append("Average response time is moderately high — consider batching, caching, or compression.")
    if not insights:
        insights.append("Performance appears stable within acceptable limits.")

    # -------------------------------------------------
    # LLM-based structured insights
    # -------------------------------------------------


    try:
        jtl_file = os.path.basename(jtl_file_with_path)
        prompt = f"""
        You are an expert performance engineer.
        Based on the following load test metrics and the attached JMeter result file: {jtl_file}, provide 3–5 short, actionable recommendations/Insights for a DevOps engineer.

        Metrics:
        - Average Response Time (ms): {avg_time}
        - P95 Latency (ms): {p95}
        - Error Rate (%): {error_rate}

        Task:
        Read the attached JMeter results (JTL — XML or CSV) file: {jtl_file} and produce between 3 and 5 short, prioritized, technically-specific recommendations/Insights for a DevOps engineer. The output MUST be a single JSON object matching provided schema:

        Rules:
        - Return structured output. No wrapper text, no extra keys.
        - Each description must reference one or more specific metrics (e.g., "p95=1200ms", "error_rate=4.2%") and include a one-line evidence snippet if taken from the JTL (e.g., "evidence: sampler 'Login' p95=1450ms, errors=12%").
        - Keep descriptions <= 200 characters.
        - Prioritize high-impact, low-effort items first.
        - Make IDs sequential starting at 1.
        - Use exact category and priority strings from the schema.

        Now read the attached file and return the JSON object.
        """

        

        with open(jtl_file_with_path, "rb") as f:
            ai_response = gemini_with_file_structuredResp(
                prompt=prompt,
                file_to_upload=f,
                Structured_class=InsightsJTL
            )

        insights.append("AI Recommendations:\n" + str(ai_response))

    except Exception as e:
        insights.append(f"LLM insights unavailable: {str(e)}")

    return {"insights": insights}


    
if __name__=='__main__':
    insight_analytic_agent("result/results.jtl")