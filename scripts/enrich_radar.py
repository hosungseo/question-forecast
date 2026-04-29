#!/usr/bin/env python3
"""Enrich cabinet_question_radar.sqlite with issue clusters and analysis views."""
from __future__ import annotations
import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

DB = Path('/Users/seohoseong/Documents/codex/cabinet-question-radar/data/cabinet_question_radar.sqlite')

MINISTRY_ALIASES = {
    '교육부': ['교육부', '학교', '초등학교', '교사', '학생', '수학여행', '소풍', '체험학습', '유보통합', '사교육'],
    '보건복지부': ['보건복지부', '복지부', '의료', '병원', '의대', '연금', '건강보험', '돌봄', '저출생'],
    '국토교통부': ['국토교통부', '국토부', '부동산', '주택', '전세', '공급', '교통', '철도'],
    '행정안전부': ['행정안전부', '행안부', '재난', '안전', '지방', '공무원', '주민', '민방위'],
    '기획재정부': ['기획재정부', '기재부', '예산', '추경', '세제', '경제', '물가', '재정'],
    '금융위원회': ['금융위원회', '금융위', '은행', '대출', '금리', '자본시장', '보험'],
    '고용노동부': ['고용노동부', '고용부', '노동', '일자리', '임금', '산재', '고용보험'],
    '법무부': ['법무부', '검찰', '범죄', '교정', '출입국'],
}
STOP = set('있는 없는 하는 되는 위해 대한 관련 그리고 그러나 그래서 이번 지금 우리 정부 국민 부처 장관 대통령 기자 뉴스 종합 단독 오늘'.split())

def toks(text):
    return [t.lower() for t in re.findall(r'[가-힣A-Za-z0-9]{2,}', text or '') if t not in STOP]

def infer_ministry(text):
    scores = {}
    for ministry, aliases in MINISTRY_ALIASES.items():
        scores[ministry] = sum(1 for a in aliases if a in text)
    ministry, score = max(scores.items(), key=lambda x:x[1])
    return ministry if score else '미분류'

def cluster_label(text, query):
    ministry = infer_ministry(text + ' ' + query)
    words = [w for w in toks(text) if len(w) >= 2]
    common = [w for w, _ in Counter(words).most_common(4)]
    topic = '·'.join(common[:3]) if common else query
    return ministry, topic

def main():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.executescript('''
    drop table if exists news_issue_clusters;
    drop table if exists news_issue_cluster_members;
    drop view if exists v_meeting_issue_summary;
    drop view if exists v_question_type_summary;
    create table news_issue_clusters (
      cluster_id text primary key,
      meeting_code text,
      ministry text,
      topic_label text,
      news_count integer,
      top_keywords_json text,
      top_titles_json text
    );
    create table news_issue_cluster_members (
      cluster_id text,
      news_id text,
      primary key (cluster_id, news_id)
    );
    ''')
    rows = con.execute('select * from pre_meeting_news').fetchall()
    groups = defaultdict(list)
    for r in rows:
        ministry, topic = cluster_label((r['title'] or '') + ' ' + (r['description'] or ''), r['query'] or '')
        cid = f"{r['meeting_code']}|{ministry}|{topic[:60]}"
        groups[cid].append(r)
    for cid, items in groups.items():
        meeting_code, ministry, topic = cid.split('|', 2)
        all_words=[]
        titles=[]
        for r in items:
            all_words += toks((r['title'] or '') + ' ' + (r['description'] or ''))
            if len(titles) < 5:
                titles.append(r['title'])
            con.execute('insert or replace into news_issue_cluster_members values (?,?)', (cid, r['news_id']))
        top_keywords=[w for w,_ in Counter(all_words).most_common(12)]
        con.execute('insert or replace into news_issue_clusters values (?,?,?,?,?,?,?)', (
            cid, meeting_code, ministry, topic, len(items), json.dumps(top_keywords, ensure_ascii=False), json.dumps(titles, ensure_ascii=False)
        ))
    con.executescript('''
    create view v_meeting_issue_summary as
      select m.meeting_date, m.meeting_no, c.meeting_code, c.ministry, c.topic_label, c.news_count,
             c.top_keywords_json, c.top_titles_json,
             (select count(*) from issue_question_links l
              join news_issue_cluster_members cm on cm.news_id=l.news_id
              where cm.cluster_id=c.cluster_id) as linked_question_count
      from news_issue_clusters c join meetings m on m.meeting_code=c.meeting_code;
    create view v_question_type_summary as
      select m.meeting_date, q.ministry, q.question_type, count(*) count
      from presidential_question_candidates q join meetings m on m.meeting_code=q.meeting_code
      group by m.meeting_date, q.ministry, q.question_type;
    ''')
    con.commit()
    print(f"clusters={len(groups)} db={DB}")
if __name__ == '__main__':
    main()
