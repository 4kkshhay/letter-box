"""Entry point: migrate the database, then serve both apps in one process."""

import asyncio

import uvicorn

from app.config import Settings, get_settings
from app.db.migrate import run_migrations
from app.main import create_admin_app, create_public_app
from app.services.pages import PageRegistry, load_pages


async def serve(settings: Settings, pages: PageRegistry) -> None:
    apps = [
        (create_public_app(settings, pages), settings.public_port),
        (create_admin_app(settings, pages), settings.admin_port),
    ]
    servers = [
        uvicorn.Server(
            uvicorn.Config(
                app,
                host=settings.listen_host,
                port=port,
                # Request paths contain secret slugs, so no access log.
                access_log=False,
                proxy_headers=False,
                server_header=False,
            )
        )
        for app, port in apps
    ]
    await asyncio.gather(*(server.serve() for server in servers))


def main() -> None:
    settings = get_settings()
    # Invalid page configs abort the start before anything is served.
    pages = load_pages(settings.static_dir)
    print(f"Loaded {len(pages.pages)} page(s)", flush=True)
    gate = settings.page_password_hashes
    print(f"Page gate: {f'on ({len(gate)} password(s))' if gate else 'off'}", flush=True)
    run_migrations(settings.database_path, settings.migrations_dir)
    asyncio.run(serve(settings, pages))


if __name__ == "__main__":
    main()
