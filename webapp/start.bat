@echo off
rem DocuMaster 웹앱을 켜고 브라우저를 엽니다. 창을 닫으면 서버도 꺼집니다.
chcp 65001 >nul
cd /d "%~dp0"
if not exist node_modules (
  echo 처음 실행이라 필요한 파일을 설치합니다...
  call npm install
)
start "" http://localhost:3000
call npm run dev
