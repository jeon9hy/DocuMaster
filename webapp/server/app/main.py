"""로컬 백엔드 진입점. 실행: webapp/server에서 `.venv/Scripts/python -m uvicorn app.main:app --port 8000`"""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .agent_settings import AgentSettingsService
from .api import router
from .auth import AuthService
from .config import Settings, load_settings
from .db import Database
from .events import EventStore
from .files import FileStore
from .imports import import_existing_projects
from .orchestrator import create_adapter
from .projects import ProjectService
from .runs import RunManager


@dataclass
class Services:
    settings: Settings
    db: Database
    events: EventStore
    files: FileStore
    projects: ProjectService
    runs: RunManager
    auth: AuthService
    agent_settings: AgentSettingsService


def build_services(settings: Settings) -> Services:
    db = Database(settings.db_path)
    events = EventStore(db)
    files = FileStore(settings.repo_root, settings.data_dir)
    projects = ProjectService(settings, db, events, files)
    agent_settings = AgentSettingsService(db, settings.codex_home)
    runs = RunManager(settings, db, events, files, projects, create_adapter(settings), agent_settings)
    return Services(settings, db, events, files, projects, runs, AuthService(settings, db), agent_settings)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        services = build_services(settings)
        services.runs.recover_on_startup()
        import_existing_projects(services)
        app.state.services = services
        try:
            yield
        finally:
            services.runs.shutdown()
            services.db.close()

    app = FastAPI(title="DocuMaster Local Backend", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,  # 세션 쿠키(HttpOnly)를 보내야 한다 — 그래서 origin은 목록으로만 연다
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app


app = create_app()
