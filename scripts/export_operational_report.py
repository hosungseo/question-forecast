#!/usr/bin/env python3
from __future__ import annotations
import json,sqlite3
from pathlib import Path
DB=Path('/Users/seohoseong/Documents/codex/cabinet-question-radar/data/cabinet_question_radar.sqlite')
OUT=Path('/Users/seohoseong/Documents/codex/cabinet-question-radar/data/operational_v2_report.md')
con=sqlite3.connect(DB); con.row_factory=sqlite3.Row
lines=['# Cabinet Question Radar — operational v2 report','', 'gold v1 교훈을 반영한 운영용 점수다. `auto_high`는 바로 검토 우선, `review_high`는 사람/LLM 2차 판정 대상으로 본다.','']
lines += ['## Band summary','','| band | count | avg score |','|---|---:|---:|']
for r in con.execute('select * from v_operational_v2_summary order by case v2_band when "auto_high" then 1 when "review_high" then 2 when "review_low" then 3 else 4 end'):
    lines.append(f"| {r['v2_band']} | {r['count']} | {r['avg_score']} |")
lines += ['','## Top operational candidates','']
for i,r in enumerate(con.execute('select * from operational_scores_v2 where v2_band in ("auto_high","review_high") order by v2_score desc, news_count desc limit 60'),1):
    titles=json.loads(r['top_titles_json'] or '[]')
    rat=json.loads(r['rationale_json'] or '[]')
    q=' '.join((r['question_text'] or '').split())[:380]
    lines += [f"### {i}. {r['v2_band']} · score {r['v2_score']} · {r['meeting_date']} 제{r['meeting_no']}회 · {r['cluster_ministry']}",
              f"- 이슈: {r['topic_label']} / 기사 {r['news_count']}건",
              f"- 대표 기사: {titles[0] if titles else ''}",
              f"- 질문/지시: {(r['question_ministry'] or '미분류')} · {r['question_type']}",
              f"- v2 근거: {', '.join(rat)}",
              f"- 발언: {q}",'']
lines += ['','## How to use','','1. 회의 전 D-7~D-1 뉴스 수집을 돌린다.','2. `operational_scores_v2`에서 `auto_high`, `review_high`를 우선 본다.','3. 예상 질문 작성 시 `bundle` 단위로 묶는다: 이슈 → 대통령 질문 패턴 → 담당부처 확인사항.','4. 최종 발송/보고 전에는 반드시 사람이 기사와 회의록 원문을 확인한다.']
OUT.write_text('\n'.join(lines)); print(OUT)
