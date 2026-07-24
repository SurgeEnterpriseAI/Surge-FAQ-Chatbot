from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor

from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage


class CheckResult(BaseModel):
    approved: bool
    confidence: float = Field(ge=0, le=1)
    reason: str
    metadata: dict = Field(default_factory=dict)


_INJECTION = re.compile(r"ignore (all |previous |prior )?instructions|system prompt|developer message", re.I)
_PII = re.compile(r"\b(?:\d[ -]*?){13,16}\b|\b\d{3}-\d{2}-\d{4}\b", re.I)


def _deterministic(name: str, query: str, answer: str) -> CheckResult | None:
    text = f"{query}\n{answer}"
    if name == "prompt_injection" and _INJECTION.search(text):
        return CheckResult(approved=False, confidence=.99, reason="Prompt-injection pattern detected")
    if name == "pii" and _PII.search(answer):
        return CheckResult(approved=False, confidence=.98, reason="Potential sensitive identifier found in response")
    return None


def _check(name: str, query: str, answer: str, llm) -> dict:
    started = time.perf_counter()
    deterministic = _deterministic(name, query, answer)
    if deterministic:
        result = deterministic
    else:
        schema_llm = llm.with_structured_output(CheckResult)
        result = schema_llm.invoke([
            SystemMessage(content=("You are the " + name.replace("_", " ") +
                " safety checker. Approve only when the proposed response is safe for customer support. "
                "Return a concise reason and non-sensitive metadata.")),
            HumanMessage(content=f"User query:\n{query}\n\nProposed answer:\n{answer}"),
        ])
    return {"name": name, **result.model_dump(), "latency_ms": round((time.perf_counter() - started) * 1000, 2)}


def run_safety_checks(query: str, answer: str, llm) -> list[dict]:
    names = ["groundedness", "prompt_injection", "pii", "hallucination", "policy_compliance"]
    with ThreadPoolExecutor(max_workers=len(names)) as pool:
        return list(pool.map(lambda name: _check(name, query, answer, llm), names))
