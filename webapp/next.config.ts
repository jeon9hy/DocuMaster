import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // start.bat은 화면을 127.0.0.1로 연다(API와 같은 호스트여야 로그인 쿠키가 실린다).
  // 개발 서버는 localhost 외 호스트의 개발용 리소스 요청을 막으므로 허용해 둔다 — 빠지면 화면이 「불러오는 중」에서 멈춘다.
  allowedDevOrigins: ["127.0.0.1"],
};

export default nextConfig;
