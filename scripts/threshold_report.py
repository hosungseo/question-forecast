#!/usr/bin/env python3
from __future__ import annotations
import sqlite3
from pathlib import Path
DB=Path('/Users/seohoseong/Documents/codex/cabinet-question-radar/data/cabinet_question_radar.sqlite')
OUT=Path('/Users/seohoseong/Documents/codex/cabinet-question-radar/data/threshold_report.md')
con=sqlite3.connect(DB); con.row_factory=sqlite3.Row
rows=con.execute('''select r.review_id, r.candidate_score, r.evidence_score, g.gold_label
from match_review_queue r left join gold_labels_v1 g on g.review_id=r.review_id
where g.gold_label in ('gold_positive_v1','gold_negative_v1')''').fetchall()
lines=['# Cabinet Question Radar — threshold calibration','']
lines.append('Gold v1 기준으로 candidate_score/evidence_score threshold를 간단 점검한 표다.')
lines += ['','## candidate_score thresholds','','| threshold | selected | TP | FP | precision | recall |','|---:|---:|---:|---:|---:|---:|']
pos=sum(1 for r in rows if r['gold_label']=='gold_positive_v1')
for th in [0.50,0.52,0.54,0.56,0.58,0.60,0.62]:
    sel=[r for r in rows if r['candidate_score']>=th]
    tp=sum(1 for r in sel if r['gold_label']=='gold_positive_v1')
    fp=sum(1 for r in sel if r['gold_label']=='gold_negative_v1')
    prec=tp/(tp+fp) if tp+fp else 0
    rec=tp/pos if pos else 0
    lines.append(f'| {th:.2f} | {len(sel)} | {tp} | {fp} | {prec:.2f} | {rec:.2f} |')
lines += ['','## evidence_score thresholds','','| threshold | selected | TP | FP | precision | recall |','|---:|---:|---:|---:|---:|---:|']
for th in [2,3,4,5,6,7]:
    sel=[r for r in rows if r['evidence_score']>=th]
    tp=sum(1 for r in sel if r['gold_label']=='gold_positive_v1')
    fp=sum(1 for r in sel if r['gold_label']=='gold_negative_v1')
    prec=tp/(tp+fp) if tp+fp else 0
    rec=tp/pos if pos else 0
    lines.append(f'| {th} | {len(sel)} | {tp} | {fp} | {prec:.2f} | {rec:.2f} |')
lines += ['','## Recommendation','','- 현재 gold v1이 8 positive / 24 negative로 작으므로 수치는 방향성만 본다.','- `evidence_score >= 4`는 recall은 높지만 precision이 낮다.','- `candidate_score >= 0.54` 부근이 작은 gold set에서 균형점으로 보이나, 최종 운영은 LLM/human adjudication을 2차 단계로 두는 것이 안전하다.']
OUT.write_text('\n'.join(lines)); print(OUT)
