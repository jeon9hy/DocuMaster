@echo off
rem DocuMaster 웹앱: 로컬 백엔드(8000)와 화면(3000)을 켜고 브라우저를 엽니다.
rem 백엔드 창과 이 창을 닫으면 둘 다 꺼집니다.
rem 기본은 실제 Claude 오케스트레이터. 비용 없는 테스트가 필요할 때만 먼저 set DOCUMASTER_ORCHESTRATOR=fake
chcp 65001 >nul
cd /d "%~dp0"

if not exist server\.venv (
  echo 처음 실행이라 백엔드 환경을 만듭니다...
  python -m venv server\.venv || goto :error
  server\.venv\Scripts\python -m pip install -q -r server\requirements.txt || goto :error
)
if not exist node_modules (
  echo 처음 실행이라 화면에 필요한 파일을 설치합니다...
  call npm install || goto :error
)

rem Owner PIN이 없으면 한 번 정한다(원문은 저장하지 않고 해시만 .data\owner.json에)
if "%DOCUMASTER_OWNER_PIN_HASH%"=="" if not exist .data\owner.json (
  echo Owner 로그인에 쓸 6자리 PIN을 정합니다.
  pushd server
  .venv\Scripts\python setup_owner.py
  popd
)

if "%DOCUMASTER_ORCHESTRATOR%"=="" set DOCUMASTER_ORCHESTRATOR=claude
echo 오케스트레이터: %DOCUMASTER_ORCHESTRATOR%
start "DocuMaster Backend" /d "%~dp0server" cmd /k ".venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

rem localhost는 IPv6(::1)부터 시도해 느려질 수 있어 127.0.0.1로 둔다.
rem 화면도 같은 호스트(127.0.0.1)로 열어야 로그인 쿠키가 API 요청에 실린다.
set NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
start "" http://127.0.0.1:3000
call npm run dev
goto :eof

:error
echo 설치에 실패했습니다. 위 메시지를 확인하세요.
pause
