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


def prep_items(packet: dict) -> list[str]:
    flow = packet.get('question_flow') or []
    minister = next((f for f in flow if f.get('stage') in ('장관 준비', 'minister_prep')), {})
    items = minister.get('items') or []
    if items:
        return items[:4]
    align = packet.get('ministry_work_alignment') or {}
    out = []
    out.extend(align.get('accountability_questions') or [])
    out.append('현황 수치와 즉시 조치/제도개선 구분')
    return out[:4]


def badge_for_delta(packet: dict) -> str:
    d = packet.get('daily_delta') or {}
    status = d.get('status')
    pc = d.get('priority_change')
    if status == 'new_or_unseen':
        return '<span class="badge new">NEW</span>'
    if isinstance(pc, (int, float)) and pc >= 20:
        return '<span class="badge up">RISING</span>'
    if (d.get('move_change') or {}).get('from') != (d.get('move_change') or {}).get('to'):
        return '<span class="badge shift">FRAME SHIFT</span>'
    return '<span class="badge stable">STABLE</span>'


def issue_page_href(p: dict, rank: int) -> str:
    issue = ''.join(ch if ch.isalnum() or ch in '_-' else '-' for ch in str(p.get('issue_id') or 'issue')).strip('-')
    return f'issue-{rank}-{issue}.html'


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
    prep = ''.join(f'<li>{esc(x)}</li>' for x in prep_items(p))
    search_blob = ' '.join([str(p.get('ministry')), str(p.get('issue_id')), q, domains, evidence(p), lead_article])
    return f'''
    <article class="issue {esc(band)}" data-ministry="{esc(p.get('ministry'))}" data-score="{esc(score)}" data-search="{esc(search_blob).lower()}">
      <div class="rank">{rank}</div>
      <div class="issue-main">
        <div class="meta"><span>{esc(p.get('ministry'))}</span><span>{esc(p.get('issue_id'))}</span><span>{esc(band)}</span>{badge_for_delta(p)}</div>
        <div class="issue-head">
          <div>
            <h3>{esc((p.get('question_synthesis') or {}).get('diagnosis',''))}</h3>
            <p class="one-line">{esc(q)}</p>
          </div>
          <div class="score"><b>{esc(score)}</b><small>question likelihood</small></div>
        </div>
        <div class="quick-row">
          <span>기사 {esc(p.get('count'))}건</span>
          <span>{esc(domains)}</span>
          <span>{esc(delta.get('interpretation','전일 비교 없음'))}</span>
        </div>
        <div class="actions"><a href="{issue_page_href(p, rank)}">상세 브리핑 열기 →</a><a class="ghost" href="memo-{rank}-{str(p.get('issue_id') or 'issue')}.md">메모</a><button class="pick" data-title="{esc(p.get('ministry'))} · {esc(p.get('issue_id'))}" data-score="{esc(score)}" data-question="{esc(q)}">검토 바구니</button></div>
        <details>
          <summary>질문·답변 준비 펼치기</summary>
          <section class="qa question-block">
            <div class="label">대통령 예상 질문</div>
            <p>{esc(q)}</p>
          </section>
          <section class="qa answer-block">
            <div class="label">장관 답변 준비</div>
            <ul>{prep}</ul>
          </section>
          <div class="facts">
            <span>업무: {esc(domains)}</span>
            <span>답변근거: {esc(evidence(p))}</span>
          </div>
          <p class="article-title">대표 기사: {esc(lead_article)}</p>
        </details>
      </div>
    </article>'''


