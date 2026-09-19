import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Nunito } from "next/font/google";
import { BRAND } from "@/constants/brand";
import "./globals.css";

// 워드마크("documaster") 글자용 둥근 서체. 본문은 Pretendard(아래 CDN)를 쓴다.
const nunito = Nunito({ subsets: ["latin"], weight: ["800"], variable: "--font-nunito" });

export const metadata: Metadata = {
  title: BRAND.name,
  description: BRAND.tagline,
  icons: { icon: BRAND.markSrc },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ko" className={`${nunito.variable} h-full antialiased`}>
      <head>
        <link
          rel="stylesheet"
          href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css"
        />
      </head>
      <body className="h-full">{children}</body>
    </html>
  );
}
