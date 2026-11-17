"""Entry point: migrate the database, then serve both apps in one process."""

import asyncio

import uvicorn

from app.config import Settings, get_settings
from app.db.migrate import run_migrations
from app.main import create_admin_app, create_public_app


async def serve(settings: Settings) -> None:
    apps = [
        (create_public_app(settings), settings.public_port),
        (create_admin_app(settings), settings.admin_port),
    ]
    servers = [
        uvicorn.Server(
            uvicorn.Config(
                app,
                host=settings.listen_host,
                port=port,
                # Request paths contain secret slugs, so no access log.
                access_log=False,
                server_header=False,
            )
        )
        for app, port in apps
    ]
    await asyncio.gather(*(server.serve() for server in servers))


def main() -> None:
    settings = get_settings()
    run_migrations(settings.database_path, settings.migrations_dir)
    asyncio.run(serve(settings))


if __name__ == "__main__":
    main()
