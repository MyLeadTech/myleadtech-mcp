# Registry submissions

Researched 2026-10-18 from each registry's own docs and forms. Nothing here has been submitted. Re-check each form before sending; several of these change often.

Common values:

| Field | Value |
| --- | --- |
| One-line description | `HVAC MCP server — fault codes, model lookup and answers cited to the OEM manual page.` |
| Name | MyLeadTech HVAC |
| Registry name | `app.myleadtech/mcp` |
| Endpoint | `https://mcp.myleadtech.app/mcp/` (Streamable HTTP) |
| Repo | `https://github.com/MyLeadTech/myleadtech-mcp` |
| Website / docs | `https://myleadtech.app/developers/mcp` |
| Auth | Bearer API key from `https://web.myleadtech.app` |
| Category (where asked) | Developer tools / Reference & documentation (pick the closest) |

Order: publish the GitHub repo first (every registry below reads it), then the official registry, then the rest. PulseMCP picks up the official registry on its own.

## 1. Official MCP registry (`mcp-publisher`)

- **Method:** CLI, `mcp-publisher publish` with `server.json` (schema `2025-12-11`). Remote-only entries need no package on npm/PyPI.
- **Account:** none to create. Authenticate with `mcp-publisher login`. The name `app.myleadtech/mcp` is a reverse-DNS name, so it needs **domain authentication for `myleadtech.app`** (DNS TXT or HTTP file). GitHub login only grants `io.github.*` names.
- **Required fields:** `name`, `description`, `version`, plus `remotes[]` with `type: streamable-http` and `url`. The remote must be publicly reachable (a 401 without a key is fine).
- **Namespace verification (manager does this once):**
  1. Install: `brew install mcp-publisher`.
  2. Make a key (macOS needs OpenSSL 3: `brew install openssl@3`, use `/opt/homebrew/opt/openssl@3/bin/openssl`):
     ```bash
     openssl genpkey -algorithm Ed25519 -out key.pem
     PUBLIC_KEY="$(openssl pkey -in key.pem -pubout -outform DER | tail -c 32 | base64)"
     echo "v=MCPv1; k=ed25519; p=${PUBLIC_KEY}"
     ```
  3. Pick one:
     - **DNS:** add a TXT record on the **apex** `myleadtech.app` (not a subdomain or selector) with the value printed above. Remove stale TXT records from earlier attempts.
     - **HTTP:** serve that same line as a file at `https://myleadtech.app/.well-known/mcp-registry-auth`.
  4. Log in:
     ```bash
     PRIVATE_KEY="$(openssl pkey -in key.pem -noout -text | grep -A3 "priv:" | tail -n +2 | tr -d ' :\n')"
     mcp-publisher login dns --domain myleadtech.app --private-key "$PRIVATE_KEY"
     # HTTP variant: mcp-publisher login http --domain myleadtech.app --private-key "$PRIVATE_KEY"
     ```
  5. Keep `key.pem` out of git (it is in `.gitignore`).
- **Publish:**
  ```bash
  cd myleadtech-mcp
  mcp-publisher validate
  mcp-publisher publish
  curl "https://registry.modelcontextprotocol.io/v0.1/servers?search=app.myleadtech/mcp"
  ```
- **Text to paste:** none; it is read from `server.json`.
- **Delay:** immediate, no manual review. The registry is labeled preview, so data resets are possible. A new release needs a higher `version` in `server.json`.

## 2. Smithery

