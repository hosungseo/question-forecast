#!/usr/bin/env python3
from __future__ import annotations
import json, sqlite3
from pathlib import Path
DB=Path('/Users/seohoseong/Documents/codex/cabinet-question-radar/data/cabinet_question_radar.sqlite')
OUT=Path('/Users/seohoseong/Documents/codex/cabinet-question-radar/data/match_report.md')
con=sqlite3.connect(DB); con.row_factory=sqlite3.Row
lines=['# Cabinet Question Radar — high-recall match report','']
counts=con.execute('select count(*) c from cluster_question_links').fetchone()['c']
lines.append(f'- cluster→question 후보 링크: **{counts}건**')
lines.append('')
lines += ['## 회의별 링크 수','','| 회의일 | 회차 | 링크수 | 평균점수 |','|---|---:|---:|---:|']
for r in con.execute('''select meeting_date,meeting_no,count(*) links,round(avg(score),3) avg_score from v_cluster_question_links group by meeting_date,meeting_no order by meeting_date desc'''):
    lines.append(f"| {r['meeting_date']} | {r['meeting_no']} | {r['links']} | {r['avg_score']} |")
lines += ['','## 부처별 링크 수','','| 부처 | 링크수 | 평균점수 |','|---|---:|---:|']
for r in con.execute('''select ministry,count(*) links,round(avg(score),3) avg_score from cluster_question_links group by ministry order by links desc'''):
    lines.append(f"| {r['ministry']} | {r['links']} | {r['avg_score']} |")
lines += ['','## Top candidates','']
for i,r in enumerate(con.execute('''select * from v_cluster_question_links order by score desc, news_count desc limit 50'''),1):
    titles=json.loads(r['top_titles_json'] or '[]')
    reasons=json.loads(r['reasons_json'] or '[]')
    shared=json.loads(r['shared_keywords_json'] or '[]')
    q=' '.join((r['text'] or '').split())[:360]
    lines += [f"### {i}. {r['meeting_date']} 제{r['meeting_no']}회 / score {r['score']}",
              f"- 이슈: {r['cluster_ministry']} · {r['topic_label']} · 기사 {r['news_count']}건",
              f"- 대표 기사: {titles[0] if titles else ''}",
              f"- 질문/지시: {(r['question_ministry'] or '미분류')} · {r['question_type']}",
              f"- 근거: {', '.join(reasons)}",
              f"- 공유 키워드: {', '.join(shared[:12])}",
              f"- 대통령 발언: {q}",'']
OUT.write_text('\n'.join(lines))
print(OUT)
