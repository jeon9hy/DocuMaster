"use client";

import { useState, type ReactNode } from "react";
import { useServerInsertedHTML } from "next/navigation";
import { CacheProvider, ThemeProvider, createCache } from "@wanteddev/wds";

/**
 * 원티드 Montage 디자인 시스템 연결. @wanteddev/wds-nextjs의 AppRouterCacheProvider와 같은 일을 하되,
 * Montage(Emotion) 스타일을 `@layer wds`에 넣어 Tailwind 유틸리티(`xl:hidden` 등)가 덮어쓸 수 있게 한다.
 * 레이어 순서는 globals.css 맨 위에서 정한다.
 */
const LAYER = "@layer wds{";

function useMontageCache() {
  const [registry] = useState(() => {
    const cache = createCache({ key: "wds" });
    cache.compat = true;
    const insert = cache.insert;
    let inserted: { name: string; isGlobal: boolean }[] = [];
    cache.insert = (selector, serialized, sheet, shouldCache) => {
      if (!serialized.styles.startsWith(LAYER)) {
        serialized.styles = `${LAYER}${serialized.styles}}`;
      }
      if (cache.inserted[serialized.name] === undefined) {
        inserted.push({ name: serialized.name, isGlobal: !selector });
      }
      return insert(selector, serialized, sheet, shouldCache);
    };
    const flush = () => {
      const flushed = inserted;
      inserted = [];
      return flushed;
    };
    return { cache, flush };
  });

  // 서버에서 그린 스타일을 HTML에 실어 보내 첫 화면이 깜빡이지 않게 한다
  useServerInsertedHTML(() => {
    const names = registry.flush();
    if (names.length === 0) return null;
    let styles = "";
    let attribute = registry.cache.key;
    const globals: { name: string; style: string }[] = [];
    for (const { name, isGlobal } of names) {
      const style = registry.cache.inserted[name];
      if (typeof style !== "string") continue;
      if (isGlobal) {
        globals.push({ name, style });
      } else {
        styles += style;
        attribute += ` ${name}`;
      }
    }
    return (
      <>
        {globals.map(({ name, style }) => (
          <style key={name} data-emotion={`${registry.cache.key}-global ${name}`} dangerouslySetInnerHTML={{ __html: style }} />
        ))}
        {styles && <style data-emotion={attribute} dangerouslySetInnerHTML={{ __html: styles }} />}
      </>
    );
  });

  return registry.cache;
}

export function MontageProvider({ children }: { children: ReactNode }) {
  const cache = useMontageCache();
  return (
    <CacheProvider value={cache}>
      {/* 라이트 고정. 바탕색은 globals.css가 정한다 */}
      <ThemeProvider disableDefaultGlobalStyle>{children}</ThemeProvider>
    </CacheProvider>
  );
}
