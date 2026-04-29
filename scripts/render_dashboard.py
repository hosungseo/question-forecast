#!/usr/bin/env python3
"""Render the GitHub Pages dashboard from enhanced radar JSON.

Design direction: warm editorial government briefing, inspired by Open Design's
artifact-first dashboard/deck surfaces without copying the product shell.
"""
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


def slug(x) -> str:
    return ''.join(ch if ch.isalnum() or ch in '_-' else '-' for ch in str(x or 'issue')).strip('-')


def first_question(packet: dict) -> str:
    qs = ((packet.get('question_synthesis') or {}).get('questions') or [])
    return qs[0].get('question', '') if qs else ''


def clean_title(text: str, limit: int = 92) -> str:
    text = ' '.join(str(text or '').replace('&quot;', '"').split())
    if len(text) <= limit:
        return text
    return text[:limit - 1].rstrip() + '…'


def recent_issue(packet: dict) -> dict:
    items = packet.get('items') or []
    lead = items[0] if items else {}
    title = clean_title(lead.get('title') or packet.get('issue_id'))
    desc = clean_title(lead.get('desc') or '', 150)
    signals = packet.get('signals') or []
    dates = sorted({it.get('pub_date') for it in items if it.get('pub_date')}, reverse=True)
    signal_text = ', '.join(signals[:5])
    summary = title
    if desc:
        summary = f"{title} — {desc}"
    return {
        'title': title,
        'summary': summary,
        'date': dates[0] if dates else '',
        'count': packet.get('count'),
        'signals': signal_text,
        'query': lead.get('query',''),
        'link': lead.get('link') or lead.get('originallink') or '',
    }


def trend_articles(packet: dict, limit: int = 3) -> list[dict]:
    """Pick diverse recent articles that explain the issue trend."""
    items = packet.get('items') or []
    out = []
    seen = set()
    for it in sorted(items, key=lambda x: (x.get('pub_date') or '', x.get('relevance_score') or 0), reverse=True):
        title = clean_title(it.get('title'), 86)
        if not title or title in seen:
            continue
        seen.add(title)
        hits = it.get('signal_hits') or []
        out.append({
            'date': it.get('pub_date',''),
            'title': title,
            'desc': clean_title(it.get('desc'), 120),
            'query': it.get('query',''),
            'score': it.get('relevance_score',''),
            'signals': ', '.join(hits[:4]),
            'link': it.get('link') or it.get('originallink') or '',
        })
        if len(out) >= limit:
            break
    return out


def evidence(packet: dict) -> str:
    cards = ((packet.get('statistical_evidence') or {}).get('answer_evidence_cards') or [])
    return ' · '.join(c.get('stat', '') for c in cards[:2]) or '답변 근거 통계 후보 없음'


def prep_items(packet: dict) -> list[str]:
    flow = packet.get('question_flow') or []
    minister = next((f for f in flow if f.get('stage') in ('장관 준비', 'minister_prep')), {})
    items = minister.get('items') or []
    if items:
        return items[:4]
    align = packet.get('ministry_work_alignment') or {}
    out = list(align.get('accountability_questions') or [])
    out.append('현황 수치와 즉시 조치/제도개선 구분')
    return out[:4]


def badge_for_delta(packet: dict) -> str:
    d = packet.get('daily_delta') or {}
    pc = d.get('priority_change')
    if d.get('status') == 'new_or_unseen':
        return '<span class="badge new">NEW</span>'
    if isinstance(pc, (int, float)) and pc >= 20:
        return '<span class="badge up">RISING</span>'
    if (d.get('move_change') or {}).get('from') != (d.get('move_change') or {}).get('to'):
        return '<span class="badge shift">FRAME SHIFT</span>'
    return '<span class="badge stable">STABLE</span>'


def issue_page_href(p: dict, rank: int) -> str:
    return f'issue-{rank}-{slug(p.get("issue_id"))}.html'


