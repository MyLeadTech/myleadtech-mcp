# MyLeadTech MCP

HVAC MCP server — fault codes, model lookup and answers cited to the OEM manual page.

This repository holds the connection details and registry metadata for the hosted MyLeadTech MCP server (the server itself runs at the endpoint below), plus a small local stdio server (`myleadtech_mcp/`) that forwards the same tools to the MyLeadTech REST API with your key.

- **Endpoint:** `https://mcp.myleadtech.app/mcp/`
- **Transport:** Streamable HTTP
- **Auth:** API key from the [MyLeadTech dashboard](https://web.myleadtech.app), sent as `Authorization: Bearer <api_key>`. The site also lists OAuth sign-in with a MyLeadTech account for clients that support it.
- **Brands served:** the top 50 US HVAC brands — full list: [myleadtech.app/brands](https://myleadtech.app/brands)
- **Contract:** `ar-00/1` (every response carries `contract_version` and the `MLT-Contract` header). Adding a field is not a breaking change; a breaking change ships as a new contract version with 12 months notice.
- **Server card:** `https://mcp.myleadtech.app/.well-known/mcp/server-card.json` (same 7 tools as `tools/list`).
- **Plans:** Sandbox 100 free units a month; Builder 2,000 and Production 15,000 units a month per company ([pricing](https://myleadtech.app/pricing#api)). Equipment lookups, sources, pages, usage, clarifying questions and empty results don't count. A retried request with the same `operation_id` / idempotency key is never charged twice (keys kept 7 days).
- **Rate limits:** 60 searches and fault-code lookups, 30 answers per minute (per server instance). A refused call returns `rate_limited` with `retry_after_seconds` and is not charged.

## Tools

| Tool | What it does | Parameters |
| --- | --- | --- |
| `resolve_equipment` | Turns a model or nameplate reference into brand and equipment, and reports coverage. Not billed. | `reference`, `market` (default `us`), `language` (default `en-US`) |
| `search_hvac_documents` | Finds passages and citations (document, page) in manufacturer documents. 1 unit when status is `ok`. | `question`, `brand`, `model_reference`, `fault_code`, `language`, `limit` (default 5), `max_chars`, `operation_id` |
| `get_hvac_source` | Returns a cited passage with bounded context. Not billed. | `source_id` |
| `answer_hvac_question` | A written answer with page-level claims (`page_number`, `document_title`), `next_action`, a guarded one-sentence `summary` and a safety `notice`. 1 unit only when a claim rests on a source established for the equipment (see below). | `question`, `brand`, `model_reference`, `fault_code`, `language`, `limit` (default 5), `audience`, `max_chars`, `operation_id` |
| `lookup_fault_code` | The published meaning of a fault code, quoted verbatim with its page. No generation. A missing brand returns a clarification and an unpublished code returns empty; neither is billed. 1 unit when status is `ok`. | `code`, `brand`, `model_reference`, `language`, `operation_id` |
| `get_hvac_document_page` | Page or zone cited, as a PNG image. The PDF is not provided. Not billed. | `document_version_id`, `page_number`, `format` (`png` only), `region` |
| `get_usage` | Plan, monthly allowance, units used and remaining, and `window_end`. Not billed. | none |

- `operation_id` makes a retry replay the earlier result instead of charging again.
- `audience`: `technician` (default) or `homeowner`; for a homeowner, answers that touch refrigerant, electrical or gas work set `requires_qualified_technician`.
- `max_chars`: 80 to 1,200 characters per passage (default 480). Truncated passages say so (`truncated`, `truncation_reason`).
- `answer_hvac_question` billing: an `ok` answer whose claims rest only on documentation not confirmed for your unit (for example a family-level manual) is **not billed**: `usage.debited` is `false`. Read `usage.debited` and `usage.units`, not `status`, to know what was charged.
- Errors carry `request_id`, `code`, `message` and, when they apply, `param`, `doc_url` and `retry_after_seconds` (same body over REST and MCP). Codes: https://myleadtech.app/developers/docs#errors

## Install

Create an API key in the [dashboard](https://web.myleadtech.app) first.

### Claude Code

```bash
claude mcp add --transport http myleadtech https://mcp.myleadtech.app/mcp/ --header "Authorization: Bearer YOUR_API_KEY"
```

Without `--header`, Claude Code can sign you in with your MyLeadTech account instead.

### Cursor

Paste into `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "myleadtech": {
      "url": "https://mcp.myleadtech.app/mcp/",
      "headers": { "Authorization": "Bearer YOUR_API_KEY" }
    }
  }
}
```

### VS Code

Paste into `.vscode/mcp.json`:

```json
{
  "servers": {
    "myleadtech": {
      "type": "http",
      "url": "https://mcp.myleadtech.app/mcp/",
      "headers": { "Authorization": "Bearer YOUR_API_KEY" }
    }
  }
}
```

### Run it locally (stdio)

The repository also ships a local stdio server. It calls the MyLeadTech REST API with your key; no manual or index is bundled in this repository.

Tools: the same seven as the hosted server. `lookup_fault_code` is on by default since 0.4.0; set `MYLEADTECH_ENABLE_LOOKUP_FAULT_CODE=0` to leave it out.

```bash
pip install .
MYLEADTECH_API_KEY=<your key> myleadtech-mcp
```

Optional: `MYLEADTECH_API_URL` (default `https://api.myleadtech.app`). Requires Python 3.10+.

Retries: a `429 rate_limited`, `503`, `504` or network timeout is retried up to 3 times, always with the same idempotency key, so the request is charged once. `quota_exceeded`, `not_entitled`, `conflict` and other 4xx are never retried. Errors read `<code>: <message> (request_id=...)`; quote the `request_id` to support.

### Other clients

Any MCP client that supports remote Streamable HTTP servers: endpoint `https://mcp.myleadtech.app/mcp/`, header `Authorization: Bearer <api_key>`.

## Example

Call `answer_hvac_question` with:

```json
{ "question": "What refrigerant does the EXA-36 use?", "brand": "example_air", "model_reference": "EXA-36-B2" }
```

Response shape (**illustrative**, `ar-00/1`: invented ids and text, not a live call and not manufacturer content):

```json
{
  "request_id": "00000000-0000-4000-8000-0000000000a1",
  "contract_version": "ar-00/1",
  "status": "ok",
  "partial": false,
  "missing": [],
  "degraded": [],
  "usage": {
    "operation": "answer",
    "debited": true,
    "units": 1,
    "remaining": 98
  },
  "next_action": "answer",
  "summary": "Illustrative summary: this example unit uses refrigerant R-000.",
  "summary_source_ids": ["chunk:00000000-0000-4000-8000-000000000001"],
  "answer": "Illustrative answer: this example unit uses refrigerant R-000.",
  "claims": [
    {
      "text": "Illustrative claim: the unit uses refrigerant R-000.",
      "source_id": "chunk:00000000-0000-4000-8000-000000000001",
      "page_number": 1,
      "document_title": "Illustrative product data"
    }
  ],
  "requires_qualified_technician": false,
  "notice": "Manufacturer documentation, not verified by MyLeadTech for your installation. Work on refrigerant, electrical or gas systems requires a qualified technician.",
  "limits": [],
  "passages": [
    {
      "source_id": "chunk:00000000-0000-4000-8000-000000000001",
      "document_version_id": "00000000-0000-4000-8000-000000000002",
      "document_type": "product_data",
      "text": "Illustrative passage text, invented for this README.",
      "pages": [1],
      "applicability": "established",
      "rank": 1,
      "citations": []
    }
  ]
}
```

Here `debited` is `true` because the claim rests on a passage whose `applicability` is `established`. With documentation not confirmed for the unit, the same `ok` answer comes back with `debited: false` and no unit charged. The cited page is available as a PNG image through `get_hvac_document_page`.

## Links

- Developer docs: https://myleadtech.app/developers/docs
- MCP guide: https://myleadtech.app/developers/mcp
- REST OpenAPI spec: https://api.myleadtech.app/v1/openapi.json
- Site: https://myleadtech.app
- Get an API key: https://web.myleadtech.app

## Listings

[![M8ven Score](https://m8ven.ai/badge/mcp/myleadtech-myleadtech-mcp-80gruo?v=7788eff4930294da1b7424d406e89d3f)](https://m8ven.ai/mcp/myleadtech-myleadtech-mcp-80gruo?s=readme)

## License

MIT, for the files in this repository only (README and configuration). The MyLeadTech service and the manufacturer documents it cites are not covered.