def main() -> int:
    data = json.loads(SRC.read_text())
    packets = (data.get('packets') or [])[:5]
    generated = data.get('generated_at','')
    high = sum(1 for p in packets if (p.get('cabinet_question_likelihood') or {}).get('band') == 'cabinet_high')
    avg = round(sum(float((p.get('cabinet_question_likelihood') or {}).get('score') or 0) for p in packets) / max(len(packets),1), 1)
    issues_html = '\n'.join(render_packet(p, i+1) for i,p in enumerate(packets))
    high_packets = [p for p in packets if (p.get('cabinet_question_likelihood') or {}).get('band') == 'cabinet_high'][:2]
    if not high_packets:
        high_packets = packets[:2]
    today_focus = ''.join(
        f'<li><b>{esc(p.get("ministry"))}</b> · {esc(p.get("issue_id"))} <span>{esc((p.get("cabinet_question_likelihood") or {}).get("score"))}</span></li>'
        for p in high_packets
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
    :root {{ --ink:#111827; --muted:#6b7280; --soft:#f6f7f9; --line:#e5e7eb; --card:#fff; --blue:#1d4ed8; --green:#047857; --amber:#b45309; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; color:var(--ink); background:#f8fafc; line-height:1.55; }}
    main {{ max-width:1120px; margin:0 auto; padding:44px 20px 80px; }}
    .top {{ display:grid; grid-template-columns:1.3fr .7fr; gap:28px; align-items:end; border-bottom:1px solid var(--line); padding-bottom:28px; }}
    .focus {{ background:#0f172a; color:white; border-radius:28px; padding:24px; margin:26px 0 18px; display:grid; grid-template-columns:.8fr 1.2fr; gap:20px; }}
    .focus h2 {{ margin:0; font-size:23px; letter-spacing:-.03em; }}
    .focus p {{ margin:8px 0 0; color:#cbd5e1; }}
    .focus ul {{ list-style:none; padding:0; margin:0; display:grid; gap:10px; }}
    .focus li {{ background:rgba(255,255,255,.08); border:1px solid rgba(255,255,255,.12); padding:12px 14px; border-radius:16px; }}
    .focus span {{ float:right; color:#93c5fd; font-weight:800; }}
    .controls {{ display:grid; grid-template-columns:1fr 190px auto auto; gap:10px; margin:0 0 14px; }}
    .controls input,.controls select,.controls button {{ border:1px solid var(--line); border-radius:14px; padding:11px 12px; background:white; font:inherit; font-weight:650; }}
    .controls button {{ cursor:pointer; color:#111827; }}
    .filters {{ display:flex; gap:8px; flex-wrap:wrap; margin:0 0 24px; }}
    .filters button {{ border:1px solid var(--line); background:white; border-radius:999px; padding:9px 12px; font-weight:700; color:#374151; cursor:pointer; }}
    .filters button.active {{ background:#111827; color:white; border-color:#111827; }}
    .eyebrow {{ color:var(--blue); font-weight:800; letter-spacing:.08em; text-transform:uppercase; font-size:12px; }}
    h1 {{ font-size:54px; letter-spacing:-.05em; line-height:.98; margin:10px 0 16px; }}
    .lead {{ font-size:19px; color:#374151; max-width:760px; margin:0; }}
    .stamp {{ text-align:right; color:var(--muted); font-size:14px; }}
    .stats {{ display:flex; gap:10px; justify-content:flex-end; margin-top:12px; flex-wrap:wrap; }}
    .stat {{ background:#fff; border:1px solid var(--line); border-radius:999px; padding:7px 11px; font-size:13px; }}
    .links {{ display:flex; gap:12px; flex-wrap:wrap; margin:22px 0 18px; }}
    .api-panel {{ display:grid; grid-template-columns:1fr auto; gap:14px; align-items:center; background:white; border:1px solid var(--line); border-radius:22px; padding:16px 18px; margin:0 0 28px; box-shadow:0 10px 30px rgba(15,23,42,.035); }}
    .api-panel h2 {{ margin:0; font-size:17px; letter-spacing:-.02em; }}
    .api-panel p {{ margin:4px 0 0; color:var(--muted); font-size:14px; }}
    .api-status {{ display:flex; gap:8px; flex-wrap:wrap; justify-content:flex-end; }}
    .pill {{ border:1px solid var(--line); border-radius:999px; padding:7px 10px; font-size:12px; font-weight:800; background:#f8fafc; color:#475569; }}
    .pill.ok {{ color:#047857; background:#ecfdf5; border-color:#bbf7d0; }}
    .pill.bad {{ color:#b91c1c; background:#fef2f2; border-color:#fecaca; }}
    .api-actions {{ margin-top:10px; display:flex; gap:8px; flex-wrap:wrap; }}
    .api-actions button,.api-actions a {{ border:1px solid var(--line); background:white; border-radius:999px; padding:8px 11px; font-size:13px; font-weight:800; color:#111827; cursor:pointer; }}
    .api-actions button:hover,.api-actions a:hover {{ background:#f8fafc; text-decoration:none; }}
    a {{ color:var(--blue); text-decoration:none; font-weight:700; }}
    a:hover {{ text-decoration:underline; }}
    .links a {{ background:white; border:1px solid var(--line); padding:10px 13px; border-radius:999px; }}
    .issues {{ display:grid; gap:14px; }}
    .issue {{ display:grid; grid-template-columns:54px 1fr; gap:16px; background:var(--card); border:1px solid var(--line); border-radius:24px; padding:18px 20px; box-shadow:0 10px 30px rgba(15,23,42,.04); }}
    .issue:hover {{ border-color:#cbd5e1; box-shadow:0 18px 42px rgba(15,23,42,.07); }}
    .issue-head {{ display:grid; grid-template-columns:1fr 108px; gap:18px; align-items:start; }}
    .score {{ text-align:right; border-left:1px solid var(--line); padding-left:16px; }}
    .score b {{ display:block; font-size:30px; letter-spacing:-.04em; }}
    .score small {{ color:var(--muted); font-size:11px; text-transform:uppercase; letter-spacing:.05em; }}
    .badge {{ font-size:11px!important; font-weight:900; letter-spacing:.04em; }}
    .badge.new {{ color:#1d4ed8!important; background:#eff6ff!important; border-color:#bfdbfe!important; }}
    .badge.up {{ color:#b91c1c!important; background:#fef2f2!important; border-color:#fecaca!important; }}
    .badge.shift {{ color:#7c2d12!important; background:#fff7ed!important; border-color:#fed7aa!important; }}
    .badge.stable {{ color:#475569!important; background:#f8fafc!important; }}
    .rank {{ width:42px; height:42px; border-radius:14px; display:grid; place-items:center; background:#111827; color:white; font-weight:800; }}
    .meta {{ display:flex; gap:8px; flex-wrap:wrap; margin-bottom:8px; }}
    .meta span {{ font-size:12px; color:#374151; background:#f3f4f6; border:1px solid #e5e7eb; padding:4px 8px; border-radius:999px; }}
    .cabinet_high .meta span:last-child {{ color:var(--green); background:#ecfdf5; border-color:#bbf7d0; }}
    .cabinet_review .meta span:last-child {{ color:var(--amber); background:#fffbeb; border-color:#fde68a; }}
    h3 {{ font-size:20px; line-height:1.35; letter-spacing:-.02em; margin:0 0 8px; }}
    .one-line {{ margin:0; color:#111827; font-size:16px; font-weight:650; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }}
    .quick-row {{ display:grid; grid-template-columns:90px 1fr 1fr; gap:8px; margin:13px 0 6px; }}
    .quick-row span {{ background:#f8fafc; border:1px solid var(--line); border-radius:12px; padding:8px 10px; color:#475569; font-size:13px; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
    .actions {{ margin:10px 0 4px; }}
    .actions a,.actions button {{ display:inline-block; background:#111827; color:white; border-radius:999px; padding:8px 12px; font-size:13px; margin-right:6px; border:0; font-weight:800; cursor:pointer; }}
    .actions a.ghost,.actions button.pick {{ background:white; color:#111827; border:1px solid var(--line); }}
    .actions a:hover,.actions button:hover {{ text-decoration:none; background:#1f2937; color:white; }}
    .actions a.ghost:hover,.actions button.pick:hover {{ background:#f8fafc; color:#111827; }}
    .tray {{ position:fixed; right:18px; bottom:18px; width:min(420px,calc(100vw - 36px)); background:#111827; color:white; border-radius:24px; padding:16px; box-shadow:0 24px 80px rgba(15,23,42,.28); z-index:20; display:none; }}
    .tray.open {{ display:block; }}
    .tray h2 {{ font-size:16px; margin:0 0 8px; }}
    .tray ul {{ margin:0; padding-left:18px; max-height:220px; overflow:auto; }}
    .tray li {{ margin:8px 0; color:#dbeafe; }}
    .tray-actions {{ display:flex; gap:8px; margin-top:12px; }}
    .tray button {{ border:1px solid rgba(255,255,255,.2); background:rgba(255,255,255,.08); color:white; border-radius:999px; padding:8px 11px; cursor:pointer; font-weight:800; }}
    details {{ margin-top:10px; }}
    summary {{ cursor:pointer; color:#1d4ed8; font-weight:800; font-size:14px; list-style:none; }}
    summary::-webkit-details-marker {{ display:none; }}
    summary::after {{ content:'+'; display:inline-grid; place-items:center; margin-left:8px; width:20px; height:20px; border-radius:999px; background:#eff6ff; }}
    details[open] summary::after {{ content:'−'; }}
    .qa {{ border-radius:18px; padding:15px 16px; margin:12px 0; }}
    .qa .label {{ font-size:12px; font-weight:900; letter-spacing:.06em; text-transform:uppercase; margin-bottom:8px; }}
    .question-block {{ background:#f8fafc; border:1px solid #e2e8f0; }}
    .question-block p {{ font-size:18px; margin:0; color:#111827; font-weight:650; letter-spacing:-.01em; }}
    .answer-block {{ background:#fffbeb; border:1px solid #fde68a; }}
    .answer-block ul {{ margin:0; padding-left:18px; color:#374151; }}
    .answer-block li {{ margin:4px 0; }}
    .facts {{ display:flex; gap:8px; flex-wrap:wrap; margin-bottom:10px; }}
    .facts span {{ font-size:13px; background:#f8fafc; border:1px solid var(--line); padding:6px 9px; border-radius:10px; color:#374151; }}
    .evidence, .delta, .article-title {{ margin:7px 0 0; color:var(--muted); font-size:14px; }}
    .note {{ margin-top:34px; color:var(--muted); font-size:14px; border-top:1px solid var(--line); padding-top:22px; }}
    @media (max-width:760px) {{ .top,.focus,.controls,.api-panel {{ grid-template-columns:1fr; }} .api-status {{ justify-content:flex-start; }} .stamp {{ text-align:left; }} .stats {{ justify-content:flex-start; }} h1 {{ font-size:42px; }} .issue,.issue-head,.quick-row {{ grid-template-columns:1fr; }} .score {{ text-align:left; border-left:0; padding-left:0; }} }}
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
  <section class="focus">
    <div><h2>오늘 먼저 볼 이슈</h2><p>질문 가능성이 높거나 장관 답변 준비가 급한 항목입니다.</p></div>
    <ul>{today_focus}</ul>
  </section>
  <nav class="links">
    <a href="daily-digest.md">Daily digest</a>
    <a href="briefing.md">Full briefing</a>
    <a href="radar.md">Radar markdown</a>
    <a href="gold-v1.md">Gold v1</a>
    <a href="threshold.md">Calibration</a>
    <a href="https://github.com/hosungseo/question-forecast">GitHub</a>
  </nav>
  <section class="api-panel" aria-label="데이터 상태">
    <div>
      <h2>데이터 상태</h2>
      <p id="apiSummary">Vercel API에서 최신 레이더를 확인합니다.</p>
      <div class="api-actions"><button id="refreshApi">API 재확인</button><button id="copyApi">API 링크 복사</button><a href="/api/latest">/api/latest</a><a href="/api/issues">/api/issues</a></div>
    </div>
    <div class="api-status"><span class="pill" id="apiLive">확인 전</span><span class="pill" id="apiGenerated">generated: -</span><span class="pill" id="apiCount">packets: -</span></div>
  </section>
  <section class="controls">
    <input id="search" type="search" placeholder="이슈, 부처, 질문, 답변근거 검색" />
    <select id="sort"><option value="rank">기본 순위</option><option value="score">질문 가능성 높은 순</option></select>
    <button id="expand">모두 펼치기</button>
    <button id="collapse">모두 접기</button>
  </section>
  <div class="filters">{filters}</div>
  <section class="issues" id="issues">
    {issues_html}
  </section>
  <p class="note">Note: This is a decision-support radar, not a claim about actual presidential intent. Statistics are answer evidence, not literal presidential questions.</p>
</main>
<aside class="tray" id="tray">
  <h2>검토 바구니</h2>
  <ul id="trayList"></ul>
  <div class="tray-actions"><button id="copyTray">복사</button><button id="clearTray">비우기</button></div>
</aside>
<script>
  const buttons = document.querySelectorAll('.filters button');
  const cards = Array.from(document.querySelectorAll('.issue'));
  const issues = document.getElementById('issues');
  const search = document.getElementById('search');
  const sort = document.getElementById('sort');
  let activeFilter = '전체';
  async function checkApi() {{
    const live = document.getElementById('apiLive');
    const generated = document.getElementById('apiGenerated');
    const count = document.getElementById('apiCount');
    const summary = document.getElementById('apiSummary');
    live.textContent = '확인 중'; live.className = 'pill';
    try {{
      const res = await fetch('/api/latest', {{ cache: 'no-store' }});
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const data = await res.json();
      const packets = data.packets || [];
      live.textContent = 'API 정상'; live.className = 'pill ok';
      generated.textContent = 'generated: ' + (data.generated_at || '-');
      count.textContent = 'packets: ' + packets.length;
      summary.textContent = '최신 JSON API가 응답했습니다. 화면 산출물과 API 산출물을 함께 사용할 수 있습니다.';
    }} catch (err) {{
      live.textContent = 'API 점검 필요'; live.className = 'pill bad';
      summary.textContent = 'API 확인에 실패했습니다. 정적 대시보드는 계속 볼 수 있습니다.';
    }}
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
  buttons.forEach(btn => btn.addEventListener('click', () => {{
    buttons.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    activeFilter = btn.dataset.filter;
    apply();
  }}));
  search.addEventListener('input', apply);
  sort.addEventListener('change', apply);
  document.getElementById('refreshApi').addEventListener('click', checkApi);
  document.getElementById('copyApi').addEventListener('click', async () => {{
    const text = `${{location.origin}}/api/latest\n${{location.origin}}/api/issues`;
    try {{ await navigator.clipboard.writeText(text); document.getElementById('copyApi').textContent = '복사됨'; setTimeout(()=>document.getElementById('copyApi').textContent='API 링크 복사',1200); }} catch(e) {{ alert(text); }}
  }});
  checkApi();
  document.getElementById('expand').addEventListener('click', () => document.querySelectorAll('details').forEach(d => d.open = true));
  document.getElementById('collapse').addEventListener('click', () => document.querySelectorAll('details').forEach(d => d.open = false));
  const tray = document.getElementById('tray');
  const trayList = document.getElementById('trayList');
  const picks = [];
  function renderTray() {{
    tray.classList.toggle('open', picks.length > 0);
    trayList.innerHTML = picks.map(p => `<li><b>${{p.title}}</b> (${{p.score}})<br>${{p.question}}</li>`).join('');
  }}
  document.querySelectorAll('.pick').forEach(btn => btn.addEventListener('click', () => {{
    const item = {{ title: btn.dataset.title, score: btn.dataset.score, question: btn.dataset.question }};
    if (!picks.some(p => p.title === item.title)) picks.push(item);
    renderTray();
  }}));
  document.getElementById('clearTray').addEventListener('click', () => {{ picks.length = 0; renderTray(); }});
  document.getElementById('copyTray').addEventListener('click', async () => {{
    const text = picks.map((p,i) => `${{i+1}}. ${{p.title}} (${{p.score}})\n- ${{p.question}}`).join('\n\n');
    try {{ await navigator.clipboard.writeText(text); document.getElementById('copyTray').textContent = '복사됨'; setTimeout(()=>document.getElementById('copyTray').textContent='복사',1200); }} catch(e) {{ alert(text); }}
  }});
  window.addEventListener('keydown', e => {{
    if (e.key === '/' && document.activeElement !== search) {{ e.preventDefault(); search.focus(); }}
    if (e.key.toLowerCase() === 'e') document.getElementById('expand').click();
    if (e.key.toLowerCase() === 'c') document.getElementById('collapse').click();
  }});
</script>
</body>
</html>'''
    OUT.write_text(html_doc)
    print(OUT)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
