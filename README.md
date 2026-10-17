# MyLeadTech MCP

HVAC MCP server — fault codes, model lookup and answers cited to the OEM manual page.

This repository holds the connection details and registry metadata for the hosted MyLeadTech MCP server. There is no server code here: the server runs at the endpoint below.

- **Endpoint:** `https://mcp.myleadtech.app/mcp/`
- **Transport:** Streamable HTTP
- **Auth:** API key from the [MyLeadTech dashboard](https://web.myleadtech.app), sent as `Authorization: Bearer <api_key>`. The site also lists OAuth sign-in with a MyLeadTech account for clients that support it.
- **Brands served:** Carrier, Trane, Lennox
- **Sandbox:** 100 free units a month. Equipment lookups and clarifying questions don't count. A retried request with the same idempotency key is never charged twice.

## Tools

| Tool | What it does | Parameters |
| --- | --- | --- |
| `resolve_equipment` | Turns a model or nameplate reference into brand and equipment, and reports coverage. Not charged. | `reference`, `market` (default `us`), `language` (default `en-US`) |
| `search_hvac_documents` | Finds passages and citations in manufacturer documents. | `question`, `brand`, `model_reference`, `fault_code`, `language`, `limit` (default 5), `operation_id` |
| `get_hvac_source` | Returns a cited passage with bounded context. | `source_id` |
| `answer_hvac_question` | A written answer with numbered, page-level sources. | `question`, `brand`, `model_reference`, `fault_code`, `language`, `limit` (default 5), `operation_id` |
| `get_hvac_document_page` | A source page as PNG, or a signed single-page PDF link when `format` is `pdf`. | `document_version_id`, `page_number`, `format` (default `png`), `region` |

`operation_id` makes a retry replay the earlier result instead of charging again.

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

### Other clients

Any MCP client that supports remote Streamable HTTP servers: endpoint `https://mcp.myleadtech.app/mcp/`, header `Authorization: Bearer <api_key>`.

## Example

Call `answer_hvac_question` with:

```json
{ "question": "What refrigerant does the 27TPA8 use?", "brand": "carrier", "model_reference": "27TPA8" }
```

Response shape (**contract example** `ar-00/1`, `answer/ok.json`, copied unchanged; not a live call):

```json
{
  "request_id": "55555555-5555-4555-8555-555555555501",
  "contract_version": "ar-00/1",
  "service_revision": "2026.10.06-doc",
  "publication": {
    "branch": "main",
    "snapshot_ref": "main-20261006-5ed-carrier-263ch"
  },
  "status": "ok",
  "partial": false,
  "missing": [],
  "degraded": [],
  "usage": {
    "operation": "answer",
    "debited": true,
    "units": null
  },
  "answer": "The 27TPA8 is a Performance Series 2-stage heat pump for R-454B indoor units only.",
  "claims": [
    {
      "text": "Uses Puron Advance (R-454B) refrigerant.",
      "source_id": "chunk:1a9595df-e0cb-4dfe-83d8-504e1da1757a"
    }
  ],
  "limits": [],
  "passages": [
    {
      "source_id": "chunk:1a9595df-e0cb-4dfe-83d8-504e1da1757a",
      "document_version_id": "65a562f3-1c45-4071-be67-30b35eac7393",
      "document_type": "product_data",
      "text": "27TPA8 Performance Series 2-Stage Heat Pump with Puron Advance™ (R-454B) Refrigerant …",
      "pages": [
        1
      ],
      "printed_label": null,
      "applicability": "established",
      "rank": 1,
      "citations": []
    }
  ]
}
```

## Links

- Developer docs: https://myleadtech.app/developers/docs
- MCP guide: https://myleadtech.app/developers/mcp
- REST OpenAPI spec: https://api.myleadtech.app/v1/openapi.json
- Site: https://myleadtech.app
- Get an API key: https://web.myleadtech.app

## License

MIT, for the files in this repository only (README and configuration). The MyLeadTech service and the manufacturer documents it cites are not covered.
