#!/usr/bin/env python3
"""Rule-based reranker for cluster-question candidate links.

Labels high-recall candidates as 확실 / 가능 / 약함 / 무관 using transparent,
reproducible features. This is intentionally conservative enough to become a
review queue before an LLM reranker is introduced.
"""
from __future__ import annotations
import json, re, sqlite3
from pathlib import Path

DB=Path('/Users/seohoseong/Documents/codex/cabinet-question-radar/data/cabinet_question_radar.sqlite')
GENERIC=set('국가 국민 정부 대통령 부처 장관 문제 필요 지원 방안 검토 결과 관련 대해 있는 하는 되는 새로운 경제 지역 교육'.split())
ACTION_TYPES={'대안 요구','검토결과 확인','부처협의 확인','관리 지시','예산/재정 확인'}
BAD_SHARED={'새로운','경제','지역','교육','국가','국민','정부','대통령','장관','부처'}

def j(s):
    try: return json.loads(s or '[]')
    except Exception: return []

def normalize_title_hit(shared, title, qtext):
    strong=[]
    for w in shared:
        if w in GENERIC or w in BAD_SHARED: continue
        if len(w)<2: continue
        if w in title and w in qtext:
            strong.append(w)
    return strong

def classify(row):
    reasons=j(row['reasons_json'])
    shared=j(row['shared_keywords_json'])
    titles=j(row['top_titles_json'])
    title_blob=' '.join(titles)
    qtext=row['text'] or ''
    reason_text=' '.join(reasons)
    score=float(row['score'])
    news_count=int(row['news_count'] or 0)
    qtype=row['question_type'] or ''
    ministry_match='부처 일치' in reason_text
    strong_terms=normalize_title_hit(shared,title_blob,qtext)
    non_generic=[w for w in shared if w not in GENERIC and w not in BAD_SHARED]

    evidence_score=0
    evidence_score += 2 if ministry_match else 0
    evidence_score += min(3,len(strong_terms))
    evidence_score += 1 if news_count>=2 else 0
    evidence_score += 1 if qtype in ACTION_TYPES else 0
    evidence_score += 1 if score>=0.60 else 0
    evidence_score -= 2 if not non_generic else 0
    evidence_score -= 1 if len(non_generic)==1 and non_generic[0] in BAD_SHARED else 0

    if evidence_score>=6:
        label='확실'
    elif evidence_score>=4:
        label='가능'
    elif evidence_score>=2:
        label='약함'
    else:
        label='무관'
    notes=[]
    if ministry_match: notes.append('부처 일치')
    if strong_terms: notes.append('제목-발언 공통 핵심어: '+','.join(strong_terms[:6]))
    if news_count>=2: notes.append(f'동일 클러스터 기사 {news_count}건')
    if qtype in ACTION_TYPES: notes.append(f'질문/지시 유형: {qtype}')
    if not non_generic: notes.append('공유어가 범용어뿐임')
    return label,evidence_score,notes,strong_terms,non_generic

def main():
    con=sqlite3.connect(DB); con.row_factory=sqlite3.Row
    con.executescript('''
    drop table if exists match_review_queue;
    create table match_review_queue(
      review_id text primary key,
      meeting_code text,
      meeting_date text,
      meeting_no integer,
      cluster_ministry text,
      question_ministry text,
      topic_label text,
      news_count integer,
      question_type text,
      candidate_score real,
      review_label text,
      evidence_score integer,
      notes_json text,
      strong_terms_json text,
      shared_keywords_json text,
      top_titles_json text,
      question_text text
    );
    ''')
    rows=con.execute('select * from v_cluster_question_links').fetchall()
    out=[]
    for idx,r in enumerate(rows,1):
        label,es,notes,strong_terms,non_generic=classify(r)
        rid=f"rq-{idx:05d}"
        out.append((rid, '', r['meeting_date'], r['meeting_no'], r['cluster_ministry'], r['question_ministry'], r['topic_label'], r['news_count'], r['question_type'], r['score'], label, es, json.dumps(notes,ensure_ascii=False), json.dumps(strong_terms,ensure_ascii=False), json.dumps(non_generic[:20],ensure_ascii=False), r['top_titles_json'], r['text']))
    con.executemany('insert into match_review_queue values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', out)
    con.executescript('''
    drop view if exists v_review_summary;
    create view v_review_summary as
      select review_label, count(*) count, round(avg(candidate_score),3) avg_candidate_score, round(avg(evidence_score),2) avg_evidence_score
      from match_review_queue group by review_label;
    drop view if exists v_review_by_ministry;
    create view v_review_by_ministry as
      select cluster_ministry, review_label, count(*) count
      from match_review_queue group by cluster_ministry, review_label;
    ''')
    con.commit()
    print('review_queue=',len(out))
    for r in con.execute('select * from v_review_summary order by case review_label when "확실" then 1 when "가능" then 2 when "약함" then 3 else 4 end'):
        print(dict(r))
if __name__=='__main__': main()
