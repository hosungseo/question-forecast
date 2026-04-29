#!/usr/bin/env python3
"""Freeze a conservative gold v1 from the adjudication draft.

This pass is intentionally stricter than the draft adjudicator. It only keeps
cases where the representative news issue and the presidential remark share a
specific event/policy object, not merely a ministry, generic risk, place, or
broad macro topic.
"""
from __future__ import annotations
import json, sqlite3, re
from pathlib import Path
DB=Path('/Users/seohoseong/Documents/codex/cabinet-question-radar/data/cabinet_question_radar.sqlite')

# Positive anchors require one of these concrete issue bundles.
BUNDLES={
 'cambodia_crime': ['캄보디아','범죄'],
 'industrial_accident': ['산재'],
 'middle_east_macro': ['중동'],
 'prices_burden': ['물가'],
}
# Terms too broad to establish positive evidence by themselves.
WEAK_ONLY={'대전','화재','행안부','지방정부','교통','유통','2차','대응','긴급','기재부','예산'}

def j(s):
    try:return json.loads(s or '[]')
    except:return []

def has_bundle(title,qtext):
    blob_title=title
    blob_q=qtext
    hits=[]
    for name,terms in BUNDLES.items():
        if all(t in blob_title or t in blob_q for t in terms) and any(t in blob_title and t in blob_q for t in terms):
            # stronger: at least one bundle term must be in both title and question.
            common=[t for t in terms if t in blob_title and t in blob_q]
            if common:
                hits.append(name+':' + ','.join(common))
    return hits

def classify(row):
    titles=j(row['top_titles_json']); title=' '.join(titles)
    q=row['question_text'] or ''
    reason=row['final_reason'] or ''
    bundle=has_bundle(title,q)
    if bundle:
        return 'gold_positive_v1','; '.join(bundle)
    # repeated Cambodia rows with 범죄 are positive even if title is truncated weirdly.
    if '캄보디아' in title and '범죄' in q:
        return 'gold_positive_v1','캄보디아 기사와 범죄 관련 대통령 질문 직접 대응'
    if '산재' in title and '산재' in q:
        return 'gold_positive_v1','산재 기사와 산재/원청책임 발언 직접 대응'
    if '중동' in title and '중동' in q and any(k in q for k in ['경제','금융시장','에너지','수급','수출입']):
        return 'gold_positive_v1','중동 리스크와 경제안보 대응 발언 대응'
    if '물가' in title and '물가' in q:
        return 'gold_positive_v1','물가 기사와 국민 부담/지원 질문 대응'
    if row['final_label']=='우연':
        return 'gold_negative_v1','draft에서 우연으로 판정됨'
    if row['final_label']=='배경':
        return 'background_v1','같은 정책영역 배경이나 직접 소재 아님'
    return 'gold_negative_v1','구체 사건/정책 객체 공유 부족: '+reason

def main():
    con=sqlite3.connect(DB); con.row_factory=sqlite3.Row
    con.executescript('''
    drop table if exists gold_labels_v1;
    create table gold_labels_v1(
      review_id text primary key,
      gold_label text,
      gold_reason text,
      draft_label text,
      meeting_date text,
      meeting_no integer,
      ministry text,
      topic_label text,
      top_titles_json text,
      question_type text,
      question_text text
    );
    ''')
    rows=con.execute('select a.*, r.review_id from adjudicated_matches a join match_review_queue r on r.review_id=a.review_id').fetchall()
    out=[]
    for r in rows:
        lab,why=classify(r)
        out.append((r['review_id'],lab,why,r['final_label'],r['meeting_date'],r['meeting_no'],r['ministry'],r['topic_label'],r['top_titles_json'],r['question_type'],r['question_text']))
    con.executemany('insert into gold_labels_v1 values (?,?,?,?,?,?,?,?,?,?,?)',out)
    con.executescript('''
    drop view if exists v_gold_v1_summary;
    create view v_gold_v1_summary as select gold_label,count(*) count from gold_labels_v1 group by gold_label;
    ''')
    con.commit()
    for r in con.execute('select * from v_gold_v1_summary order by gold_label'):
        print(dict(r))
if __name__=='__main__':main()
