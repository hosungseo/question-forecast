#!/usr/bin/env python3
"""Export copy-ready per-issue minister answer memos."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
DOCS = ROOT / 'docs'
SRC = DATA / 'next_meeting_radar_enhanced.json'


def slug(x: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_-]+','-', x or 'issue').strip('-')


def bullets(items):
    return '\n'.join(f'- {x}' for x in items if x)


def write_memo(p: dict, rank: int, generated: str) -> Path:
    issue = slug(p.get('issue_id'))
    out = DOCS / f'memo-{rank}-{issue}.md'
    like = p.get('cabinet_question_likelihood') or {}
    synth = p.get('question_synthesis') or {}
    align = p.get('ministry_work_alignment') or {}
    stat = p.get('statistical_evidence') or {}
    oral = p.get('oral_brief') or {}
    flow = p.get('question_flow') or []
    prep = next((f.get('items') for f in flow if f.get('stage') == 'minister_prep'), []) or []
    questions = synth.get('questions') or []
    evidence = stat.get('answer_evidence_cards') or []
    cases = p.get('similar_historical_cases') or []
    articles = p.get('items') or []
    lines = [
        f"# {p.get('ministry')} — {p.get('issue_id')} 답변 준비 메모",
        '',
        f"- 생성: {generated}",
        f"- 질문 가능성: {like.get('score')} / {like.get('band')}",
        f"- 연결 업무: {', '.join((align.get('function_domains') or [])[:4])}",
        '',
        '## 30초 구두보고',
        oral.get('thirty_second',''),
        '',
        '## 대통령 예상 질문',
    ]
    for q in questions[:4]:
        lines.append(f"- **{q.get('move_label', q.get('move'))}**: {q.get('question')}")
    lines += ['', '## 답변 골격', bullets(oral.get('answer_skeleton') or []), '', '## 장관 준비 체크리스트', bullets(prep)]
    lines += ['', '## 답변에 써야 할 통계 근거']
    if stat.get('answer_frame'):
        lines.append(f"- 프레임: {stat.get('answer_frame')}")
    for e in evidence[:4]:
        lines.append(f"- **{e.get('stat')}**: {e.get('use_in_answer')} ({e.get('how_to_phrase')})")
    lines += ['', '## 과거 유사 질문']
    for c in cases[:4]:
        lines.append(f"- {c.get('meeting_date')} · {c.get('question_type')} — {c.get('excerpt')}")
    lines += ['', '## 대표 기사']
    for a in articles[:6]:
        lines.append(f"- {a.get('pub_date')} · score {a.get('relevance_score')} · {a.get('title')}")
    out.write_text('\n'.join(lines).strip() + '\n')
    return out


def main() -> int:
    data = json.loads(SRC.read_text())
    generated = data.get('generated_at','')
    paths = []
    for i,p in enumerate((data.get('packets') or [])[:5], 1):
        paths.append(write_memo(p, i, generated))
    for p in paths:
        print(p)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
