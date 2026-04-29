#!/usr/bin/env python3
from __future__ import annotations
import csv,json,sqlite3
from pathlib import Path
DB=Path('/Users/seohoseong/Documents/codex/cabinet-question-radar/data/cabinet_question_radar.sqlite')
OUT=Path('/Users/seohoseong/Documents/codex/cabinet-question-radar/data/gold_set_draft.md')
CSV=Path('/Users/seohoseong/Documents/codex/cabinet-question-radar/data/gold_set_draft.csv')
con=sqlite3.connect(DB); con.row_factory=sqlite3.Row
order='case final_label when "확정" then 1 when "배경" then 2 when "우연" then 3 else 4 end'
lines=['# Cabinet Question Radar — gold set draft','']
lines+=['## Summary','','| 최종판정 | 건수 |','|---|---:|']
for r in con.execute(f'select final_label,count(*) count from adjudicated_matches group by final_label order by {order}'):
    lines.append(f"| {r['final_label']} | {r['count']} |")
lines+=['','## Draft labels','']
rows=con.execute(f'select * from adjudicated_matches order by {order}, evidence_score desc, candidate_score desc').fetchall()
for i,r in enumerate(rows,1):
    titles=json.loads(r['top_titles_json'] or '[]')
    q=' '.join((r['question_text'] or '').split())[:420]
    lines += [f"### {i}. {r['final_label']} · {r['meeting_date']} 제{r['meeting_no']}회 · {r['ministry']}",
              f"- 원판정: {r['review_label']} / evidence {r['evidence_score']} / candidate {r['candidate_score']}",
              f"- 이슈: {r['topic_label']}",
              f"- 대표 기사: {titles[0] if titles else ''}",
              f"- 질문유형: {r['question_type']}",
              f"- 최종근거: {r['final_reason']}",
              f"- 발언: {q}",'']
OUT.write_text('\n'.join(lines))
with CSV.open('w',newline='') as f:
    w=csv.writer(f)
    w.writerow(['final_label','reason','meeting_date','meeting_no','ministry','topic','review_label','evidence_score','candidate_score','top_title','question_type','question_text'])
    for r in rows:
        titles=json.loads(r['top_titles_json'] or '[]')
        w.writerow([r['final_label'],r['final_reason'],r['meeting_date'],r['meeting_no'],r['ministry'],r['topic_label'],r['review_label'],r['evidence_score'],r['candidate_score'],titles[0] if titles else '',r['question_type'],' '.join((r['question_text'] or '').split())[:700]])
print(OUT); print(CSV)
