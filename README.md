# MyLeadTech MCP

HVAC MCP server — model lookup and answers cited to the OEM manual page.

This repository holds the connection details and registry metadata for the hosted MyLeadTech MCP server (the server itself runs at the endpoint below), plus a small local stdio server (`myleadtech_mcp/`) that forwards the same tools to the MyLeadTech REST API with your key.

- **Endpoint:** `https://mcp.myleadtech.app/mcp/`
- **Transport:** Streamable HTTP
- **Auth:** API key from the [MyLeadTech dashboard](https://web.myleadtech.app), sent as `Authorization: Bearer <api_key>`. The site also lists OAuth sign-in with a MyLeadTech account for clients that support it.
- **Brands served:** the top 50 US HVAC brands — full list: [myleadtech.app/brands](https://myleadtech.app/brands)
- **Fault codes:** a browsable public example is the [Carrier fault code index](https://myleadtech.app/brands/carrier/codes). A dedicated `lookup_fault_code` tool is planned and is listed here only once it is live on the hosted server.
- **Sandbox:** 100 free units a month. Equipment lookups and clarifying questions don't count. A retried request with the same idempotency key is never charged twice.

## Tools

| Tool | What it does | Parameters |
| --- | --- | --- |
| `resolve_equipment` | Turns a model or nameplate reference into brand and equipment, and reports coverage. Not charged. | `reference`, `market` (default `us`), `language` (default `en-US`) |
| `search_hvac_documents` | Finds passages and citations in manufacturer documents. | `question`, `brand`, `model_reference`, `fault_code`, `language`, `limit` (default 5), `operation_id` |
| `get_hvac_source` | Returns a cited passage with bounded context. | `source_id` |
| `answer_hvac_question` | A written answer with numbered, page-level sources. | `question`, `brand`, `model_reference`, `fault_code`, `language`, `limit` (default 5), `operation_id` |
| `get_hvac_document_page` | Page or zone cited, as a PNG image. The PDF is not provided. | `document_version_id`, `page_number`, `format` (`png` only), `region` |

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

### Run it locally (stdio)

The repository also ships a local stdio server with the same tools as the hosted server (current set listed in `myleadtech_mcp/server.py`). It calls the MyLeadTech REST API with your key; no manual or index is bundled in this repository.

```bash
pip install .
MYLEADTECH_API_KEY=<your key> myleadtech-mcp
```

Optional: `MYLEADTECH_API_URL` (default `https://api.myleadtech.app`). Requires Python 3.10+.

### Other clients

Any MCP client that supports remote Streamable HTTP servers: endpoint `https://mcp.myleadtech.app/mcp/`, header `Authorization: Bearer <api_key>`.

## Example

Call `answer_hvac_question` with:

```json
{ "question": "What refrigerant does the 27TPA8 use?", "brand": "carrier", "model_reference": "27TPA8" }
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
    "units": 1
  },
  "answer": "Illustrative answer: this example unit uses refrigerant R-000.",
  "claims": [
    {
      "text": "Illustrative claim: the unit uses refrigerant R-000.",
      "source_id": "chunk:00000000-0000-4000-8000-000000000001"
    }
  ],
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

When `debited` is `true`, `usage.units` carries the units charged (`1` for a successful answer). The cited page is available as a PNG image through `get_hvac_document_page`.

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
