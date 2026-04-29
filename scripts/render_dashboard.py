#!/usr/bin/env python3
"""Render the GitHub Pages dashboard from enhanced radar JSON."""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
DOCS = ROOT / 'docs'
SRC = DATA / 'next_meeting_radar_enhanced.json'
OUT = DOCS / 'index.html'


def esc(x) -> str:
    return html.escape(str(x or ''))


def first_question(packet: dict) -> str:
    qs = ((packet.get('question_synthesis') or {}).get('questions') or [])
    return qs[0].get('question','') if qs else ''


def evidence(packet: dict) -> str:
    cards = ((packet.get('statistical_evidence') or {}).get('answer_evidence_cards') or [])
    if not cards:
        return '답변 근거 통계 후보 없음'
    return ' · '.join(c.get('stat','') for c in cards[:2])


def render_packet(p: dict, rank: int) -> str:
    like = p.get('cabinet_question_likelihood') or {}
    align = p.get('ministry_work_alignment') or {}
    delta = p.get('daily_delta') or {}
    band = like.get('band','-')
    score = like.get('score','-')
    domains = ', '.join((align.get('function_domains') or [])[:3])
    q = first_question(p)
    articles = p.get('items') or []
    lead_article = articles[0].get('title','') if articles else ''
    return f'''
    <article class="issue {esc(band)}">
      <div class="rank">{rank}</div>
      <div class="issue-main">
        <div class="meta"><span>{esc(p.get('ministry'))}</span><span>{esc(p.get('issue_id'))}</span><span>{esc(band)}</span></div>
        <h3>{esc((p.get('question_synthesis') or {}).get('diagnosis',''))}</h3>
        <p class="question">{esc(q)}</p>
        <div class="facts">
          <span>질문가능성 <b>{esc(score)}</b></span>
          <span>기사 {esc(p.get('count'))}건</span>
          <span>업무: {esc(domains)}</span>
        </div>
        <p class="evidence"><b>답변 근거</b> {esc(evidence(p))}</p>
        <p class="delta">{esc(delta.get('interpretation','전일 비교 없음'))}</p>
        <p class="article-title">대표 기사: {esc(lead_article)}</p>
      </div>
    </article>'''


def main() -> int:
    data = json.loads(SRC.read_text())
    packets = (data.get('packets') or [])[:5]
    generated = data.get('generated_at','')
    high = sum(1 for p in packets if (p.get('cabinet_question_likelihood') or {}).get('band') == 'cabinet_high')
    avg = round(sum(float((p.get('cabinet_question_likelihood') or {}).get('score') or 0) for p in packets) / max(len(packets),1), 1)
    issues_html = '\n'.join(render_packet(p, i+1) for i,p in enumerate(packets))
    html_doc = f'''<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Question Forecast</title>
  <style>
    :root {{ --ink:#111827; --muted:#6b7280; --soft:#f6f7f9; --line:#e5e7eb; --card:#fff; --blue:#1d4ed8; --green:#047857; --amber:#b45309; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; color:var(--ink); background:#f8fafc; line-height:1.55; }}
    main {{ max-width:1120px; margin:0 auto; padding:44px 20px 80px; }}
    .top {{ display:grid; grid-template-columns:1.3fr .7fr; gap:28px; align-items:end; border-bottom:1px solid var(--line); padding-bottom:28px; }}
    .eyebrow {{ color:var(--blue); font-weight:800; letter-spacing:.08em; text-transform:uppercase; font-size:12px; }}
    h1 {{ font-size:54px; letter-spacing:-.05em; line-height:.98; margin:10px 0 16px; }}
    .lead {{ font-size:19px; color:#374151; max-width:760px; margin:0; }}
    .stamp {{ text-align:right; color:var(--muted); font-size:14px; }}
    .stats {{ display:flex; gap:10px; justify-content:flex-end; margin-top:12px; flex-wrap:wrap; }}
    .stat {{ background:#fff; border:1px solid var(--line); border-radius:999px; padding:7px 11px; font-size:13px; }}
    .links {{ display:flex; gap:12px; flex-wrap:wrap; margin:22px 0 34px; }}
    a {{ color:var(--blue); text-decoration:none; font-weight:700; }}
    a:hover {{ text-decoration:underline; }}
    .links a {{ background:white; border:1px solid var(--line); padding:10px 13px; border-radius:999px; }}
    .issues {{ display:grid; gap:14px; }}
    .issue {{ display:grid; grid-template-columns:54px 1fr; gap:16px; background:var(--card); border:1px solid var(--line); border-radius:24px; padding:20px; box-shadow:0 10px 30px rgba(15,23,42,.04); }}
    .rank {{ width:42px; height:42px; border-radius:14px; display:grid; place-items:center; background:#111827; color:white; font-weight:800; }}
    .meta {{ display:flex; gap:8px; flex-wrap:wrap; margin-bottom:8px; }}
    .meta span {{ font-size:12px; color:#374151; background:#f3f4f6; border:1px solid #e5e7eb; padding:4px 8px; border-radius:999px; }}
    .cabinet_high .meta span:last-child {{ color:var(--green); background:#ecfdf5; border-color:#bbf7d0; }}
    .cabinet_review .meta span:last-child {{ color:var(--amber); background:#fffbeb; border-color:#fde68a; }}
    h3 {{ font-size:21px; line-height:1.35; letter-spacing:-.02em; margin:0 0 10px; }}
    .question {{ font-size:17px; margin:0 0 14px; color:#111827; }}
    .facts {{ display:flex; gap:8px; flex-wrap:wrap; margin-bottom:10px; }}
    .facts span {{ font-size:13px; background:#f8fafc; border:1px solid var(--line); padding:6px 9px; border-radius:10px; color:#374151; }}
    .evidence, .delta, .article-title {{ margin:7px 0 0; color:var(--muted); font-size:14px; }}
    .note {{ margin-top:34px; color:var(--muted); font-size:14px; border-top:1px solid var(--line); padding-top:22px; }}
    @media (max-width:760px) {{ .top {{ grid-template-columns:1fr; }} .stamp {{ text-align:left; }} .stats {{ justify-content:flex-start; }} h1 {{ font-size:42px; }} .issue {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body>
<main>
  <section class="top">
    <div>
      <div class="eyebrow">Cabinet intelligence prototype</div>
      <h1>Question Forecast</h1>
      <p class="lead">매일 보도를 부처 업무와 과거 국무회의 질문 패턴에 연결해, 장관이 준비해야 할 예상 질의와 답변 근거를 정리합니다.</p>
    </div>
    <div class="stamp">
      <div>Generated<br><b>{esc(generated)}</b></div>
      <div class="stats"><span class="stat">Top 5</span><span class="stat">High {high}</span><span class="stat">Avg {avg}</span></div>
    </div>
  </section>
  <nav class="links">
    <a href="briefing.md">Full briefing</a>
    <a href="radar.md">Radar markdown</a>
    <a href="gold-v1.md">Gold v1</a>
    <a href="threshold.md">Calibration</a>
    <a href="https://github.com/hosungseo/question-forecast">GitHub</a>
  </nav>
  <section class="issues">
    {issues_html}
  </section>
  <p class="note">Note: This is a decision-support radar, not a claim about actual presidential intent. Statistics are answer evidence, not literal presidential questions.</p>
</main>
</body>
</html>'''
    OUT.write_text(html_doc)
    print(OUT)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
