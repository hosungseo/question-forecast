#!/usr/bin/env python3
from __future__ import annotations
import sqlite3
from pathlib import Path

DB = Path('/Users/seohoseong/Documents/codex/cabinet-question-radar/data/cabinet_question_radar.sqlite')
OUT = Path('/Users/seohoseong/Documents/codex/cabinet-question-radar/data/summary.md')

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
meetings = conn.execute('''
select m.*,
  (select count(*) from pre_meeting_news n where n.meeting_code=m.meeting_code) news_count,
  (select count(*) from presidential_question_candidates q where q.meeting_code=m.meeting_code) question_count,
  (select count(*) from issue_question_links l where l.meeting_code=m.meeting_code) link_count
from meetings m order by meeting_date desc
''').fetchall()

lines = ['# Cabinet Question Radar — pilot summary', '']
lines.append('| 회의일 | 회차 | 회의 전 뉴스 | 질문/지시 후보 | 링크 후보 |')
lines.append('|---|---:|---:|---:|---:|')
for m in meetings:
    lines.append(f"| {m['meeting_date']} | {m['meeting_no']} | {m['news_count']} | {m['question_count']} | {m['link_count']} |")

lines.append('\n## Top issue-question links\n')
links = conn.execute('''
select m.meeting_date,n.pub_date,n.query,n.title,q.ministry,q.question_type,l.score,l.shared_keywords_json,q.text
from issue_question_links l
join meetings m on l.meeting_code=m.meeting_code
join pre_meeting_news n on l.news_id=n.news_id
join presidential_question_candidates q on l.question_id=q.question_id
order by l.score desc limit 20
''').fetchall()
if not links:
    lines.append('- 링크 후보 없음')
else:
    for i, r in enumerate(links, 1):
        qtext = ' '.join(r['text'].split())[:260]
        lines.append(f"### {i}. {r['meeting_date']} / score {r['score']}")
        lines.append(f"- 뉴스({r['pub_date']}, `{r['query']}`): {r['title']}")
        lines.append(f"- 질문유형: {r['ministry'] or '미분류'} · {r['question_type']}")
        lines.append(f"- 공유 키워드: {r['shared_keywords_json']}")
        lines.append(f"- 대통령 발언: {qtext}\n")

OUT.write_text('\n'.join(lines))
print(OUT)
