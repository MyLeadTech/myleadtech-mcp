# Installing the MyLeadTech HVAC MCP server (for AI agents)

This is a **remote** MCP server. There is nothing to clone, build or run locally.

- Endpoint: `https://mcp.myleadtech.app/mcp/`
- Transport: Streamable HTTP
- Auth: `Authorization: Bearer <MYLEADTECH_API_KEY>`

## Steps

1. Ask the user for their MyLeadTech API key. If they have none, tell them to create one at https://web.myleadtech.app (a free sandbox of 100 units a month is included). Never invent a key.
2. Add the server to the client's MCP settings. For Cline (`cline_mcp_settings.json`):

   ```json
   {
     "mcpServers": {
       "myleadtech": {
         "type": "streamableHttp",
         "url": "https://mcp.myleadtech.app/mcp/",
         "headers": { "Authorization": "Bearer MYLEADTECH_API_KEY" },
         "disabled": false
       }
     }
   }
   ```

   Replace `MYLEADTECH_API_KEY` with the user's key.
3. Check the connection by calling `resolve_equipment` with `{"reference": "27TPA836A0030"}`. It is not billed. A `401` means the key is missing or wrong.

## Tools

`resolve_equipment`, `search_hvac_documents`, `get_hvac_source`, `answer_hvac_question`, `get_hvac_document_page`. All are read-only. Details and examples: https://myleadtech.app/developers/mcp
