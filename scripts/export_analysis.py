#!/usr/bin/env python3
from __future__ import annotations
import json, sqlite3
from pathlib import Path
DB=Path('/Users/seohoseong/Documents/codex/cabinet-question-radar/data/cabinet_question_radar.sqlite')
OUT=Path('/Users/seohoseong/Documents/codex/cabinet-question-radar/data/analysis.md')
con=sqlite3.connect(DB); con.row_factory=sqlite3.Row
lines=['# Cabinet Question Radar — analysis report','']
meta={r['key']:r['value'] for r in con.execute('select * from run_meta')}
lines += ['## Run meta','']
for k,v in meta.items(): lines.append(f'- {k}: `{v}`')
lines += ['','## Coverage','','| 회의일 | 회차 | 뉴스 | 이슈클러스터 | 질문/지시 후보 | 링크 후보 |','|---|---:|---:|---:|---:|---:|']
for r in con.execute('''select m.meeting_date,m.meeting_no,
(select count(*) from pre_meeting_news n where n.meeting_code=m.meeting_code) news,
(select count(*) from news_issue_clusters c where c.meeting_code=m.meeting_code) clusters,
(select count(*) from presidential_question_candidates q where q.meeting_code=m.meeting_code) questions,
(select count(*) from issue_question_links l where l.meeting_code=m.meeting_code) links
from meetings m order by m.meeting_date desc'''):
    lines.append(f"| {r['meeting_date']} | {r['meeting_no']} | {r['news']} | {r['clusters']} | {r['questions']} | {r['links']} |")
lines += ['','## Top pre-meeting issue clusters','','| 회의일 | 부처 | 뉴스수 | 링크수 | 토픽 | 대표 제목 |','|---|---|---:|---:|---|---|']
for r in con.execute('''select * from v_meeting_issue_summary order by news_count desc, linked_question_count desc limit 30'''):
    titles=json.loads(r['top_titles_json'] or '[]')
    title=(titles[0] if titles else '').replace('|','/')[:90]
    lines.append(f"| {r['meeting_date']} | {r['ministry']} | {r['news_count']} | {r['linked_question_count']} | {r['topic_label'][:40]} | {title} |")
lines += ['','## Question/directive type summary','','| 회의일 | 부처 | 유형 | 건수 |','|---|---|---|---:|']
for r in con.execute('''select * from v_question_type_summary order by meeting_date desc, count desc limit 60'''):
    lines.append(f"| {r['meeting_date']} | {r['ministry'] or '미분류'} | {r['question_type']} | {r['count']} |")
lines += ['','## Strongest news → presidential-question candidates','']
for i,r in enumerate(con.execute('''select m.meeting_date,n.pub_date,n.query,n.title,q.ministry,q.question_type,l.score,l.shared_keywords_json,q.text
from issue_question_links l join meetings m on m.meeting_code=l.meeting_code join pre_meeting_news n on n.news_id=l.news_id join presidential_question_candidates q on q.question_id=l.question_id
order by l.score desc limit 25'''),1):
    q=' '.join((r['text'] or '').split())[:320]
    lines += [f"### {i}. {r['meeting_date']} / score {r['score']}",f"- 뉴스({r['pub_date']}, `{r['query']}`): {r['title']}",f"- 질문/지시 후보: {r['ministry'] or '미분류'} · {r['question_type']}",f"- 공유 키워드: {r['shared_keywords_json']}",f"- 대통령 발언: {q}",'']
lines += ['','## Reading notes','','- 현재 링크는 확정 매핑이 아니라 candidate link다.','- Broad 키워드 잡음이 있으므로 다음 개선은 부처명·고유명사·기사량 급증 신호 가중치다.','- Naver News API는 과거 기간 필터가 직접 없으므로 `YYYY.MM.DD + 키워드` 쿼리로 회의 전 주간을 근사 수집한다.']
OUT.write_text('\n'.join(lines))
print(OUT)
