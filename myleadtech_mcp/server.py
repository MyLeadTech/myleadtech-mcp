"""MyLeadTech HVAC MCP server (stdio).

Local MCP server: it runs on your machine and exposes the same seven read-only
tools as the hosted server (https://mcp.myleadtech.app/mcp/).
Each tool calls the MyLeadTech REST API (https://api.myleadtech.app/v1) with your
API key. The manuals and the index stay on the MyLeadTech side: nothing is
bundled here, and the key decides what you can read and how many units you use.

Environment:
  MYLEADTECH_API_KEY   required, key from https://web.myleadtech.app
  MYLEADTECH_API_URL   optional, defaults to https://api.myleadtech.app
  MYLEADTECH_ENABLE_LOOKUP_FAULT_CODE=0
                       optional: do not register lookup_fault_code (on by default since
                       the API serves it, 14/11/2026)

Retries: 429 rate_limited, 503, 504 and network timeouts are retried at most 3 times,
always with the SAME Idempotency-Key as the first attempt, so a retried request is
charged once. quota_exceeded, not_entitled, conflict and other 4xx are never retried.
Errors are raised as "<code>: <message> (request_id=...)".
"""

from __future__ import annotations

import os
import time
import uuid
from typing import Any, Callable, Literal

import httpx
from mcp.server.fastmcp import FastMCP, Image
from mcp.types import ToolAnnotations

from myleadtech_mcp import __version__

MAX_RETRIES = 3
MAX_WAIT_S = 10.0
RETRYABLE = (429, 503, 504)
NEVER_RETRY = ("quota_exceeded", "not_entitled", "forbidden", "unauthorized", "conflict", "invalid_request")
FAULT_CODE_PATH = os.environ.get("MYLEADTECH_FAULT_CODE_PATH", "/v1/fault-codes/lookup")
_sleep: Callable[[float], None] = time.sleep  # remplaçable en test

API_URL = os.environ.get("MYLEADTECH_API_URL", "https://api.myleadtech.app").rstrip("/")
TIMEOUT = httpx.Timeout(60.0, connect=10.0)

mcp = FastMCP(
    "MyLeadTech",
    instructions=(
        "HVAC service knowledge cited to OEM manual pages. Start with resolve_equipment "
        "(not billed) when a model reference is known; answers are empty rather than guessed."
    ),
)


def _headers() -> dict[str, str]:
    key = os.environ.get("MYLEADTECH_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "MYLEADTECH_API_KEY is not set. Create a key at https://web.myleadtech.app "
            "(a free sandbox of 100 units a month is included)."
        )
    return {"Authorization": f"Bearer {key}", "User-Agent": f"myleadtech-mcp/{__version__}"}


def _error(response: httpx.Response) -> RuntimeError:
    """Message + request_id, jamais le corps brut."""
    try:
        body = response.json()
    except ValueError:
        body = {}
    err = (body.get("error") or {}) if isinstance(body, dict) else {}
    rid = response.headers.get("X-Request-Id") or (body.get("request_id") if isinstance(body, dict) else None)
    code = err.get("code") or f"http_{response.status_code}"
    return RuntimeError(f"{code}: {err.get('message') or response.reason_phrase} (request_id={rid})")


def _wait(response: httpx.Response | None, attempt: int) -> float | None:
    """Délai avant reprise, ou None si on ne reprend pas."""
    if attempt > MAX_RETRIES:
        return None
    if response is None:  # erreur réseau / timeout
        return min(MAX_WAIT_S, 0.5 * 2 ** (attempt - 1))
    if response.status_code not in RETRYABLE:
        return None
    try:
        err = (response.json().get("error") or {})
    except (ValueError, AttributeError):
        err = {}
    if err.get("code") in NEVER_RETRY:
        return None
    retry_after = err.get("retry_after_seconds")
    if retry_after is None:
        try:
            retry_after = float(response.headers.get("Retry-After") or "")
        except ValueError:
            retry_after = None
    if retry_after is None:
        return min(MAX_WAIT_S, 0.5 * 2 ** (attempt - 1))
    return None if retry_after > MAX_WAIT_S else max(0.0, float(retry_after))


def _call(method: str, path: str, *, json: dict | None = None, params: dict | None = None,
          idempotency: str | None = None) -> httpx.Response:
    """Un appel logique : la clé d'idempotence est fixée UNE fois ; chaque reprise la réutilise."""
    headers = _headers()
    if idempotency:
        headers["Idempotency-Key"] = idempotency
    attempt = 0
    while True:
        attempt += 1
        try:
            with httpx.Client(base_url=API_URL, timeout=TIMEOUT) as client:
                response = client.request(method, path, json=json, params=params, headers=headers)
        except httpx.TransportError as exc:
            wait = _wait(None, attempt)
            if wait is None:
                raise RuntimeError(f"network: {exc.__class__.__name__} after {attempt} attempts "
                                   "(request_id=none)") from None
            _sleep(wait)
            continue
        if response.status_code < 400:
            return response
        wait = _wait(response, attempt)
        if wait is None:
            return response
        _sleep(wait)


def _json(response: httpx.Response) -> dict[str, Any]:
    if response.status_code >= 400:
        raise _error(response)
    try:
        return response.json()
    except ValueError:
        raise RuntimeError(f"invalid_response: not JSON (request_id={response.headers.get('X-Request-Id')})") from None


