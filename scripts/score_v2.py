#!/usr/bin/env python3
"""Build operational v2 scores for cluster-question links.

v2 is calibrated from gold v1 lessons:
- concrete shared issue bundles matter more than generic ministry/keyword overlap
- candidate_score alone is too noisy
- evidence_score alone is weak
- output should separate auto-high-confidence from review-needed candidates
"""
from __future__ import annotations
import json, re, sqlite3
from pathlib import Path
DB=Path('/Users/seohoseong/Documents/codex/cabinet-question-radar/data/cabinet_question_radar.sqlite')
BUNDLES={
 'cambodia_crime':['캄보디아','범죄'],
 'industrial_accident':['산재','원청','임금체불','하도급'],
 'middle_east_macro':['중동','에너지','수급','금융시장','유가'],
 'prices_burden':['물가','부담','지원'],
 'medical_disruption':['의료대란','비상진료','전공의','의대'],
 'school_field_trip':['초등학교','소풍','수학여행','체험학습','교사'],
 'disaster_safety':['화재','산불','호우','재난','사고','안전'],
 'real_estate':['부동산','주택','전세','공급','아파트'],
}
GENERIC={'경제','지역','교육','새로운','기업','20년','전국','금융','공직','논의','예산','행안부','기재부','법무부','복지부','교육부','국토부','전략','모든','2차','교통','대응','긴급'}
ACTION_TYPES={'대안 요구','검토결과 확인','부처협의 확인','관리 지시','예산/재정 확인','현황 질문'}

def j(s):
    try:return json.loads(s or '[]')
    except:return []

def bundle_hits(title,q):
    hits=[]
    for name,terms in BUNDLES.items():
        common=[t for t in terms if t in title and t in q]
        if common:
            hits.append((name,common))
    return hits

def score(row):
    titles=j(row['top_titles_json']); title=' '.join(titles)
    q=row['text'] or ''
    shared=[w for w in j(row['shared_keywords_json']) if w not in GENERIC]
    reasons=j(row['reasons_json'])
    b=bundle_hits(title,q)
    ministry_match=any('부처 일치' in r for r in reasons)
    news_count=int(row['news_count'] or 0)
    qtype=row['question_type'] or ''
    s=0.0
    rationale=[]
    if b:
        s += 0.55
        rationale.append('bundle:'+ ';'.join(f'{name}({",".join(c)})' for name,c in b[:3]))
    if ministry_match:
        s += 0.12
        rationale.append('ministry_match')
    if shared:
        s += min(0.15, 0.04*len(shared))
        rationale.append('specific_shared:'+','.join(shared[:6]))
    if news_count>=3:
        s += 0.08
        rationale.append(f'cluster_volume:{news_count}')
    elif news_count>=2:
        s += 0.04
        rationale.append(f'cluster_volume:{news_count}')
    if qtype in ACTION_TYPES:
        s += 0.05
        rationale.append('actionable_question_type')
    # penalty for only generic/ministry signal
    if not b and len(shared)==0:
        s -= 0.18
        rationale.append('generic_only_penalty')
    s=max(0,min(1,round(s,3)))
    if s>=0.72:
        band='auto_high'
    elif s>=0.50:
        band='review_high'
    elif s>=0.32:
        band='review_low'
    else:
        band='discard'
    return s,band,rationale,b,shared

def main():
    con=sqlite3.connect(DB); con.row_factory=sqlite3.Row
    con.executescript('''
    drop table if exists operational_scores_v2;
    create table operational_scores_v2(
      row_id text primary key,
      meeting_date text,
      meeting_no integer,
      cluster_ministry text,
      question_ministry text,
      topic_label text,
      news_count integer,
      question_type text,
      v2_score real,
      v2_band text,
      rationale_json text,
      bundle_hits_json text,
      specific_shared_json text,
      top_titles_json text,
      question_text text
    );
    ''')
    rows=con.execute('select * from v_cluster_question_links').fetchall()
    out=[]
    for i,r in enumerate(rows,1):
        s,band,rat,b,shared=score(r)
        out.append((f'v2-{i:05d}',r['meeting_date'],r['meeting_no'],r['cluster_ministry'],r['question_ministry'],r['topic_label'],r['news_count'],r['question_type'],s,band,json.dumps(rat,ensure_ascii=False),json.dumps(b,ensure_ascii=False),json.dumps(shared,ensure_ascii=False),r['top_titles_json'],r['text']))
    con.executemany('insert into operational_scores_v2 values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',out)
    con.executescript('''
    drop view if exists v_operational_v2_summary;
    create view v_operational_v2_summary as select v2_band,count(*) count,round(avg(v2_score),3) avg_score from operational_scores_v2 group by v2_band;
    ''')
    con.commit()
    print('operational_scores_v2=',len(out))
    for r in con.execute('select * from v_operational_v2_summary order by case v2_band when "auto_high" then 1 when "review_high" then 2 when "review_low" then 3 else 4 end'):
        print(dict(r))
if __name__=='__main__':main()
