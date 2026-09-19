---
name: doc-finish
description: 문서 모드의 마무리 — 아냐가 쓴 07을 PDF로 굽고, 로이드가 정독과 Render Gate(모아보기 → 의심 쪽만 확대)를 한 번에 하고, 아냐에게 퇴고 1회를 보낸 뒤 cross-check로 넘긴다. 로이드 전용 — DOCUMENT 모드에서 07이 저장된 직후에 쓴다.
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

## 2. 정독 — 07 원고를 한 번만 읽는다
독자로서 처음부터 끝까지 읽으며 **두 목록을 동시에** 만든다.
- **퇴고 목록**: 첫 쪽만 봐도 결론이 서는가 · 걸리는 문장·반복·번역투 · 표기 불일치 · 요약이 본문보다 센 곳
- **교차 확인 후보**: 요약·결론·제목의 수치 · 인용문 · 기관·인명 · 차트 대표값 → `기록.md`에 근거 ID와 함께 적는다. cross-check가 07을 다시 읽지 않고 이 목록을 쓴다.

## 3. Render Gate — 모아보기 먼저, 확대는 의심 쪽만
`contact.png` 한 장으로 전 쪽의 흐름을 본다: 표지와 accent · 장마다 Key Visual의 자리 · 본문만 두 쪽 넘게 이어지는 곳 · 쪽 끝에 홀로 남은 제목.
표·차트·`자료:`·한정이 있는 쪽과 모아보기에서 걸린 쪽만 확대해서 본다:
```bash
python -c "import fitz,sys; d=fitz.open('$O/$ID.pdf'); [d[int(n)-1].get_pixmap(dpi=100).save('$O/p%02d.png'%int(n)) for n in sys.argv[1:]]" 3 7
```
확대해서 볼 것: 표·차트 잘림 · 차트 값이 06B와 같은가 · `자료:`와 한정의 위치 · 글자 겹침.

## 4. 퇴고 1회
§2·§3에서 걸린 곳을 **위치와 함께 한 번에 모아** 보낸다 —
`SendMessage(to:"<아냐>", message:"퇴고: <쪽/절 · 문제 · 요청> 목록. 지적한 곳만 Edit.")`
다시 굽고, **고친 쪽만** 확대해서 확인한다. 퇴고는 1회다. 남은 기계적 오류는 로이드가 고치고 기록한다.
LLM 검수 에이전트를 더 부르지 않는다. 그다음 `skills/cross-check`로 간다.
