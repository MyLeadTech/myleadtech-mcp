"""MyLeadTech HVAC MCP server (stdio).

Local MCP server: it runs on your machine and exposes five read-only tools.
Each tool calls the MyLeadTech REST API (https://api.myleadtech.app/v1) with your
API key. The manuals and the index stay on the MyLeadTech side: nothing is
bundled here, and the key decides what you can read and how many units you use.

Environment:
  MYLEADTECH_API_KEY   required, key from https://web.myleadtech.app
  MYLEADTECH_API_URL   optional, defaults to https://api.myleadtech.app
"""

from __future__ import annotations

import base64
import os
import uuid
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP, Image
from mcp.types import ToolAnnotations

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
    return {"Authorization": f"Bearer {key}", "User-Agent": "myleadtech-mcp/0.2.0"}


def _call(method: str, path: str, *, json: dict | None = None, params: dict | None = None,
          idempotency: str | None = None) -> httpx.Response:
    headers = _headers()
    if idempotency:
        headers["Idempotency-Key"] = idempotency
    with httpx.Client(base_url=API_URL, timeout=TIMEOUT) as client:
        response = client.request(method, path, json=json, params=params, headers=headers)
    return response


def _json(response: httpx.Response) -> dict[str, Any]:
    try:
        body = response.json()
    except ValueError:
        body = {"detail": response.text[:500]}
    if response.status_code >= 400:
        raise RuntimeError(f"MyLeadTech API {response.status_code}: {body}")
    return body


def _query(question: str, brand, model_reference, fault_code, language, limit) -> dict[str, Any]:
    body: dict[str, Any] = {"question": question, "language": language, "limit": limit}
    for name, value in (("brand", brand), ("model_reference", model_reference), ("fault_code", fault_code)):
        if value:
            body[name] = value
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
    description="Search OEM HVAC manuals by question, brand, model reference or fault code. Returns bounded passages with citations (document, page).",
    annotations=_read("Search HVAC documents", billed=True),
)
def search_hvac_documents(question: str, brand: str | None = None, model_reference: str | None = None,
                          fault_code: str | None = None, language: str = "en-US", limit: int = 5,
                          operation_id: str | None = None) -> dict[str, Any]:
    return _json(_call("POST", "/v1/search",
                       json=_query(question, brand, model_reference, fault_code, language, limit),
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
    description="Answer an HVAC service question with citations to the OEM manual page it came from. Returns empty rather than guessing when no source supports an answer.",
    annotations=_read("Answer HVAC question", billed=True),
)
def answer_hvac_question(question: str, brand: str | None = None, model_reference: str | None = None,
                         fault_code: str | None = None, language: str = "en-US", limit: int = 5,
                         operation_id: str | None = None) -> dict[str, Any]:
    return _json(_call("POST", "/v1/answers",
                       json=_query(question, brand, model_reference, fault_code, language, limit),
                       idempotency=operation_id or str(uuid.uuid4())))


@mcp.tool(
    name="get_hvac_document_page",
    title="Get manual page",
    description="Return a source manual page as a PNG image (format png only; PDF output is disabled).",
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


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
