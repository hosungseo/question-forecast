#!/usr/bin/env python3
from __future__ import annotations
import json, sqlite3
from pathlib import Path
DB=Path('/Users/seohoseong/Documents/codex/cabinet-question-radar/data/cabinet_question_radar.sqlite')
OUT=Path('/Users/seohoseong/Documents/codex/cabinet-question-radar/data/review_queue.md')
CSV=Path('/Users/seohoseong/Documents/codex/cabinet-question-radar/data/review_queue_top.csv')
con=sqlite3.connect(DB); con.row_factory=sqlite3.Row
order='case review_label when "확실" then 1 when "가능" then 2 when "약함" then 3 else 4 end'
lines=['# Cabinet Question Radar — review queue','']
lines += ['## Label summary','','| 판정 | 건수 | 후보평균 | 근거평균 |','|---|---:|---:|---:|']
for r in con.execute(f'select * from v_review_summary order by {order}'):
    lines.append(f"| {r['review_label']} | {r['count']} | {r['avg_candidate_score']} | {r['avg_evidence_score']} |")
lines += ['','## Ministry × label','','| 부처 | 확실 | 가능 | 약함 | 무관 |','|---|---:|---:|---:|---:|']
mins=sorted({r['cluster_ministry'] for r in con.execute('select distinct cluster_ministry from match_review_queue')})
for m in mins:
    counts={r['review_label']:r['count'] for r in con.execute('select review_label,count(*) count from match_review_queue where cluster_ministry=? group by review_label',(m,))}
    lines.append(f"| {m} | {counts.get('확실',0)} | {counts.get('가능',0)} | {counts.get('약함',0)} | {counts.get('무관',0)} |")
lines += ['','## 확실/가능 우선 검토 후보','']
rows=con.execute(f'''select * from match_review_queue where review_label in ('확실','가능') order by {order}, evidence_score desc, candidate_score desc, news_count desc limit 80''').fetchall()
if not rows:
    lines.append('- 없음')
for i,r in enumerate(rows,1):
    titles=json.loads(r['top_titles_json'] or '[]')
    notes=json.loads(r['notes_json'] or '[]')
    strong=json.loads(r['strong_terms_json'] or '[]')
    q=' '.join((r['question_text'] or '').split())[:360]
    lines += [f"### {i}. {r['review_label']} · {r['meeting_date']} 제{r['meeting_no']}회 · {r['cluster_ministry']} · evidence {r['evidence_score']}",
              f"- 이슈: {r['topic_label']} / 기사 {r['news_count']}건",
              f"- 대표 기사: {titles[0] if titles else ''}",
              f"- 질문/지시: {(r['question_ministry'] or '미분류')} · {r['question_type']}",
              f"- 근거: {', '.join(notes)}",
              f"- 핵심어: {', '.join(strong)}",
              f"- 발언: {q}",'']
OUT.write_text('\n'.join(lines))
# CSV-lite for spreadsheet import
import csv
with CSV.open('w', newline='') as f:
    w=csv.writer(f)
    w.writerow(['label','meeting_date','meeting_no','ministry','topic','news_count','question_type','evidence_score','candidate_score','top_title','question_text'])
    for r in con.execute(f'''select * from match_review_queue order by {order}, evidence_score desc, candidate_score desc limit 300'''):
        titles=json.loads(r['top_titles_json'] or '[]')
        w.writerow([r['review_label'],r['meeting_date'],r['meeting_no'],r['cluster_ministry'],r['topic_label'],r['news_count'],r['question_type'],r['evidence_score'],r['candidate_score'],titles[0] if titles else '', ' '.join((r['question_text'] or '').split())[:500]])
print(OUT)
print(CSV)
