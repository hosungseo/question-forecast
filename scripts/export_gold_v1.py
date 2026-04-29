#!/usr/bin/env python3
from __future__ import annotations
import csv,json,sqlite3
from pathlib import Path
DB=Path('/Users/seohoseong/Documents/codex/cabinet-question-radar/data/cabinet_question_radar.sqlite')
OUT=Path('/Users/seohoseong/Documents/codex/cabinet-question-radar/data/gold_v1.md')
CSV=Path('/Users/seohoseong/Documents/codex/cabinet-question-radar/data/gold_v1.csv')
con=sqlite3.connect(DB); con.row_factory=sqlite3.Row
order='case gold_label when "gold_positive_v1" then 1 when "background_v1" then 2 else 3 end'
lines=['# Cabinet Question Radar — gold v1','', '보수적으로 고정한 1차 학습/검증 라벨이다. `gold_positive_v1`만 직접 반영 사례로 사용하고, `gold_negative_v1`은 threshold 조정용 negative set으로 사용한다.','']
lines+=['## Summary','','| label | count |','|---|---:|']
for r in con.execute(f'select gold_label,count(*) count from gold_labels_v1 group by gold_label order by {order}'):
    lines.append(f"| {r['gold_label']} | {r['count']} |")
lines+=['','## Positive v1','']
for i,r in enumerate(con.execute('select * from gold_labels_v1 where gold_label="gold_positive_v1" order by meeting_date, topic_label'),1):
    titles=json.loads(r['top_titles_json'] or '[]')
    q=' '.join((r['question_text'] or '').split())[:500]
    lines += [f"### P{i}. {r['meeting_date']} 제{r['meeting_no']}회 · {r['ministry']}",
              f"- 이슈: {r['topic_label']}", f"- 대표 기사: {titles[0] if titles else ''}",
              f"- 발언유형: {r['question_type']}", f"- gold reason: {r['gold_reason']}", f"- 발언: {q}",'']
lines+=['','## Background / Negative examples','']
for i,r in enumerate(con.execute(f'select * from gold_labels_v1 where gold_label!="gold_positive_v1" order by {order}, meeting_date limit 40'),1):
    titles=json.loads(r['top_titles_json'] or '[]')
    q=' '.join((r['question_text'] or '').split())[:260]
    lines += [f"### N{i}. {r['gold_label']} · {r['meeting_date']} 제{r['meeting_no']}회 · {r['ministry']}",
              f"- 이슈: {r['topic_label']}", f"- 대표 기사: {titles[0] if titles else ''}",
              f"- reason: {r['gold_reason']}", f"- 발언: {q}",'']
OUT.write_text('\n'.join(lines))
with CSV.open('w',newline='') as f:
    w=csv.writer(f); w.writerow(['gold_label','gold_reason','draft_label','meeting_date','meeting_no','ministry','topic','top_title','question_type','question_text'])
    for r in con.execute(f'select * from gold_labels_v1 order by {order}, meeting_date'):
        titles=json.loads(r['top_titles_json'] or '[]')
        w.writerow([r['gold_label'],r['gold_reason'],r['draft_label'],r['meeting_date'],r['meeting_no'],r['ministry'],r['topic_label'],titles[0] if titles else '',r['question_type'],' '.join((r['question_text'] or '').split())[:800]])
print(OUT); print(CSV)
