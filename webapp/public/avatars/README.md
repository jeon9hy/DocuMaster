# avatars — 에이전트 초상

실제 캐릭터 이미지를 쓰려면 정사각형 이미지를 아래 이름으로 넣고,
`src/constants/agents.ts`에서 해당 에이전트의 `avatarSrc`를 채우세요. 예: `avatarSrc: "/avatars/loid.png"`

| 파일 | 에이전트 |
| --- | --- |
| `loid.png` | 로이드 포저 |
| `yor.png` | 요르 포저 |
| `yuri.png` | 유리 브라이어 |
| `anya.png` | 아냐 포저 |
| `bond.png` | 본드 |

비워 두면 `src/components/agent/portraits.tsx`의 SVG 초상을 씁니다.