def _query(question: str, brand, model_reference, fault_code, language, limit,
           max_chars: int | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {"question": question, "language": language, "limit": limit}
    for name, value in (("brand", brand), ("model_reference", model_reference), ("fault_code", fault_code)):
        if value:
            body[name] = value
    if max_chars is not None:  # absent = défaut serveur (480) : même empreinte d'idempotence qu'avant
        body["max_chars"] = max_chars
    return body


def _read(title: str, billed: bool = False) -> ToolAnnotations:
    return ToolAnnotations(title=title, readOnlyHint=True, destructiveHint=False,
                           idempotentHint=not billed, openWorldHint=False)


@mcp.tool(
    name="resolve_equipment",
    title="Resolve HVAC equipment",
    description="Resolve an HVAC model or nameplate reference to brand, family and documentation coverage. Not billed.",
    annotations=_read("Resolve HVAC equipment"),
)
def resolve_equipment(reference: str, market: str = "us", language: str = "en-US") -> dict[str, Any]:
    return _json(_call("POST", "/v1/equipment/resolve",
                       json={"reference": reference, "market": market, "language": language}))


@mcp.tool(
    name="search_hvac_documents",
    title="Search HVAC documents",
    description="Search OEM HVAC manuals by question, brand, model reference or fault code. Returns bounded passages with citations (document, page). Billed: 1 unit when status is ok.",
    annotations=_read("Search HVAC documents", billed=True),
)
def search_hvac_documents(question: str, brand: str | None = None, model_reference: str | None = None,
                          fault_code: str | None = None, language: str = "en-US", limit: int = 5,
                          max_chars: int | None = None, operation_id: str | None = None) -> dict[str, Any]:
    return _json(_call("POST", "/v1/search",
                       json=_query(question, brand, model_reference, fault_code, language, limit, max_chars),
                       idempotency=operation_id or str(uuid.uuid4())))


@mcp.tool(
    name="get_hvac_source",
    title="Get cited source",
    description="Return the passage and bounded context of a source already cited by search or answer.",
    annotations=_read("Get cited source"),
)
def get_hvac_source(source_id: str) -> dict[str, Any]:
    return _json(_call("GET", f"/v1/sources/{source_id}"))


@mcp.tool(
    name="answer_hvac_question",
    title="Answer HVAC question",
    description="Answer an HVAC service question with citations to the OEM manual page it came from. Returns empty rather than guessing when no source supports an answer. Billed: 1 unit when status is ok and at least one claim rests on a source established for the equipment; an ok answer from documentation not confirmed for the unit is not billed (usage.debited=false). audience: technician (default) or homeowner.",
    annotations=_read("Answer HVAC question", billed=True),
)
def answer_hvac_question(question: str, brand: str | None = None, model_reference: str | None = None,
                         fault_code: str | None = None, language: str = "en-US", limit: int = 5,
                         operation_id: str | None = None,
                         audience: Literal["technician", "homeowner"] = "technician",
                         max_chars: int | None = None) -> dict[str, Any]:
    body = _query(question, brand, model_reference, fault_code, language, limit, max_chars)
    if audience != "technician":  # défaut absent du corps : même empreinte qu'avant
        body["audience"] = audience
    return _json(_call("POST", "/v1/answers", json=body, idempotency=operation_id or str(uuid.uuid4())))


@mcp.tool(
    name="get_hvac_document_page",
    title="Get manual page",
    description="Page or zone cited as a PNG image. The PDF is not provided.",
    annotations=_read("Get manual page"),
)
def get_hvac_document_page(document_version_id: str, page_number: int, region: str | None = None) -> Image:
    params: dict[str, Any] = {"format": "png"}
    if region:
        params["region"] = region
    response = _call("GET", f"/v1/documents/{document_version_id}/pages/{page_number}", params=params)
    if response.status_code >= 400:
        _json(response)
    return Image(data=response.content, format="png")


@mcp.tool(
    name="get_usage",
    title="Get usage",
    description="Return the account's plan, monthly allowance, units used and remaining, and the end of the current window (window_end). Not billed. API keys need any MyLeadTech scope; OAuth needs usage.read.",
    annotations=_read("Get usage"),
)
def get_usage() -> dict[str, Any]:
    return _json(_call("GET", "/v1/usage"))


def lookup_fault_code(code: str, brand: str | None = None, model_reference: str | None = None,
                      language: str = "en-US", operation_id: str | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {"code": code, "language": language}
    if brand:
        body["brand"] = brand
    if model_reference:
        body["model_reference"] = model_reference
    # préfixe fc: : distingue la recherche de code d'une recherche libre côté ledger
    return _json(_call("POST", FAULT_CODE_PATH, json=body, idempotency=operation_id or f"fc:{uuid.uuid4()}"))


def register_optional_tools() -> None:
    """lookup_fault_code : actif par défaut (servi par l'API depuis le 14/11/2026) ; drapeau à 0 = retiré."""
    if os.environ.get("MYLEADTECH_ENABLE_LOOKUP_FAULT_CODE", "1") != "0":
        mcp.tool(
            name="lookup_fault_code",
            title="Look up a fault code",
            description="Look up a published fault code and return its meaning quoted verbatim from the OEM "
                        "manual, with citations. No generation. A missing brand returns a clarification and an "
                        "unpublished code returns empty; neither is billed. Billed: 1 unit when status is ok.",
            annotations=_read("Look up a fault code", billed=True),
        )(lookup_fault_code)


register_optional_tools()


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
