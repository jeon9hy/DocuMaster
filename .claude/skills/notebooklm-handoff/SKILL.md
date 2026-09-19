---
name: notebooklm-handoff
description: 검수를 마친 발표팩(07)을 NotebookLM에 넘겨 슬라이드 초안을 만든다(기본은 슬라이드만 — 인포그래픽·브리핑은 사용자가 요청할 때만). `nlm` CLI가 인증돼 있으면 로이드가 직접 돌리고, 아니면 업로드 목록과 프롬프트를 사용자에게 넘긴다. 생성물 검사(Render Gate)와 최종 이관까지 포함. 로이드 전용 — PRESENTATION 모드의 마지막 단계.
user-invocable: true
---

# NotebookLM 인계

## 0. 경로 정하기
```bash
python .claude/tools/nlm_pipeline.py check
```
| 결과 | 경로 |
| --- | --- |
| `인증 OK` | §2 자동 |
| `인증되지 않았다` | 무인 갱신(`nlm auth refresh`)까지 이미 실패한 결과다(E-019). 사용자에게 `nlm login`을 부탁하고, 안 되면 §5 |
| `nlm 을 찾지 못했다` | §6 설치 → 안 되면 §5 |

**호출한 척하거나 결과를 가정하지 않는다.** 못 돌렸으면 "발표팩까지 완성, 생성은 사용자 몫"이라고 보고한다.

## 1. 올릴 것
발표팩 `07_notebooklm_presentation_pack.md`, 핵심 원문(파일·URL), 사용자가 준 참고 디자인만 올린다.
00~06은 올리지 않는다(REMOVE가 되살아난다). 도구가 파일명으로 거부한다. 우회하지 않는다.

## 2. 자동 경로
```bash
python .claude/tools/nlm_pipeline.py run --id "$ID"        # 포그라운드로 돌린다 (백그라운드는 완료를 실패로 오판한다, E-025)
```
노트북 생성부터 업로드·생성·폴링·`output/` 다운로드·기계 검사·`_nlm_run.md` 기록까지 이어서 간다. 팩의 `# 제작 지시`가 프롬프트가 된다.
옵션: `--source <파일>`·`--url <URL>`(반복 가능) · `--artifacts slides,infographic`(요청 시에만) · `--slide-format presenter_slides|detailed_deck` ·
`--slide-length short` · `--timeout 3600` · `--slides-pptx`.
- 끊겼으면 `run`을 다시 돌리지 말고 `resume --id "$ID"`로 잇는다.
- 폴링이 10분 넘게 `unknown`만 내면 `nlm download slide-deck`을 직접 시도한다. 받아지면 완성이다(E-028).
- `RESOURCE_EXHAUSTED`는 한도다. 여러 번 두드리지 말고 멈추고 보고한다(E-037).

## 3. 검사 — 기계 검사 + Render Gate
`_nlm_run.md`의 기계 검사(장수, 빈 장, 파일 열림)를 먼저 본다. 슬라이드는 통 이미지라 숫자 검사가 안 되니(E-017) 눈으로 대조한다.
**모아보기 한 장으로 전체를 먼저 보고, 의심 장만 확대한다**(`skills/doc-finish` §1의 모아보기 스크립트에 `<ID>_slides.pdf`를 넣고 `dpi=60`, `c=3`으로 쓴다).
```bash
python -c "import fitz,sys; d=fitz.open(r'작업/$ID/output/${ID}_slides.pdf'); [d[int(n)-1].get_pixmap(dpi=110).save(r'작업/$ID/output/slide_p%02d.png'%int(n)) for n in sys.argv[1:]]" 3 9
```
- **모아보기에서 볼 것**: 발표규격 §6 재작업 대상 · 흐름과 리듬 · 한 덱처럼 보이는가 · 같은 캐릭터를 모든 장에서 비교(다른 동물·체형이면 실패).
- **확대해서 볼 것** — 숫자·한정·출처가 있는 장과 모아보기에서 걸린 장만 본다.
  - 팩에 없는 숫자나 주장(계산값 포함, E-018)
  - 한정 문구가 숫자 옆에 있고 읽히는가
  - 근거 ID·URL·검증 문단 노출
  - 로고, "공식" 표기, 사진풍 실존 얼굴, `Slide Title` 같은 자리표시자
  - 잘림·겹침, 워터마크 간섭

**실패한 장만 고친다.** 설계와 다르게 그렸으면 팩의 해당 필드를 그대로 인용해 revise한다. 설계 자체가 문제면 요르 06B로 돌린다.
```bash
nlm slides revise <artifact-id> --slide '3 제목을 지우고 「화면」의 주인공을 화면 절반 이상으로 키워 주세요' --confirm
```
revise는 원문을 다시 읽지 않는다. 없던 사실을 넣으라고 시키지 않는다. 고친 장만 다시 확대해서 본다.
목표는 **최종 편집이 쉬운 초안**이다. 선·비율이 조금 다른 것은 통과, 외형 오류와 노출된 검증 문단은 불통과다.

## 4. 이관 · 보고
```bash
python .claude/tools/nlm_pipeline.py promote --id "$ID"   # 검사 미통과면 보류된다. 직접 닫았을 때만 --force
```
`최종/<ID>/`에 `<ID>_슬라이드.pdf`와 `<ID>_발표팩.md`(최종 디자인 세션의 지시서)가 들어가고, `최종/_manifest.md`에 한 줄이 붙는다.
보고: 경로(자동/수동) · 노트북 URL · 올린 자료 · 슬라이드 수 · NotebookLM이 더하거나 빠뜨린 것 · 고친 장 · REMOVE·CAUTION · 남은 수동 작업.

## 5. 수동 경로
업로드 목록(§1)과 팩의 `# 제작 지시` 절을 그대로 사용자에게 넘긴다. 슬라이드만 안내한다. 받은 파일을 `output/`에 두면 §3으로 검사한다.
도구가 깨졌으면 재시도로 우회하지 말고 이 경로로 내려간다. 증상은 `환경기록.md`에 한 줄로 적는다.

## 6. 설치 (한 번만)
`uv tool install notebooklm-mcp-cli` → `nlm login`(사용자) → `nlm doctor`. 이 파이프라인은 MCP가 아니라 CLI를 쓴다.
