---
name: doc-finish
description: 문서 모드의 마무리 — 아냐가 쓴 07을 기계 검사하고, 로이드 Lite Review와 Render Gate를 거쳐 필요한 경우에만 제한 수정한 뒤 cross-check로 넘긴다. 로이드 전용 — DOCUMENT 모드에서 07이 저장된 직후에 쓴다.
user-invocable: true
---

# 문서 마무리 — 그대로 제출할 최종본으로

기준은 `공통/문서규격.md`다. 품질 단계는 줄이지 않는다. 대신 **같은 것을 두 번 읽지 않게** 한다.

## 1. 굽기
```bash
W="작업/$ID/workspace"; O="작업/$ID/output"
python .claude/tools/gate_check.py "$ID" 07                                    # FAIL은 아냐에게, CHECK는 정독 때 닫는다
python .claude/tools/md2html.py "$W/07_final_document.md" "$O/$ID.html"      # `경고:` 줄부터 닫는다
python .claude/tools/make_pdf.py "$O/$ID.html" "$O/$ID.pdf" --label "$ID"    # 마지막 줄이 "검사 결과: OK"
python - "$O/$ID.pdf" "$O/contact.png" <<'EOF'
import sys, io, fitz; from PIL import Image
d=fitz.open(sys.argv[1]); ims=[Image.open(io.BytesIO(p.get_pixmap(dpi=40).tobytes("png"))) for p in d]
w,h=ims[0].size; c=4; s=Image.new("RGB",(w*c,h*((len(ims)+c-1)//c)),"white")
for i,im in enumerate(ims): s.paste(im,((i%c)*w,(i//c)*h))
s.save(sys.argv[2]); print(d.page_count,"쪽")
EOF
```

## 2. 로이드 Lite Review — 마지막 이상 탐지

공동 집필이나 취향 검수가 아니다. 07을 한 번 읽으며 아래 네 범주만 본다.

- **FACT**: 수치·날짜·단위·법적 조건·출처 대응 오류, 근거보다 강한 인과.
- **LOGIC**: 앞뒤 모순, 본문에서 나오지 않는 결론, 중요한 조건 누락, 동일 개념의 상충 정의.
- **INTERNAL**: 에이전트명·중간 파일명·`05`·`06`·내부 경로·로그·오케스트레이션 표현.
- **DUP**: 같은 한계·판단의 반복, 요약과 결론 중복, 표·차트 숫자 재낭독.

문장 취향, 소제목 재작성, 목차 재설계, 새 차트 제안은 하지 않는다. 문제가 없으면 개선점을 만들지 않는다. 동시에 요약·결론·제목의 수치, 인용문, 기관·인명, 차트 대표값을 교차 확인 후보로 `기록.md`에 근거 ID와 함께 적는다.

문제가 없으면 `# Review\n\nSTATUS: PASS`, 있으면 `STATUS: REVISE`와 `[FACT|LOGIC|INTERNAL|DUP]` 이슈만 최대 8개 남긴다.

## 3. Render Gate — 모아보기 먼저, 확대는 의심 쪽만
`contact.png` 한 장으로 전 쪽의 흐름을 본다: 표지와 accent · 과도한 공백/밀집 · 쪽 끝에 홀로 남은 제목 · 비주얼과 본문의 균형. 비주얼의 장별 할당량은 검사하지 않는다.
00에 정확한 쪽수 제약이 있으면 PDF 쪽수와 대조한다. 다르면 Render Gate 실패다. 표·차트·`자료:`·한정·출처가 있는 쪽과 모아보기에서 걸린 쪽만 확대해서 본다:
```bash
python -c "import fitz,sys; d=fitz.open('$O/$ID.pdf'); [d[int(n)-1].get_pixmap(dpi=100).save('$O/p%02d.png'%int(n)) for n in sys.argv[1:]]" 3 7
```
확대해서 볼 것: 본문 인용이 작은 위첨자인가 · 출처가 별도 페이지에서 자료별 한 행인가 · 표·차트 잘림 · 값·조건이 05와 같은가 · `자료:`와 한정의 위치 · 글자 겹침.

## 4. 필요한 경우에만 제한 수정

`PASS`면 원고를 수정하지 않는다. `REVISE`면 §2·§3의 이슈를 위치와 함께 한 번에 보낸다.
`SendMessage(to:"<아냐>", message:"REVISE: <쪽/절 · [범주] 문제> 목록. 보고된 문제만 Edit.")`

아냐는 보고된 문제만 고치며 전체를 다시 쓰지 않는다. 다시 굽고 고친 쪽만 확대한다. 수정은 1회다. 남은 기계적 오류는 로이드가 고치고 기록한다.
LLM 검수 에이전트를 더 부르지 않는다. 그다음 `skills/cross-check`로 간다.
