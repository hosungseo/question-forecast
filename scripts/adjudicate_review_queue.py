#!/usr/bin/env python3
"""Create a first-pass gold-label draft for high-priority review candidates.

Labels:
- 확정: same concrete issue/event and presidential remark directly asks/directs about it.
- 배경: same policy field or agenda mood, but not the same concrete issue.
- 우연: lexical/ministry overlap only.
- 무관: clearly different topic.
"""
from __future__ import annotations
import json, re, sqlite3
from pathlib import Path
DB=Path('/Users/seohoseong/Documents/codex/cabinet-question-radar/data/cabinet_question_radar.sqlite')
CONCRETE_TERMS={
 '캄보디아','범죄','산재','대통령선거','투표','개표','비상진료체계','의료대란','대전','화재','유가족','초등학교','산불','물가','부동산','검찰개혁','경찰국','지방정부','중동','긴급','대응','전공의','의대','원청','임금체불','하도급','마약','유통','전세사기'
}
BROAD_TERMS={'경제','지역','교육','새로운','기업','20년','전국','금융','공직','논의','예산','행안부','기재부','법무부','복지부','교육부','국토부','전략','모든','2차','교통','안전','사고'}

def j(s):
    try:return json.loads(s or '[]')
    except:return []

def has_same_concrete(title, qtext, terms):
    hits=[]
    blob=title+' '+qtext
    for t in CONCRETE_TERMS:
        if t in title and t in qtext:
            hits.append(t)
    for t in terms:
        if t not in BROAD_TERMS and len(t)>=2 and t in title and t in qtext:
            hits.append(t)
    return sorted(set(hits))

def label_row(r):
    titles=j(r['top_titles_json']); title=' '.join(titles)
    q=r['question_text'] or ''
    strong=j(r['strong_terms_json']); notes=j(r['notes_json'])
    same=has_same_concrete(title,q,strong)
    ministry_same=(r['cluster_ministry'] and r['question_ministry'] and r['cluster_ministry']==r['question_ministry']) or any('부처 일치' in n for n in notes)
    qtype=r['question_type'] or ''
    # Direct known patterns
    concrete_same=[t for t in same if t in CONCRETE_TERMS and t not in BROAD_TERMS]
    if concrete_same and qtype in ('대안 요구','검토결과 확인','부처협의 확인','관리 지시','현황 질문','예산/재정 확인'):
        return '확정', '구체 이슈어가 대표 기사와 대통령 발언에 함께 나타남: '+','.join(concrete_same[:6])
    if ministry_same and same:
        return '배경', '같은 부처·정책영역이며 일부 구체어 공유: '+','.join(same[:6])
    non_broad=[t for t in strong if t not in BROAD_TERMS]
    if ministry_same and non_broad:
        return '배경', '부처 일치와 비범용 공유어가 있으나 같은 사건인지 불명확: '+','.join(non_broad[:6])
    if ministry_same:
        return '우연', '부처명 또는 넓은 정책어 중심의 약한 연결'
    if strong:
        return '우연', '공유어는 있으나 부처/구체 이슈 연결 약함: '+','.join(strong[:6])
    return '무관','구체 공유 근거 부족'

def main():
    con=sqlite3.connect(DB); con.row_factory=sqlite3.Row
    con.executescript('''
    drop table if exists adjudicated_matches;
    create table adjudicated_matches(
      review_id text primary key,
      final_label text,
      final_reason text,
      meeting_date text,
      meeting_no integer,
      ministry text,
      topic_label text,
      review_label text,
      evidence_score integer,
      candidate_score real,
      top_titles_json text,
      question_type text,
      question_text text
    );
    ''')
    rows=con.execute('''select * from match_review_queue where review_label in ('확실','가능') order by case review_label when '확실' then 1 else 2 end, evidence_score desc, candidate_score desc, news_count desc''').fetchall()
    out=[]
    for r in rows:
        lab,reason=label_row(r)
        out.append((r['review_id'],lab,reason,r['meeting_date'],r['meeting_no'],r['cluster_ministry'],r['topic_label'],r['review_label'],r['evidence_score'],r['candidate_score'],r['top_titles_json'],r['question_type'],r['question_text']))
    con.executemany('insert into adjudicated_matches values (?,?,?,?,?,?,?,?,?,?,?,?,?)',out)
    con.executescript('''
    drop view if exists v_adjudication_summary;
    create view v_adjudication_summary as select final_label,count(*) count from adjudicated_matches group by final_label;
    ''')
    con.commit()
    print('adjudicated=',len(out))
    for r in con.execute('select * from v_adjudication_summary order by case final_label when "확정" then 1 when "배경" then 2 when "우연" then 3 else 4 end'):
        print(dict(r))
if __name__=='__main__':main()
