"""REST + SSE 라우트(지침서 §12). 로직은 서비스에 두고 여기서는 입출력만 바꾼다."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

from .agent_settings import UnsupportedConfigError
from .auth import AVATAR_MAX_BYTES, SESSION_COOKIE, SESSION_DAYS, AuthError
from .files import UnsafePathError, UploadTooLargeError
from .projects import InvalidRequestError, NotFoundError
from .runs import ConflictError
from .usage import usage_report

router = APIRouter(prefix="/api")

SSE_KEEPALIVE_SECONDS = 15


class NewProject(BaseModel):
    name: str
    mode: str = "auto"


class NewMessage(BaseModel):
    text: str


class InputResponse(BaseModel):
    answer: str


class AgentConfig(BaseModel):
    provider: str
    modelId: str
    reasoningLevel: str | None = None


class LoginBody(BaseModel):
    pin: str


class PinChange(BaseModel):
    currentPin: str
    newPin: str


def _services(request: Request):
    return request.app.state.services


def require_owner(request: Request) -> None:
    """바꾸는 요청은 모두 Owner만. 화면의 버튼을 잠그는 것과 별개로 여기서 막는다.

    다른 로컬 페이지가 쿠키를 싣고 보내는 요청(CSRF)을 막으려고 Origin도 허용 목록과 맞춰 본다.
    """
    services = _services(request)
    origin = request.headers.get("origin")
    if origin and origin not in services.settings.cors_origins:
        raise _error(403, "forbidden_origin", "허용되지 않은 출처의 요청입니다.")
    if not services.auth.is_owner(request.cookies.get(SESSION_COOKIE)):
        raise _error(401, "auth_required", "로그인한 Owner만 할 수 있는 작업입니다. 로그인 후 다시 시도하세요.")


OWNER = [Depends(require_owner)]


def _error(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message})


def _guard(action):
    """서비스 예외 → HTTP 오류. 사용자에게 '알 수 없는 오류'만 보여 주지 않도록 코드와 문장을 함께 준다."""
    try:
        return action()
    except NotFoundError as error:
        raise _error(404, "not_found", str(error)) from error
    except ConflictError as error:
        raise _error(409, "conflict", str(error)) from error
    except UploadTooLargeError as error:
        raise _error(413, "file_upload_error", "파일이 너무 큽니다(최대 200MB).") from error
    except UnsafePathError as error:
        raise _error(400, "unsafe_path", "허용되지 않은 경로입니다.") from error
    except InvalidRequestError as error:
        raise _error(400, "invalid_request", str(error)) from error


# --- 시스템 ---------------------------------------------------------------------


@router.get("/system/health")
def health(request: Request):
    """LLM을 부르지 않는다 — 도구가 PATH에 있는지만 본다."""
    return {"ok": True, **_services(request).runs.status()}


# --- 프로젝트 --------------------------------------------------------------------


@router.get("/projects")
def list_projects(request: Request):
    return _services(request).projects.list()


@router.post("/projects", status_code=201, dependencies=OWNER)
def create_project(body: NewProject, request: Request):
    return _guard(lambda: _services(request).projects.create(body.name, body.mode))


@router.delete("/projects/{project_id}", status_code=204, dependencies=OWNER)
def delete_project(project_id: str, request: Request):
    """목록에서만 지운다(작업/·최종/ 파일은 그대로). 실행 중이면 먼저 멈춰야 한다."""
    services = _services(request)
    if services.runs.active_run(project_id):
        raise _error(409, "conflict", "실행 중인 프로젝트는 삭제할 수 없습니다. 먼저 중지하세요.")
    _guard(lambda: services.projects.delete(project_id))


@router.get("/projects/{project_id}/workspace")
def get_workspace(project_id: str, request: Request):
    return _guard(lambda: _services(request).projects.snapshot(project_id))


# --- 실행 ------------------------------------------------------------------------


@router.post("/projects/{project_id}/runs", status_code=202, dependencies=OWNER)
def start_run(project_id: str, request: Request):
    return {"runId": _guard(lambda: _services(request).runs.start(project_id))}


@router.post("/projects/{project_id}/runs/{run_id}/stop", status_code=202, dependencies=OWNER)
def stop_run(project_id: str, run_id: str, request: Request):
    """run_id가 'current'이면 이 프로젝트의 진행 중 실행을 멈춘다."""
    services = _services(request)
    active = services.runs.active_run(project_id)
    if active and run_id not in ("current", active["id"]):
        raise _error(409, "conflict", "이미 끝난 실행입니다.")
    _guard(lambda: services.runs.request_stop(project_id))
    return {"ok": True}


@router.post("/projects/{project_id}/inputs/{prompt_id}/response", status_code=202, dependencies=OWNER)
def respond(project_id: str, prompt_id: str, body: InputResponse, request: Request):
    _guard(lambda: _services(request).runs.respond(project_id, prompt_id, body.answer))
    return {"ok": True}


@router.post("/projects/{project_id}/messages", status_code=201, dependencies=OWNER)
def send_message(project_id: str, body: NewMessage, request: Request):
    _guard(lambda: _services(request).projects.add_message(project_id, body.text))
    return {"ok": True}


@router.get("/projects/{project_id}/events")
async def stream_events(
    project_id: str,
    request: Request,
    after_seq: int = Query(0, alias="afterSeq", ge=0),
    last_event_id: str | None = Header(None),
):
    """SSE. 먼저 구독을 건 뒤 DB의 afterSeq 이후를 보내고, 이어서 실시간 이벤트를 보낸다.

    브라우저가 자동 재연결할 때 보내는 Last-Event-ID(= seq)가 있으면 그것을 우선한다.
    구독과 replay가 겹쳐도 seq로 중복을 거르므로 빠지거나 두 번 가는 이벤트가 없다.
    """
    services = _services(request)
    _guard(lambda: services.projects.get(project_id))
    if last_event_id and last_event_id.isdigit():
        after_seq = max(after_seq, int(last_event_id))
    store = services.events
    subscriber = store.subscribe(project_id)

    def frame(event: dict) -> str:
        return f"id: {event['seq']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"

    async def generate():
        last_sent = after_seq
        try:
            yield "retry: 2000\n\n"
            for event in store.list_after(project_id, after_seq):
                last_sent = event["seq"]
                yield frame(event)
            while not await request.is_disconnected():
                try:
                    event = await asyncio.wait_for(subscriber.queue.get(), timeout=SSE_KEEPALIVE_SECONDS)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                    continue
                if event["seq"] <= last_sent:
                    continue
                if event["seq"] > last_sent + 1:
                    # 드물게 순서가 어긋나면 빠진 구간을 DB에서 채운다
                    for missing in store.list_after(project_id, last_sent):
                        if missing["seq"] >= event["seq"]:
                            break
                        last_sent = missing["seq"]
                        yield frame(missing)
                last_sent = event["seq"]
                yield frame(event)
        finally:
            store.unsubscribe(project_id, subscriber)

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# --- 레퍼런스 ---------------------------------------------------------------------


@router.post("/projects/{project_id}/references", status_code=201, dependencies=OWNER)
def add_reference(
    project_id: str,
    request: Request,
    source: str = Form(...),
    apply_policy: str = Form("nextStage", alias="applyPolicy"),
    file: UploadFile | None = File(None),
    url: str = Form(""),
    title: str = Form(""),
    text: str = Form(""),
):
    """multipart/form-data 하나로 받는다. source = file | url | text"""
    projects = _services(request).projects
    if source == "file" and file is not None:
        return _guard(lambda: projects.add_file_reference(
            project_id, file.filename or "file", file.file, file.content_type, apply_policy))
    if source == "url":
        return _guard(lambda: projects.add_url_reference(project_id, url, title, apply_policy))
    if source == "text":
        return _guard(lambda: projects.add_text_reference(project_id, title, text, apply_policy))
    raise _error(400, "invalid_request", "source는 file(파일 포함) · url · text 중 하나여야 합니다.")


@router.delete("/projects/{project_id}/references/{reference_id}", status_code=204, dependencies=OWNER)
def remove_reference(project_id: str, reference_id: str, request: Request):
    _guard(lambda: _services(request).projects.remove_reference(project_id, reference_id))


# --- 작업물 ----------------------------------------------------------------------


def _download_url(request: Request, project_id: str, artifact_id: str) -> str:
    return str(request.url_for("download_artifact", project_id=project_id, artifact_id=artifact_id))


@router.get("/projects/{project_id}/artifacts")
def list_artifacts(project_id: str, request: Request):
    return _guard(lambda: _services(request).projects.artifact_list(project_id))


@router.get("/projects/{project_id}/artifacts/{artifact_id}")
def get_artifact(project_id: str, artifact_id: str, request: Request):
    return _guard(lambda: _services(request).projects.artifact(project_id, artifact_id))


@router.get("/projects/{project_id}/artifacts/{artifact_id}/content")
def artifact_content(project_id: str, artifact_id: str, request: Request):
    url = _download_url(request, project_id, artifact_id)
    return _guard(lambda: _services(request).projects.artifact_content(project_id, artifact_id, url))


@router.get("/projects/{project_id}/artifacts/{artifact_id}/download", name="download_artifact")
def download_artifact(project_id: str, artifact_id: str, request: Request, inline: bool = False):
    projects = _services(request).projects
    path = _guard(lambda: projects.artifact_path(project_id, artifact_id))
    row = projects.artifact(project_id, artifact_id)
    return FileResponse(path, media_type=row["mime_type"], filename=row["name"],
                        content_disposition_type="inline" if inline else "attachment")


# --- 에이전트 설정(전역) ------------------------------------------------------------


@router.get("/settings/agents")
def list_agent_settings(request: Request):
    """읽기는 누구나(Guest는 보기만). 실제로 반영되는 선택지와 잠긴 이유를 함께 준다."""
    return _services(request).agent_settings.list()


@router.patch("/settings/agents/{agent_id}", dependencies=OWNER)
def update_agent_setting(agent_id: str, body: AgentConfig, request: Request):
    settings = _services(request).agent_settings
    try:
        settings.update(agent_id, body.model_dump())
    except KeyError as error:
        raise _error(404, "not_found", f"알 수 없는 에이전트: {agent_id}") from error
    except UnsupportedConfigError as error:
        raise _error(400, "unsupported_config", str(error)) from error
    return settings.list()


@router.delete("/settings/agents/{agent_id}", dependencies=OWNER)
def reset_agent_setting(agent_id: str, request: Request):
    settings = _services(request).agent_settings
    try:
        settings.reset(agent_id)
    except KeyError as error:
        raise _error(404, "not_found", f"알 수 없는 에이전트: {agent_id}") from error
    return settings.list()


@router.get("/system/usage")
def system_usage(request: Request):
    """실제로 확인되는 값만. 확인할 수 없으면 available=false와 이유."""
    settings = _services(request).settings
    return usage_report(settings.claude_usage_file, settings.codex_usage_live, settings.log_dir)


# --- 인증(단일 Owner) ------------------------------------------------------------------


def _session_payload(request: Request, authenticated: bool) -> dict:
    auth = _services(request).auth
    return {"configured": auth.configured(), "authenticated": authenticated,
            "pinManagedByEnv": auth.pin_managed_by_env(),
            "profile": auth.profile() if authenticated else None}


@router.get("/auth/session")
def auth_session(request: Request):
    auth = _services(request).auth
    return _session_payload(request, auth.is_owner(request.cookies.get(SESSION_COOKIE)))


@router.post("/auth/login")
def login(body: LoginBody, request: Request, response: Response):
    services = _services(request)
    try:
        token = services.auth.login(body.pin)
    except AuthError as error:
        status = 429 if error.retry_after else 401
        headers = {"Retry-After": str(error.retry_after)} if error.retry_after else None
        return JSONResponse(status_code=status, headers=headers,
                            content={"detail": {"code": "login_failed", "message": str(error)}})
    response.set_cookie(SESSION_COOKIE, token, max_age=SESSION_DAYS * 86400, httponly=True,
                        samesite="lax", secure=services.settings.cookie_secure, path="/")
    return _session_payload(request, True)


@router.post("/auth/logout")
def logout(request: Request, response: Response):
    _services(request).auth.logout(request.cookies.get(SESSION_COOKIE))
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, samesite="lax")
    return _session_payload(request, False)


@router.patch("/auth/profile", dependencies=OWNER)
async def update_profile(
    request: Request,
    nickname: str | None = Form(None),
    remove_avatar: bool = Form(False, alias="removeAvatar"),
    avatar: UploadFile | None = File(None),
):
    image = None
    if avatar is not None:
        data = await avatar.read(AVATAR_MAX_BYTES + 1)
        image = (data, avatar.content_type or "")
    try:
        _services(request).auth.update_profile(nickname, image, remove_avatar)
    except AuthError as error:
        raise _error(400, "invalid_request", str(error)) from error
    return _session_payload(request, True)


@router.get("/auth/avatar")
def owner_avatar(request: Request):
    path = _services(request).auth.avatar_path()
    if path is None:
        raise _error(404, "not_found", "프로필 이미지가 없습니다.")
    return FileResponse(path, headers={"Cache-Control": "no-cache"})


@router.post("/auth/pin", dependencies=OWNER)
def change_pin(body: PinChange, request: Request, response: Response):
    try:
        _services(request).auth.change_pin(body.currentPin, body.newPin)
    except AuthError as error:
        raise _error(400, "invalid_request", str(error)) from error
    # 모든 세션을 끊었으므로 이 브라우저도 다시 로그인한다
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, samesite="lax")
    return _session_payload(request, False)
