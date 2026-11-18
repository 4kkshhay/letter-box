# Deployment

Target: a shared `linux/arm64` server that also hosts unrelated sites and
exposes no inbound web ports. Compose files and scripts arrive in Phase 1;
this document fixes the shape.

## Release and deploy pipeline

`.github/workflows/release-deploy.yml` has two independently triggered jobs:

1. **Build and release image** — runs after a merge reaches `main`, builds
   `linux/arm64`, and pushes private `latest` and full commit-SHA tags to GHCR.
2. **Deploy to server** — runs only when manually dispatched from `main`. It
   deploys the current `main` release by default, or an entered full commit SHA
   for rollback. It copies the runtime files over SSH, pulls that SHA-tagged
   image, resolves it to its immutable digest, starts the project and checks
   readiness on both internal ports. After success, it keeps the seven newest
   GHCR image versions and deletes older versions.

The GHCR package must remain private because the image contains page configs
and their link slugs. During the pull, the short-lived GitHub token is held in
a run-specific Docker config under memory-backed `/dev/shm`, never in
`letterbox`'s home directory. The deploy job logs out and deletes that config
on both success and failure. After readiness passes, it records the deployed
digest in `.release.env` for manual Compose/export commands.

Image cleanup uses the same automatic `GITHUB_TOKEN`; it needs no additional
secret. Images are built without provenance or SBOM attestations, so each
release is a single GHCR version and keeping seven versions leaves the current
release and six rollback candidates. A failed deployment does not prune the
registry.

After a successful deployment the server removes this project's older app
images (only images from this project's GHCR repository; the running one is
kept). Rollback pulls the selected release from GHCR again. Other projects'
images are never touched.

## Compose project

Lives in its own directory with its own Compose project name, so deploys and
clean-ups of other stacks on the host cannot touch it.

| Service | Purpose |
| --- | --- |
| `app` | The site: public app on container port 8000, admin app on 8001 |
| `cloudflared` | This project's own Cloudflare Tunnel; reaches `app` over the project network |

- No host ports are published on the server.
- `app` gets a small memory limit (about 256 MB).
- The server pulls the arm64 image by digest; source and build tooling are not
  copied there.
- `docker-compose.production.yml` adds a pinned `cloudflared` container. The
  app and tunnel have read-only root filesystems, no Linux capabilities and
  `no-new-privileges`.

### One-time server setup

The production SSH deployment user is `letterbox`. Create `/srv/letter-box`,
owned by that user, with a private `.env` and writable `data/` directory.
Docker Compose v2 must be available to `letterbox`. The deploy workflow creates
the remaining directories and copies runtime files on its first run.

The bootstrap script creates the account, installs the deployment public key,
adds the account to the Docker group, creates the directories and securely
writes `.env`. Generate the admin hash locally first, then copy and run the
script from an existing SSH administrator account:

```bash
./scripts/hash-admin-password.sh
scp scripts/setup-production-server <admin-user>@<server>:/tmp/
ssh -t <admin-user>@<server> 'sudo bash /tmp/setup-production-server'
```

It prompts for the `letterbox_deploy.pub` line, Cloudflare tunnel token and the
complete output from the hash command. It generates `SESSION_SECRET` itself and
never prints the secret values. Re-running it is safe: the key is not duplicated
and a non-empty `.env` is preserved.

Configure these GitHub repository or `production` environment secrets:

| Secret | Value |
| --- | --- |
| `DEPLOY_HOST` | Server hostname or IP |
| `DEPLOY_USER` | `letterbox` |
| `DEPLOY_SSH_KEY` | Private deployment key |
| `DEPLOY_KNOWN_HOSTS` | Verified OpenSSH known-hosts line for the server |

The public key belongs in that user's `authorized_keys`. Verify the server host
fingerprint out of band before storing `DEPLOY_KNOWN_HOSTS`; the workflow never
accepts a host key automatically.

## Hostnames

The site uses the domain `letterbox.ink`, registered with Cloudflare and
already on Cloudflare nameservers. Use it for all deployment, tunnel and QR
configuration. Hostnames configured on the tunnel:

| Hostname | Target |
| --- | --- |
| `letterbox.ink` | `http://app:8000` |
| `admin.letterbox.ink` | `http://app:8001` |

- Stable hostnames that outlive the printed QR codes. Never generate QR codes
  for a temporary URL.
- Do not cache HTML or API responses at the edge; pass the app's cache headers
  through.
- Keep `cloudflared` at its default log level; debug logging records request
  paths, which contain the secret slug. Edge-side logs are outside the app's
  control.
- Optional: an access policy in front of `admin.letterbox.ink` as a second layer.
- Recommended: an edge rate limit on `/l/*` and `/api/v1/pages/*` to slow link
  guessing (F-009).

Create one remotely managed tunnel in Cloudflare, put its token in the server
`.env`, and add both public hostnames with the targets above. The pinned
`cloudflared` container reads the token and makes outbound-only connections.

Production `.env` on the server:

```dotenv
COMPOSE_FILE=docker-compose.yml:docker-compose.production.yml
APP_ENV=production
PUBLIC_BASE_URL=https://letterbox.ink
DATA_DIR=./data
APP_UID=<output of id -u letterbox>
APP_GID=<output of id -g letterbox>
ADMIN_PASSWORD_HASH='<generated scrypt hash>'
SESSION_SECRET=<long random value, at least 32 characters>
TUNNEL_TOKEN=<from the Cloudflare dashboard>
```

The domain must stay registered (renewal due each November) for as long as
printed QR codes should work.

## Admin login

One password, stored only as a scrypt hash in `ADMIN_PASSWORD_HASH`; generate
the assignment with `scripts/hash-admin-password.sh`. Sessions are signed with
`SESSION_SECRET`, which must be at least 32 characters in production. Keep both
values in `.env` only. Production cookies are always marked `Secure` from
`APP_ENV`, without trusting forwarded scheme headers.

## Data

- The SQLite file lives in `./data` on the host, bind-mounted to `/data`. It
  is outside the image, so building and deploying a new image keeps all saved
  responses and opens.
- Data is lost only if `./data` is deleted or the disk fails. Links keep
  working either way, because they are defined in the page configs.
- Migrations run on start and never drop data.

### Export

There is no automated backup. `scripts/export-db` uses SQLite's online backup
API, checks the snapshot integrity, and writes it atomically to
`./data/exports/letterbox-<timestamp>.db`, which can be copied off the server:

```bash
./scripts/export-db
scp <server>:<project-dir>/data/exports/letterbox-<timestamp>.db .
```

## Releasing a new page

1. Add and verify the page as described in [adding a page](adding-a-page.md).
2. Merge it to `main`; the release job builds and publishes the image.
3. After the release job passes, manually run **Release and deploy** on `main`
   from the Actions tab. Leave `release_sha` blank to deploy the current commit.
4. Open the real link on a phone and exercise it.
5. Check the result in the admin dashboard, then reset the page. This is
   required: the first open counts as "received", so a test open left in
   place would show the page as received before it is sent.
6. Download the QR code from the dashboard.

## Disabling a link

Immediately: block both `/l/<slug>` and `/api/v1/pages/<slug>` with an edge
rule. Permanently: set `"enabled": false` in the page's `page.json` and
deploy.

## Local development

Windows 11 + WSL2 Ubuntu + Docker Desktop, or any Linux Docker host. Runs the
`app` service only, with both ports published on `127.0.0.1`
(`PUBLIC_PORT`, `ADMIN_PORT`): pages at `http://localhost:8610`, admin at
`http://localhost:8611`.
