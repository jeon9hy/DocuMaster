// node --test가 src/의 TypeScript를 바로 읽게 하는 최소 설정(의존성 없음).
// Node 24의 타입 제거 기능을 쓰고, "@/..." 별칭과 확장자 없는 import만 풀어 준다.
import { register } from "node:module";

register("./resolve-hooks.mjs", import.meta.url);
