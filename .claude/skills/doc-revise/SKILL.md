---
name: doc-revise
description: 완료된 문서(DOC 최종본)를 사용자의 첨삭 요청대로 고친다 — 로이드가 요청을 05 안에서 고칠 수 있는 것과 새 사실이 필요한 것으로 가르고, 아냐가 07 새 버전에 지시 항목만 고치고, 로이드가 바뀐 구간을 검사·렌더한 뒤 최종본을 교체한다. 로이드 전용 — `상태: 완료`인 DOCUMENT 작업에 첨삭 요청이 왔을 때 쓴다.
user-invocable: true
---

# 첨삭 — 완료된 문서를 05 안에서 고친다

요르·유리를 부르지 않는다. 검증 라운드가 없으므로 **05에 없는 사실은 첨삭으로 들어오지 못한다**(CLAUDE.md §3). PPT는 대상이 아니다.
`R` = 이 작업의 첨삭 회차(`output/revise_r*.md` 수 + 1). 07 원문 전체는 이 절차에서 한 번만 읽는다.
**대상** = 요청의 `[첨삭 대상]` PDF(없으면 `<ID>.pdf`). `$PDF` = 그 이름(확장자 없이), `$DOC` = 그 PDF의 원고 07 —
`<ID>.pdf`면 `07_final_document`, 그 밖이면 `상태.md` 07 칸·`기록.md`에서 찾는다(못 찾으면 묻는다). 최종본이 여러 부여도 대상 하나만 고친다.

## 1. 시작
```bash
python .claude/tools/stage.py set --id "$ID" --status "진행 중 첨삭 r$R" --next "doc-revise"   # 웹앱은 이미 해 두었다
ls -d 최종/*/"$ID"                                   # 유형 폴더 = finish --kind 값
ls 작업/"$ID"/workspace/"$DOC"*.md                   # 최신 버전과 다음 번호(_v02, _v03 …)
```

## 2. 요청 가르기 — 로이드
최신 07과 05 첫 줄·§2·§5를 읽고(`sed -n '1p;/^## 2\./,/^## 3\./p;/^## 5\./,$p'`) 요청을 항목으로 나눠 하나씩 판정한다.

| 판정 | 무엇 |
| --- | --- |
| **반영** | 문장·말투·길이, 순서·장 구조·제목, 표·그림 배치, 05 §2에 있는 사실을 더 쓰거나 빼기, 해석을 판단으로 더 풀기 |
| **불가 · 새 사실** | 05에 없는 사실·수치·예시·출처·계산이 있어야 하는 요청 |
| **불가 · 근거** | CAUTION의 범위·라벨 삭제, REMOVE 항목 되살리기, 근거보다 센 결론·인과, `독자 한계` 삭제 |

취향(문체·색)은 묻지 않고 가정해서 적는다. 애매한 위치는 07에서 가장 가까운 곳으로 잡고 적는다.
`작업/$ID/output/revise_r$R.md`에 **요청 원문 · 항목별 판정과 이유 · 아냐 지시**를 쓴다. 아냐 지시는 항목마다 `위치(장 제목 + 인용 한 구절) · 무엇이 불편한가 · 방향`이다. 고친 문장을 로이드가 미리 쓰지 않는다.

**반영할 항목이 없으면** 아냐를 부르지 않는다. `stage.py set --status "사용자 승인 대기 · 첨삭 r$R"`로 두고, 불가 이유와 선택지(요청 바꾸기 / 새 작업으로 조사)를 묻는다.
답이 취소면 `stage.py set --status 완료 --next "없음 — <최종 경로>" --log "첨삭 r$R 취소"`로 닫는다. 일부만 불가면 멈추지 않고 진행해 완료 보고에 올린다.

## 3. 아냐 — 07 새 버전
`실행.md` §5와 같은 방법으로 모델 JSON의 `anya.model`을 쓴다.
```
Agent(subagent_type:"general-purpose", description:"아냐 첨삭 r<R>", model:<아냐 모델>,
  prompt: "너는 아냐다. 먼저 .claude/아냐/첨삭.md 와 .claude/공통/문서규격.md 를 읽고 그대로 따른다.
          입력(이것만): ./작업/<ID>/workspace/<최신 07> · 00_user_brief.md · 05_verified_research_pack.md(첫 줄·§2·§5만)
          글 유형 파일: .claude/공통/글_<00의 유형>.md · 첨삭 지시: ./작업/<ID>/output/revise_r<R>.md
          출력: ./작업/<ID>/workspace/<$DOC>_v<NN>.md (최신 07을 복사한 뒤 지시 항목만 Edit). 응답은 항목별 처리 3~8줄.")
```

## 4. 확인 — 로이드, 바뀐 구간만
```bash
python .claude/tools/render_doc.py "$ID" --doc "$DOC" --name "$PDF"   # 최신 $DOC로 기계 검사 + output/$PDF.pdf·contact.png
git diff --no-index --word-diff=plain 작업/"$ID"/workspace/<이전 07> 작업/"$ID"/workspace/<새 07>
```
- 종료 코드 1·「경고:」는 doc-finish §1과 같이 닫는다. 3이면 멈추고 보고한다.
- diff에서 본다: **지시 밖 수정**(되돌리게 한다) · 새로 생긴 숫자·날짜·기관·인명이 이전 07이나 05 §2에 있는가 · 범위·라벨·CAUTION 조건·위첨자가 따라왔는가 · 결론이 세졌는가 · 제작 과정 유출(doc-finish §2 INTERNAL).
- 05 §2에서 처음 본문에 들어온 수치가 요약·결론·제목에 오르면 그 값만 `skills/cross-check`로 원문을 대조한다. 그 밖에는 원문을 다시 열지 않는다.
- 렌더는 doc-finish §3대로 모아보기를 보고 바뀐 쪽만 확대한다. 장 구조를 바꿨으면 전 쪽을 본다.
- 문제는 한 번에 묶어 `SendMessage(to:"<아냐>", message:"REVISE: …")` 1회. 남은 기계적 오류는 로이드가 고친다. 내용 문제가 남으면 교체하지 않고 보고한다.

`revise_r$R.md` 끝에 확인 결과(지시별 반영 여부 · 확인한 쪽 · 교차 확인 · 남은 것)를 덧붙인다.

## 5. 교체와 보고
```bash
python .claude/tools/stage.py finish --id "$ID" --kind <1의 유형 폴더> --file "$PDF.pdf"   # 이전판을 ${PDF}_vNN.pdf로 남기고 output/$PDF.pdf → 최종/<유형>/$ID/ (manifest 줄은 그대로)
python .claude/tools/stage.py log --id "$ID" "첨삭 r$R: 07 v<NN> · 반영 n · 불가 n · 교차 확인 n/n · 아냐 에이전트=<id>"
```
이전 최종 PDF는 `finish`가 같은 폴더에 `<$PDF>_vNN.pdf`로 남기고, `<$PDF>.pdf`는 늘 최신본이다. 다른 최종 PDF는 그대로 둔다. 보고(CLAUDE.md §7): 최종 경로·07 버전 · **반영한 것** · **반영하지 않은 것과 이유**(새 사실이 필요하면 새 작업으로 조사해야 한다고 쓴다) · 확인 범위 · 모델.