def case_line(packet: dict) -> str:
    cases = packet.get('similar_historical_cases') or []
    if not cases:
        return '과거 유사 질문 사례 없음'
    c = cases[0]
    return f"{c.get('meeting_date','')} · {c.get('question_type','')} · {c.get('excerpt','')[:110]}"


def render_trend_articles(p: dict) -> str:
    articles = trend_articles(p, 3)
    if not articles:
        return '<div class="trend-empty">트렌드 기사 없음</div>'
    rows = []
    for a in articles:
        href = esc(a.get('link'))
        title = esc(a.get('title'))
        title_html = f'<a href="{href}">{title}</a>' if href else title
        rows.append(f'''<li>
          <div class="trend-date">{esc(a.get('date'))}<span>{esc(a.get('score'))}점</span></div>
          <div class="trend-copy"><b>{title_html}</b><p>{esc(a.get('desc'))}</p><em>{esc(a.get('signals') or a.get('query'))}</em></div>
        </li>''')
    return '<ol class="trend-list">' + ''.join(rows) + '</ol>'


def render_packet(p: dict, rank: int) -> str:
    like = p.get('cabinet_question_likelihood') or {}
    align = p.get('ministry_work_alignment') or {}
    delta = p.get('daily_delta') or {}
    band = like.get('band', '-')
    score = like.get('score', '-')
    domains = ', '.join((align.get('function_domains') or [])[:3])
    q = first_question(p)
    diagnosis = (p.get('question_synthesis') or {}).get('diagnosis', '')
    issue = recent_issue(p)
    lead_article = issue['title']
    trend_html = render_trend_articles(p)
    prep = ''.join(f'<li>{esc(x)}</li>' for x in prep_items(p))
    search_blob = ' '.join([str(p.get('ministry')), str(p.get('issue_id')), q, domains, evidence(p), case_line(p), issue['summary'], issue['signals']])
    return f'''
    <article class="issue {esc(band)}" data-ministry="{esc(p.get('ministry'))}" data-score="{esc(score)}" data-search="{esc(search_blob).lower()}">
      <div class="rank"><span>{rank}</span></div>
      <div class="issue-main">
        <div class="meta"><span>{esc(p.get('ministry'))}</span><span>{esc(p.get('issue_id'))}</span><span>{esc(band)}</span>{badge_for_delta(p)}</div>
        <div class="issue-head">
          <div>
            <div class="recent-label">최근 이슈</div>
            <h3 class="issue-title">{esc(issue['title'])}</h3>
          </div>
          <div class="score"><b>{esc(score)}</b><small>질문 가능성</small></div>
        </div>
        <p class="issue-summary">{esc(issue['summary'])}</p>
        <div class="signal-strip"><span>{esc(issue['date'])}</span><span>기사 {esc(issue['count'])}건</span><span>{esc(issue['signals'])}</span></div>
        <section class="trend-box"><div class="trend-head"><b>최근 트렌드 기사</b><span>최신성·관련도 기준 대표 흐름</span></div>{trend_html}</section>
        <div class="forecast-note"><b>질문 프레임</b><span>{esc(diagnosis)}</span></div>
        <p class="first-q">{esc(q)}</p>
        <div class="brief-grid">
          <div><small>업무 연결</small><b>{esc(domains or '소관 업무 검토')}</b></div>
          <div><small>답변 근거</small><b>{esc(evidence(p))}</b></div>
          <div><small>유사사례</small><b>{esc(case_line(p))}</b></div>
        </div>
        <div class="actions"><a href="{issue_page_href(p, rank)}">상세 브리핑</a><a class="ghost" href="memo-{rank}-{slug(p.get('issue_id'))}.md">메모</a><button class="pick" data-title="{esc(p.get('ministry'))} · {esc(p.get('issue_id'))}" data-score="{esc(score)}" data-question="{esc(q)}">검토 바구니</button></div>
        <details>
          <summary>장관 답변 준비 펼치기</summary>
          <section class="qa answer-block"><div class="label">Minister answer prep</div><ul>{prep}</ul></section>
          <p class="delta">전일 대비: {esc(delta.get('interpretation','비교 기준 없음'))}</p>
          <p class="article-title">대표 기사: {esc(lead_article)}</p>
        </details>
      </div>
    </article>'''


