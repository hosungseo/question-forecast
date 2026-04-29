#!/usr/bin/env python3
"""Create higher-recall news issue cluster -> presidential question/directive matches."""
from __future__ import annotations
import json, re, sqlite3, math
from collections import Counter
from pathlib import Path

DB=Path('/Users/seohoseong/Documents/codex/cabinet-question-radar/data/cabinet_question_radar.sqlite')
STOP=set('있는 없는 하는 되는 위해 대한 관련 그리고 그러나 그래서 이번 지금 우리 정부 국민 부처 장관 대통령 기자 뉴스 종합 단독 오늘 회의 국무회의'.split())
GENERIC=set('국가 국민 정부 대통령 부처 장관 문제 필요 지원 방안 검토 결과 관련 대해 있는 하는 되는'.split())
MINISTRY_ALIASES={
 '교육부':['교육부','학교','초등학교','교사','학생','수학여행','소풍','체험학습','사교육','유보통합','대학'],
 '보건복지부':['보건복지부','복지부','의료','병원','의대','연금','건강보험','돌봄','저출생','환자'],
 '국토교통부':['국토교통부','국토부','부동산','주택','전세','공급','교통','철도','아파트'],
 '행정안전부':['행정안전부','행안부','재난','안전','지방','공무원','주민','화재','호우'],
 '기획재정부':['기획재정부','기재부','예산','추경','세제','경제','물가','재정','세금'],
 '금융위원회':['금융위원회','금융위','은행','대출','금리','자본시장','보험','금융'],
 '고용노동부':['고용노동부','고용부','노동','일자리','임금','산재','고용보험','노조'],
 '법무부':['법무부','검찰','범죄','교정','출입국','재판','수사'],
}

def toks(s):
    out=[]
    for t in re.findall(r'[가-힣A-Za-z0-9]{2,}', s or ''):
        if t in STOP or t.lower() in STOP: continue
        out.append(t.lower())
    return out

def infer_ministry(text):
    scores={m:sum(1 for a in aliases if a in text) for m,aliases in MINISTRY_ALIASES.items()}
    m,score=max(scores.items(), key=lambda x:x[1])
    return m if score else ''

def load_json(s):
    try: return json.loads(s or '[]')
    except Exception: return []

def score_pair(cluster, question):
    c_words=set(load_json(cluster['top_keywords_json'])) | set(toks(cluster['topic_label']))
    q_words=set(load_json(question['keywords_json']))
    shared=sorted((c_words & q_words) - GENERIC)
    c_text=(cluster['topic_label'] or '')+' '+' '.join(load_json(cluster['top_titles_json']))
    q_text=question['text'] or ''
    c_min=cluster['ministry'] or infer_ministry(c_text)
    q_min=question['ministry'] or infer_ministry(q_text)
    ministry_match = bool(c_min and q_min and c_min==q_min)
    alias_hit = False
    if c_min:
        alias_hit = any(a in q_text for a in MINISTRY_ALIASES.get(c_min,[]))
    # weighted score: cluster prominence + ministry/topic overlap + lexical overlap
    news_weight=min(0.25, math.log1p(cluster['news_count'])/12)
    lexical=min(0.45, len(shared)/10)
    ministry_bonus=0.35 if ministry_match else (0.18 if alias_hit else 0)
    type_bonus=0.08 if question['question_type'] in ('대안 요구','검토결과 확인','부처협의 확인','관리 지시') else 0
    score=round(news_weight+lexical+ministry_bonus+type_bonus,3)
    reasons=[]
    if ministry_match: reasons.append(f'부처 일치:{c_min}')
    elif alias_hit: reasons.append(f'발언 내 {c_min} 관련어')
    if shared: reasons.append('공유어:'+','.join(shared[:8]))
    if cluster['news_count']>=3: reasons.append(f'기사량:{cluster["news_count"]}')
    return score, shared, reasons, c_min or q_min or '미분류'

def main():
    con=sqlite3.connect(DB); con.row_factory=sqlite3.Row
    con.executescript('''
    drop table if exists cluster_question_links;
    create table cluster_question_links(
      link_id text primary key,
      meeting_code text,
      cluster_id text,
      question_id text,
      score real,
      ministry text,
      shared_keywords_json text,
      reasons_json text
    );
    ''')
    clusters=con.execute('select * from news_issue_clusters').fetchall()
    by_meeting={}
    for q in con.execute('select * from presidential_question_candidates'):
        by_meeting.setdefault(q['meeting_code'],[]).append(q)
    rows=[]
    for c in clusters:
        for q in by_meeting.get(c['meeting_code'],[]):
            score, shared, reasons, ministry=score_pair(c,q)
            if score>=0.48 and (shared or '부처 일치:'+ministry in reasons or any(r.startswith('발언 내') for r in reasons)):
                lid=f"{abs(hash((c['cluster_id'],q['question_id']))):x}"
                rows.append((lid,c['meeting_code'],c['cluster_id'],q['question_id'],score,ministry,json.dumps(shared[:20],ensure_ascii=False),json.dumps(reasons,ensure_ascii=False)))
    con.executemany('insert or replace into cluster_question_links values (?,?,?,?,?,?,?,?)', rows)
    con.executescript('''
    drop view if exists v_cluster_question_links;
    create view v_cluster_question_links as
      select m.meeting_date,m.meeting_no,c.ministry as cluster_ministry,c.topic_label,c.news_count,
             q.ministry as question_ministry,q.question_type,l.score,l.shared_keywords_json,l.reasons_json,
             c.top_titles_json,q.text
      from cluster_question_links l
      join meetings m on m.meeting_code=l.meeting_code
      join news_issue_clusters c on c.cluster_id=l.cluster_id
      join presidential_question_candidates q on q.question_id=l.question_id;
    ''')
    con.commit()
    print(f'cluster_question_links={len(rows)}')
if __name__=='__main__': main()