- **Method:** web flow at `https://smithery.ai/new` (enter the public HTTPS URL), or CLI: `smithery mcp publish "https://mcp.myleadtech.app/mcp/" -n @myleadtech/hvac`. No `smithery.yaml` is needed for a URL-based server, so none is in this repo.
- **Account:** Smithery account (GitHub sign-in). The `@myleadtech` namespace is created at first publish; confirm it is free.
- **Required:** public HTTPS URL, Streamable HTTP, and OAuth support if the server needs auth. Smithery scans the server for its tool list.
- **Risk:** our endpoint answers 401 without a key. Smithery says auth-required servers prompt for authentication to finish the scan. If the scan can't complete, Smithery accepts a static card at `/.well-known/mcp/server-card.json` on the MCP host. Minimal card (tool schemas can be copied from the `tools/list` response):
  ```json
  { "serverInfo": { "name": "MyLeadTech HVAC", "version": "0.1.0" },
    "authentication": { "required": true, "schemes": ["bearer"] },
    "tools": [] }
  ```
  The `schemes` value is unverified: the docs only show `oauth2`. Smithery's CLI also takes `--config-schema` to collect the API key; for example `'{"type":"object","properties":{"apiKey":{"type":"string"}}}'`.
- **Paste:** display name `MyLeadTech HVAC`, description `HVAC MCP server — fault codes, model lookup and answers cited to the OEM manual page.`, homepage `https://myleadtech.app/developers/mcp`.
- **Delay:** no stated review; listing appears after the scan.

## 3. Glama

- **Method:** form on `https://glama.ai/mcp/servers` via the **Add Server** button. Glama also auto-indexes public GitHub repos that look like MCP servers.
- **Account:** Glama account (sign-in, robot check).
- **Fields:** repository URL (required, `https://github.com/MyLeadTech/myleadtech-mcp`) and name (optional).
- **Caveat:** Glama's directory is built around servers whose code it can run from a repo (Dockerfile in its admin). This repo has no code, so it may be indexed with limited details or sit as a listing without a build. Glama also has a separate **connectors** directory for servers hosted at a URL; look for its add flow after signing in. I could not confirm that flow without an account.
- **Claim ownership:** add `glama.json` at the repo root once the listing exists:
  ```json
  { "$schema": "https://glama.ai/mcp/schemas/server.json", "maintainers": ["GITHUB_USERNAME_OF_ORG_OWNER"] }
  ```
  Replace the placeholder with the maintainer's GitHub username. Check the schema URL in Glama's docs before committing.
- **Paste:** name `MyLeadTech HVAC`, description `HVAC MCP server — fault codes, model lookup and answers cited to the OEM manual page.`.
- **Delay:** not stated. Treat as days.

## 4. mcp.so

- **Method:** web form at `https://mcp.so/submit?type=server` (its FAQ says GitHub-issue submission, which the form replaces).
- **Account:** sign-in required before submitting.
- **Fields seen:** Repository URL (required, `https://github.com/owner/repository` format) and Name. The page also pushes a paid "premium" tier (dofollow link, faster review); the free tier is enough.
- **Paste:** repo `https://github.com/MyLeadTech/myleadtech-mcp`, name `MyLeadTech HVAC`. The description is taken from the repo README, so keep the first line of `README.md` identical to the one-liner.
- **Delay:** not stated for the free tier.

## 5. PulseMCP

- **Method:** **submissions are paused** (page last updated 2026-09-03: no new servers, no listing changes). PulseMCP tells authors to publish to the official registry and says it will pick it up automatically.
- **Account:** none.
- **Action:** do nothing now. After step 1, check `https://www.pulsemcp.com/servers?q=myleadtech` in a week or two. Re-check `https://www.pulsemcp.com/submit` for a reopened form.
- **Delay:** unknown until submissions reopen.

## 6. mcpservers.org

- **Method:** web form at `https://mcpservers.org/submit`.
- **Account:** none; contact email only.
- **Fields:**

  | Field | Paste |
  | --- | --- |
  | Server Name | `MyLeadTech HVAC` |
  | Category | closest to developer tools / reference (pick from the dropdown) |
  | Short Description | `HVAC MCP server — fault codes, model lookup and answers cited to the OEM manual page.` |
  | Repository, Website or Documentation | `https://github.com/MyLeadTech/myleadtech-mcp` |
  | Official MCP Registry Name (optional) | `app.myleadtech/mcp` (only after step 1 succeeds) |
  | This server supports remote connections | checked |
  | Contact Email | the team address the manager chooses |
  | Submission plan | Free |
- **Delay:** free plan, review within 2 weeks. Premium ($39) promises 24 hours; not needed.