def main() -> int:
    data = json.loads(SRC.read_text())
    packets = (data.get('packets') or [])[:5]
    generated = data.get('generated_at', '')
    high = sum(1 for p in packets if (p.get('cabinet_question_likelihood') or {}).get('band') == 'cabinet_high')
    avg = round(sum(float((p.get('cabinet_question_likelihood') or {}).get('score') or 0) for p in packets) / max(len(packets), 1), 1)
    issues_html = '\n'.join(render_packet(p, i + 1) for i, p in enumerate(packets))
    top = packets[0] if packets else {}
    top_q = first_question(top)
    top_issue = recent_issue(top) if top else {'title':'','summary':'','signals':'','date':'','count':'','link':''}
    focus_items = ''.join(
        f'<li><span>{i+1}</span><b>{esc(p.get("ministry"))}</b><em>{esc(p.get("issue_id"))}</em><strong>{esc((p.get("cabinet_question_likelihood") or {}).get("score"))}</strong></li>'
        for i, p in enumerate(packets[:5])
    )
    ministries = ['전체'] + sorted({p.get('ministry') for p in packets if p.get('ministry')})
    filters = ''.join(f'<button data-filter="{esc(m)}">{esc(m)}</button>' for m in ministries)

    html_doc = f'''<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Question Forecast</title>
  <style>
    :root {{ --paper:#f3efe7; --paper2:#fbf8f1; --ink:#17130d; --muted:#71685b; --line:#ded4c3; --deep:#1f2a24; --accent:#8f3f23; --blue:#234d8f; --green:#1f6b45; --amber:#9a5a12; --shadow:0 24px 80px rgba(52,39,22,.10); }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family: ui-serif, Georgia, "Times New Roman", serif; color:var(--ink); background:radial-gradient(circle at 18% 0%, #fffaf0 0, transparent 34%), linear-gradient(180deg,var(--paper2),var(--paper)); line-height:1.55; }}
    body::before {{ content:""; position:fixed; inset:0; pointer-events:none; opacity:.23; background-image:linear-gradient(rgba(23,19,13,.035) 1px, transparent 1px),linear-gradient(90deg,rgba(23,19,13,.025) 1px,transparent 1px); background-size:32px 32px; }}
    main {{ max-width:1180px; margin:0 auto; padding:38px 20px 88px; position:relative; }}
    .masthead {{ border:1px solid var(--line); background:rgba(251,248,241,.88); box-shadow:var(--shadow); border-radius:34px; overflow:hidden; }}
    .kicker {{ display:flex; justify-content:space-between; gap:16px; border-bottom:1px solid var(--line); padding:13px 18px; color:var(--muted); font:700 12px/1.2 ui-sans-serif,system-ui; letter-spacing:.12em; text-transform:uppercase; }}
    .hero {{ display:grid; grid-template-columns:1.1fr .9fr; min-height:390px; }}
    .hero-copy {{ padding:44px 46px 38px; }}
    h1 {{ margin:0; font-size:76px; line-height:.88; letter-spacing:-.065em; max-width:650px; }}
    .lead {{ margin:24px 0 0; max-width:620px; font-size:21px; color:#3d3329; }}
    .hero-panel {{ border-left:1px solid var(--line); padding:28px; background:linear-gradient(135deg,#1f2a24,#101713); color:#f7f0df; display:flex; flex-direction:column; justify-content:space-between; }}
    .hero-panel small {{ display:block; color:#ccbfa9; font:800 12px/1.2 ui-sans-serif,system-ui; text-transform:uppercase; letter-spacing:.1em; }}
    .hero-panel h2 {{ margin:12px 0 12px; font-size:28px; line-height:1.15; letter-spacing:-.03em; }}
    .hero-issue {{ padding:15px 16px; border:1px solid rgba(255,255,255,.18); border-radius:20px; background:rgba(255,255,255,.07); font-size:16px; color:#fff8e8; }}
    .hero-signals {{ margin:10px 0 16px; color:#ccbfa9; font:800 12px/1.45 ui-sans-serif,system-ui; }}
    .question-kicker {{ margin-top:4px; }}
    .hero-question {{ padding:16px 18px; border-left:4px solid #d29a62; background:rgba(255,255,255,.05); font-size:17px; }}
    .hero-stats {{ display:grid; grid-template-columns:repeat(3,1fr); gap:10px; margin-top:24px; }}
    .hero-stats div {{ border-top:1px solid rgba(255,255,255,.22); padding-top:12px; }}
    .hero-stats b {{ display:block; font:800 28px/1 ui-sans-serif,system-ui; }}
    .hero-stats span {{ color:#ccbfa9; font:700 11px/1.2 ui-sans-serif,system-ui; text-transform:uppercase; }}
    .links,.filters {{ display:flex; flex-wrap:wrap; gap:9px; }}
    .links {{ margin:22px 0 16px; }}
    a {{ color:var(--blue); text-decoration:none; font-weight:800; }}
    a:hover {{ text-decoration:underline; }}
    .links a,.filters button,.controls button,.controls input,.controls select,.api-actions button,.api-actions a {{ font:800 13px/1.2 ui-sans-serif,system-ui; border:1px solid var(--line); border-radius:999px; background:rgba(255,255,255,.68); color:#2f291f; padding:10px 13px; }}
    .filters {{ margin:0 0 20px; }}
    .filters button,.controls button,.api-actions button {{ cursor:pointer; }}
    .filters button.active {{ background:var(--deep); color:#fff7e8; border-color:var(--deep); }}
    .api-panel {{ display:grid; grid-template-columns:1fr auto; gap:18px; align-items:center; border:1px solid var(--line); border-radius:24px; background:rgba(255,255,255,.58); padding:16px 18px; margin:0 0 18px; }}
    .api-panel h2 {{ margin:0; font-size:18px; letter-spacing:-.02em; }}
    .api-panel p {{ margin:4px 0 0; color:var(--muted); font-size:14px; }}
    .api-status,.api-actions {{ display:flex; gap:8px; flex-wrap:wrap; justify-content:flex-end; }}
    .api-actions {{ margin-top:10px; justify-content:flex-start; }}
    .pill {{ border:1px solid var(--line); border-radius:999px; padding:7px 10px; font:800 12px/1.2 ui-sans-serif,system-ui; background:#fffaf0; color:var(--muted); }}
    .pill.ok {{ color:var(--green); background:#edf8ef; border-color:#bfdcc7; }} .pill.bad {{ color:#9d1c1c; background:#fff0ed; border-color:#f1beb6; }}
    .controls {{ display:grid; grid-template-columns:1fr 190px auto auto; gap:10px; margin:0 0 12px; }}
    .controls input,.controls select {{ border-radius:18px; font-weight:700; width:100%; }}
    .brief-layout {{ display:grid; grid-template-columns:310px 1fr; gap:18px; align-items:start; }}
    .brief-rail {{ position:sticky; top:16px; border:1px solid var(--line); border-radius:28px; background:rgba(255,255,255,.58); padding:20px; box-shadow:0 18px 50px rgba(52,39,22,.06); }}
    .brief-rail h2 {{ margin:0 0 6px; font-size:23px; letter-spacing:-.03em; }}
    .brief-rail p {{ margin:0 0 16px; color:var(--muted); }}
    .focus-list {{ list-style:none; padding:0; margin:0; display:grid; gap:10px; }}
    .focus-list li {{ display:grid; grid-template-columns:26px 1fr auto; gap:9px; align-items:center; border-top:1px solid var(--line); padding-top:10px; font-family:ui-sans-serif,system-ui; }}
    .focus-list span {{ display:grid; place-items:center; width:24px; height:24px; border-radius:50%; background:var(--deep); color:white; font-size:12px; font-weight:900; }}
    .focus-list b {{ font-size:13px; }} .focus-list em {{ grid-column:2; color:var(--muted); font-size:12px; font-style:normal; margin-top:-8px; }} .focus-list strong {{ grid-row:1/3; grid-column:3; color:var(--accent); }}
    .issues {{ display:grid; gap:14px; }}
    .issue {{ display:grid; grid-template-columns:58px 1fr; gap:16px; border:1px solid var(--line); border-radius:28px; background:rgba(255,255,255,.74); padding:18px; box-shadow:0 18px 56px rgba(52,39,22,.07); }}
    .issue:hover {{ transform:translateY(-1px); box-shadow:0 26px 70px rgba(52,39,22,.10); }}
    .rank span {{ display:grid; place-items:center; width:48px; height:60px; border-radius:18px; background:var(--ink); color:#fff7e8; font:900 20px/1 ui-sans-serif,system-ui; }}
    .meta {{ display:flex; gap:7px; flex-wrap:wrap; margin-bottom:10px; }}
    .meta span,.badge {{ font:900 11px/1.2 ui-sans-serif,system-ui; color:#4b4033; background:#f6efe2; border:1px solid var(--line); padding:5px 8px; border-radius:999px; letter-spacing:.03em; }}
    .cabinet_high .meta span:nth-child(3) {{ color:var(--green); background:#edf8ef; border-color:#bfdcc7; }} .cabinet_review .meta span:nth-child(3) {{ color:var(--amber); background:#fff5df; border-color:#ead29d; }}
    .badge.new {{ color:#234d8f; background:#edf3ff; }} .badge.up {{ color:#9d1c1c; background:#fff0ed; }} .badge.shift {{ color:#8f3f23; background:#fff2e8; }}
    .issue-head {{ display:grid; grid-template-columns:1fr 94px; gap:18px; }}
    .recent-label {{ font:900 11px/1.2 ui-sans-serif,system-ui; color:var(--accent); letter-spacing:.09em; text-transform:uppercase; margin-bottom:5px; }}
    h3 {{ margin:0; font-size:22px; line-height:1.28; letter-spacing:-.025em; }}
    .issue-title {{ font-size:25px; }}
    .issue-summary {{ margin:10px 0 10px; color:#3d3329; font-size:16px; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }}
    .signal-strip {{ display:flex; flex-wrap:wrap; gap:7px; margin:0 0 12px; }}
    .signal-strip span {{ font:850 12px/1.2 ui-sans-serif,system-ui; color:#5d5144; background:#f6efe2; border:1px solid var(--line); border-radius:999px; padding:7px 9px; }}
    .trend-box {{ border:1px solid var(--line); border-radius:22px; background:#fffaf0; padding:13px 14px; margin:12px 0; }}
    .trend-head {{ display:flex; justify-content:space-between; gap:10px; align-items:baseline; margin-bottom:8px; }}
    .trend-head b {{ font:900 13px/1.2 ui-sans-serif,system-ui; color:var(--accent); letter-spacing:.05em; text-transform:uppercase; }}
    .trend-head span {{ color:var(--muted); font:800 12px/1.2 ui-sans-serif,system-ui; }}
    .trend-list {{ list-style:none; margin:0; padding:0; display:grid; gap:9px; }}
    .trend-list li {{ display:grid; grid-template-columns:92px 1fr; gap:10px; padding-top:9px; border-top:1px solid #eadfca; }}
    .trend-list li:first-child {{ border-top:0; padding-top:0; }}
    .trend-date {{ color:var(--muted); font:900 12px/1.25 ui-sans-serif,system-ui; }}
    .trend-date span {{ display:block; color:var(--blue); margin-top:4px; }}
    .trend-copy b {{ display:block; font-size:15px; line-height:1.35; }}
    .trend-copy p {{ margin:4px 0; color:#4b4033; font-size:13px; line-height:1.45; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }}
    .trend-copy em {{ color:var(--muted); font:800 11px/1.2 ui-sans-serif,system-ui; font-style:normal; }}
    .trend-empty {{ color:var(--muted); font-size:13px; }}
    .forecast-note {{ display:grid; grid-template-columns:92px 1fr; gap:10px; align-items:start; border-top:1px solid var(--line); border-bottom:1px solid var(--line); padding:10px 0; margin:12px 0; }}
    .forecast-note b {{ font:900 12px/1.4 ui-sans-serif,system-ui; color:var(--blue); }}
    .forecast-note span {{ color:var(--muted); font-size:14px; }}
    .score {{ text-align:right; border-left:1px solid var(--line); padding-left:14px; font-family:ui-sans-serif,system-ui; }}
    .score b {{ display:block; font-size:32px; letter-spacing:-.05em; }} .score small {{ color:var(--muted); font-weight:900; font-size:11px; text-transform:uppercase; }}
    .first-q {{ margin:12px 0 14px; padding-left:14px; border-left:4px solid var(--accent); font-size:18px; font-weight:700; color:#221b13; }}
    .brief-grid {{ display:grid; grid-template-columns:1fr 1fr 1.2fr; gap:10px; }}
    .brief-grid div {{ border:1px solid var(--line); border-radius:18px; background:#fbf8f1; padding:12px; min-width:0; }}
    .brief-grid small {{ display:block; font:900 11px/1.2 ui-sans-serif,system-ui; color:var(--muted); text-transform:uppercase; letter-spacing:.06em; margin-bottom:6px; }}
    .brief-grid b {{ display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; font-size:14px; line-height:1.45; }}
    .actions {{ margin:13px 0 4px; display:flex; flex-wrap:wrap; gap:7px; }}
    .actions a,.actions button {{ border:1px solid var(--ink); background:var(--ink); color:#fff7e8; border-radius:999px; padding:9px 12px; font:900 13px/1.2 ui-sans-serif,system-ui; cursor:pointer; }}
    .actions .ghost,.actions .pick {{ background:transparent; color:var(--ink); border-color:var(--line); }}
    details {{ margin-top:12px; }} summary {{ cursor:pointer; color:var(--blue); font:900 14px/1.2 ui-sans-serif,system-ui; list-style:none; }} summary::-webkit-details-marker {{ display:none; }}
    .qa {{ border-radius:20px; padding:15px 17px; margin:12px 0; background:#fff6df; border:1px solid #ead29d; }} .label {{ font:900 11px/1.2 ui-sans-serif,system-ui; color:#8f3f23; letter-spacing:.08em; text-transform:uppercase; margin-bottom:8px; }}
    .qa ul {{ margin:0; padding-left:18px; }} .qa li {{ margin:4px 0; }} .delta,.article-title,.note {{ color:var(--muted); font-size:14px; }}
    .tray {{ position:fixed; right:18px; bottom:18px; width:min(420px,calc(100vw - 36px)); background:var(--deep); color:#fff7e8; border-radius:24px; padding:16px; box-shadow:0 24px 80px rgba(15,23,42,.28); z-index:20; display:none; }} .tray.open {{ display:block; }} .tray h2 {{ font-size:16px; margin:0 0 8px; }} .tray li {{ margin:8px 0; color:#d8cfbd; }} .tray-actions {{ display:flex; gap:8px; margin-top:12px; }} .tray button {{ border:1px solid rgba(255,255,255,.2); background:rgba(255,255,255,.08); color:white; border-radius:999px; padding:8px 11px; cursor:pointer; font-weight:800; }}
    .note {{ border-top:1px solid var(--line); margin-top:30px; padding-top:20px; }}
    @media (max-width:880px) {{ .hero,.brief-layout,.api-panel,.controls {{ grid-template-columns:1fr; }} .hero-panel {{ border-left:0; border-top:1px solid var(--line); }} h1 {{ font-size:54px; }} .brief-rail {{ position:static; }} .issue,.issue-head,.brief-grid {{ grid-template-columns:1fr; }} .score {{ text-align:left; border-left:0; padding-left:0; }} }}
  </style>
</head>
<body>
<main>
  <section class="masthead">
    <div class="kicker"><span>Cabinet intelligence prototype</span><span>Generated · {esc(generated)}</span></div>
    <div class="hero">
      <div class="hero-copy"><h1>Question Forecast</h1><p class="lead">매일 보도를 부처 업무, 과거 국무회의 질문 패턴, 답변 근거 통계에 연결해 장관용 예상 질의 브리핑을 만듭니다.</p></div>
      <aside class="hero-panel"><div><small>오늘의 최근 이슈</small><h2>{esc(top_issue['title'])}</h2><div class="hero-issue">{esc(top_issue['summary'])}</div><div class="hero-signals">{esc(top_issue['date'])} · 기사 {esc(top_issue['count'])}건 · {esc(top_issue['signals'])}</div><small class="question-kicker">Today’s first question</small><div class="hero-question">{esc(top_q)}</div></div><div class="hero-stats"><div><b>{len(packets)}</b><span>packets</span></div><div><b>{high}</b><span>high</span></div><div><b>{avg}</b><span>avg score</span></div></div></aside>
    </div>
  </section>
  <nav class="links"><a href="daily-digest.md">Daily digest</a><a href="briefing.md">Full briefing</a><a href="radar.md">Radar markdown</a><a href="gold-v1.md">Gold v1</a><a href="threshold.md">Calibration</a><a href="https://github.com/hosungseo/question-forecast">GitHub</a></nav>
  <section class="api-panel" aria-label="데이터 상태"><div><h2>데이터 상태</h2><p id="apiSummary">Vercel API에서 최신 레이더를 확인합니다.</p><div class="api-actions"><button id="refreshApi">API 재확인</button><button id="copyApi">API 링크 복사</button><a href="/api/latest">/api/latest</a><a href="/api/issues">/api/issues</a></div></div><div class="api-status"><span class="pill" id="apiLive">확인 전</span><span class="pill" id="apiGenerated">generated: -</span><span class="pill" id="apiCount">packets: -</span></div></section>
  <section class="controls"><input id="search" type="search" placeholder="이슈, 부처, 질문, 답변근거 검색" /><select id="sort"><option value="rank">기본 순위</option><option value="score">질문 가능성 높은 순</option></select><button id="expand">모두 펼치기</button><button id="collapse">모두 접기</button></section>
  <div class="filters">{filters}</div>
  <section class="brief-layout"><aside class="brief-rail"><h2>오늘 먼저 볼 이슈</h2><p>질문 가능성이 높거나 장관 답변 준비가 급한 순서입니다.</p><ul class="focus-list">{focus_items}</ul></aside><section class="issues" id="issues">{issues_html}</section></section>
  <p class="note">Note: This is a decision-support radar, not a claim about actual presidential intent. Statistics are answer evidence, not literal presidential questions.</p>
</main>
<aside class="tray" id="tray"><h2>검토 바구니</h2><ul id="trayList"></ul><div class="tray-actions"><button id="copyTray">복사</button><button id="clearTray">비우기</button></div></aside>
<script>
  const buttons = document.querySelectorAll('.filters button');
  const cards = Array.from(document.querySelectorAll('.issue'));
  const issues = document.getElementById('issues');
  const search = document.getElementById('search');
  const sort = document.getElementById('sort');
  let activeFilter = '전체';
  async function checkApi() {{
    const live = document.getElementById('apiLive'), generated = document.getElementById('apiGenerated'), count = document.getElementById('apiCount'), summary = document.getElementById('apiSummary');
    live.textContent = '확인 중'; live.className = 'pill';
    try {{
      const res = await fetch('/api/latest', {{ cache: 'no-store' }});
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const data = await res.json(); const packets = data.packets || [];
      live.textContent = 'API 정상'; live.className = 'pill ok'; generated.textContent = 'generated: ' + (data.generated_at || '-'); count.textContent = 'packets: ' + packets.length;
      summary.textContent = '최신 JSON API가 응답했습니다. 화면 산출물과 API 산출물을 함께 사용할 수 있습니다.';
    }} catch (err) {{ live.textContent = 'API 점검 필요'; live.className = 'pill bad'; summary.textContent = 'API 확인에 실패했습니다. 정적 대시보드는 계속 볼 수 있습니다.'; }}
  }}
  function apply() {{
    const q = (search.value || '').trim().toLowerCase();
    cards.forEach(card => {{
      const okFilter = activeFilter === '전체' || card.dataset.ministry === activeFilter;
      const okSearch = !q || (card.dataset.search || '').includes(q);
      card.style.display = (okFilter && okSearch) ? 'grid' : 'none';
    }});
    const ordered = cards.slice().sort((a,b) => sort.value === 'score' ? (Number(b.dataset.score||0)-Number(a.dataset.score||0)) : 0);
    ordered.forEach(card => issues.appendChild(card));
  }}
  buttons[0]?.classList.add('active');
  buttons.forEach(btn => btn.addEventListener('click', () => {{ buttons.forEach(b => b.classList.remove('active')); btn.classList.add('active'); activeFilter = btn.dataset.filter; apply(); }}));
  search.addEventListener('input', apply); sort.addEventListener('change', apply);
  document.getElementById('refreshApi').addEventListener('click', checkApi);
  document.getElementById('copyApi').addEventListener('click', async () => {{ const text = `${{location.origin}}/api/latest\n${{location.origin}}/api/issues`; try {{ await navigator.clipboard.writeText(text); document.getElementById('copyApi').textContent = '복사됨'; setTimeout(()=>document.getElementById('copyApi').textContent='API 링크 복사',1200); }} catch(e) {{ alert(text); }} }});
  checkApi();
  document.getElementById('expand').addEventListener('click', () => document.querySelectorAll('details').forEach(d => d.open = true));
  document.getElementById('collapse').addEventListener('click', () => document.querySelectorAll('details').forEach(d => d.open = false));
  const tray = document.getElementById('tray'), trayList = document.getElementById('trayList'), picks = [];
  function renderTray() {{ tray.classList.toggle('open', picks.length > 0); trayList.innerHTML = picks.map(p => `<li><b>${{p.title}}</b> (${{p.score}})<br>${{p.question}}</li>`).join(''); }}
  document.querySelectorAll('.pick').forEach(btn => btn.addEventListener('click', () => {{ const item = {{ title: btn.dataset.title, score: btn.dataset.score, question: btn.dataset.question }}; if (!picks.some(p => p.title === item.title)) picks.push(item); renderTray(); }}));
  document.getElementById('clearTray').addEventListener('click', () => {{ picks.length = 0; renderTray(); }});
  document.getElementById('copyTray').addEventListener('click', async () => {{ const text = picks.map((p,i) => `${{i+1}}. ${{p.title}} (${{p.score}})\n- ${{p.question}}`).join('\n\n'); try {{ await navigator.clipboard.writeText(text); document.getElementById('copyTray').textContent = '복사됨'; setTimeout(()=>document.getElementById('copyTray').textContent='복사',1200); }} catch(e) {{ alert(text); }} }});
  window.addEventListener('keydown', e => {{ if (e.key === '/' && document.activeElement !== search) {{ e.preventDefault(); search.focus(); }} if (e.key.toLowerCase() === 'e') document.getElementById('expand').click(); if (e.key.toLowerCase() === 'c') document.getElementById('collapse').click(); }});
</script>
</body>
</html>'''
    OUT.write_text(html_doc)
    print(OUT)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
