# Deployment

Target: a shared `linux/arm64` server that also hosts unrelated sites and
exposes no inbound web ports. Compose files and scripts arrive in Phase 1;
this document fixes the shape.

## Compose project

Lives in its own directory with its own Compose project name, so deploys and
clean-ups of other stacks on the host cannot touch it.

| Service | Purpose |
| --- | --- |
| `app` | The site: public app on container port 8000, admin app on 8001 |
| `cloudflared` | This project's own Cloudflare Tunnel; reaches `app` over the project network |

- No host ports are published on the server.
- `app` gets a small memory limit (about 256 MB).
- The image is built on the server itself, which avoids cross-building for
  arm64: `git pull && docker compose up -d --build`.

## Hostnames

Configured on the tunnel (hostnames are chosen later):

| Hostname | Target |
| --- | --- |
| `<domain>` | `http://app:8000` |
| `admin.<domain>` | `http://app:8001` |

- Stable hostnames that outlive the printed QR codes. Never generate QR codes
  for a temporary URL.
- Do not cache HTML or API responses at the edge; pass the app's cache headers
  through.
- Keep `cloudflared` at its default log level; debug logging records request
  paths, which contain the secret slug. Edge-side logs are outside the app's
  control.
- Optional: an access policy in front of `admin.<domain>` as a second layer.

Set `PUBLIC_BASE_URL` to the final HTTPS origin, `APP_ENV=production` and
`TUNNEL_TOKEN` in `.env`.

## Admin login

One password, set as `ADMIN_PASSWORD` in `.env`; sessions are signed with
`SESSION_SECRET`. Use long random values for both.

## Data

- The SQLite file lives in `./data` on the host, bind-mounted to `/data`. It
  is outside the image, so building and deploying a new image keeps all saved
  responses, acknowledgements and opens.
- Data is lost only if `./data` is deleted or the disk fails. Links keep
  working either way, because they are defined in the page configs.
- Migrations run on start and never drop data.

### Export

There is no automated backup. `scripts/export-db` writes a consistent
snapshot to `./data/exports/letterbox-<timestamp>.db`, which can be copied
off the server:

```bash
./scripts/export-db
scp <server>:<project-dir>/data/exports/letterbox-<timestamp>.db .
```

## Releasing a new page

1. Add the page directory and deploy.
2. Open the real link on a phone and exercise it.
3. Check the result in the admin dashboard, then reset the page.
4. Download the QR code from the dashboard.

## Disabling a link

Immediately: block the path with an edge rule. Permanently: set
`"enabled": false` in the page's `page.json` and deploy.

## Local development

Windows 11 + WSL2 Ubuntu + Docker Desktop, or any Linux Docker host. Runs the
`app` service only, with both ports published on `127.0.0.1`
(`PUBLIC_PORT`, `ADMIN_PORT`): pages at `http://localhost:8610`, admin at
`http://localhost:8611`.
