#!/usr/bin/env python3
"""Render per-issue detail pages for the GitHub Pages dashboard."""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
DOCS = ROOT / 'docs'
SRC = DATA / 'next_meeting_radar_enhanced.json'


def esc(x) -> str:
    return html.escape(str(x or ''))


def slug(issue_id: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_-]+','-', issue_id or 'issue').strip('-')


def li(items):
    return '\n'.join(f'<li>{esc(x)}</li>' for x in items if x)


def render_issue(p: dict, rank: int, generated: str) -> None:
    issue = slug(p.get('issue_id'))
    out = DOCS / f'issue-{rank}-{issue}.html'
    like = p.get('cabinet_question_likelihood') or {}
    synth = p.get('question_synthesis') or {}
    align = p.get('ministry_work_alignment') or {}
    stat = p.get('statistical_evidence') or {}
    cases = p.get('similar_historical_cases') or []
    flow = p.get('question_flow') or []
    articles = p.get('items') or []
    questions = synth.get('questions') or []
    oral = p.get('oral_brief') or {}
    prep = next((f.get('items') for f in flow if f.get('stage') == 'minister_prep'), []) or []
    evidence = stat.get('answer_evidence_cards') or []
    html_doc = f'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{esc(p.get('ministry'))} · {esc(p.get('issue_id'))}</title>
<style>
:root {{ --ink:#111827; --muted:#64748b; --line:#e5e7eb; --bg:#f8fafc; --card:#fff; --blue:#1d4ed8; }}
body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; background:var(--bg); color:var(--ink); line-height:1.65; }}
main {{ max-width:920px; margin:0 auto; padding:34px 20px 80px; }}
a {{ color:var(--blue); font-weight:800; text-decoration:none; }} a:hover {{ text-decoration:underline; }}
.back {{ display:inline-block; margin-bottom:22px; }}
.hero {{ background:#0f172a; color:white; border-radius:30px; padding:28px; margin-bottom:20px; }}
.meta {{ display:flex; gap:8px; flex-wrap:wrap; margin-bottom:12px; }}
.meta span {{ background:rgba(255,255,255,.1); border:1px solid rgba(255,255,255,.16); padding:5px 9px; border-radius:999px; font-size:13px; }}
h1 {{ font-size:34px; line-height:1.18; letter-spacing:-.04em; margin:0 0 12px; }}
.hero p {{ color:#cbd5e1; margin:0; }}
.grid {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }}
.card {{ background:white; border:1px solid var(--line); border-radius:22px; padding:20px; margin:14px 0; }}
.card h2 {{ margin:0 0 12px; font-size:19px; letter-spacing:-.02em; }}
.bigq {{ font-size:20px; font-weight:750; letter-spacing:-.02em; }}
.label {{ color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.08em; font-weight:900; }}
.score {{ font-size:42px; font-weight:900; letter-spacing:-.06em; }}
ul {{ padding-left:20px; margin:8px 0 0; }}
li {{ margin:6px 0; }}
.article {{ border-top:1px solid var(--line); padding-top:10px; margin-top:10px; color:#334155; }}
@media (max-width:760px) {{ .grid {{ grid-template-columns:1fr; }} h1 {{ font-size:28px; }} }}
</style></head><body><main>
<a class="back" href="index.html">← Dashboard</a> · <a class="back" href="memo-{rank}-{issue}.md">Copy-ready memo</a>
<section class="hero">
  <div class="meta"><span>#{rank}</span><span>{esc(p.get('ministry'))}</span><span>{esc(p.get('issue_id'))}</span><span>{esc(like.get('band'))}</span></div>
  <h1>{esc(synth.get('diagnosis'))}</h1>
  <p>Generated {esc(generated)} · 최근 7일 뉴스 기반 장관 답변 준비 패킷</p>
</section>
<section class="grid">
  <div class="card"><div class="label">Question likelihood</div><div class="score">{esc(like.get('score'))}</div><p>{esc(like.get('band'))}</p></div>
  <div class="card"><div class="label">Connected work</div><h2>{esc(', '.join((align.get('function_domains') or [])[:4]))}</h2><p>{esc(', '.join((align.get('matched_work_signals') or [])[:8]))}</p></div>
</section>
<section class="card"><h2>30초 구두보고</h2><p class="bigq">{esc(oral.get('thirty_second'))}</p></section>
<section class="card"><div class="label">대통령 예상 질문</div><p class="bigq">{esc((questions[0] or {}).get('question') if questions else '')}</p></section>
<section class="card"><h2>예상 답변 골격</h2><ul>{li(oral.get('answer_skeleton') or [])}</ul><p class="article"><b>부족한 근거:</b> {esc(oral.get('evidence_gap'))}</p></section>
<section class="card"><h2>예상 질의 흐름</h2><ul>{''.join(f'<li><b>{esc(f.get("stage"))}</b>: {esc(f.get("question") or ", ".join(f.get("items",[])))}</li>' for f in flow[:5])}</ul></section>
<section class="card"><h2>장관 답변 준비 체크리스트</h2><ul>{li(prep)}</ul></section>
<section class="card"><h2>답변에 써야 할 통계 근거</h2><p>{esc(stat.get('answer_frame'))}</p><ul>{''.join(f'<li><b>{esc(e.get("stat"))}</b>: {esc(e.get("use_in_answer"))}</li>' for e in evidence[:4])}</ul></section>
<section class="card"><h2>과거 유사 질문</h2><ul>{''.join(f'<li>{esc(c.get("meeting_date"))} · {esc(c.get("question_type"))} — {esc(c.get("excerpt"))}</li>' for c in cases[:4])}</ul></section>
<section class="card"><h2>대표 기사</h2>{''.join(f'<p class="article"><b>{esc(a.get("pub_date"))}</b> · score {esc(a.get("relevance_score"))}<br>{esc(a.get("title"))}</p>' for a in articles[:6])}</section>
</main></body></html>'''
    out.write_text(html_doc)


def main() -> int:
    data = json.loads(SRC.read_text())
    generated = data.get('generated_at','')
    for i,p in enumerate((data.get('packets') or [])[:5], 1):
        render_issue(p, i, generated)
    print('rendered issue pages')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
