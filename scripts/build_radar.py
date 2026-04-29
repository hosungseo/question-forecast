#!/usr/bin/env python3
"""Build a pilot Cabinet Question Radar SQLite database.

Reads the local cabinet-meeting remarks DB, extracts presidential question/directive
candidates, collects pre-meeting Naver News items for simple ministry/topic queries,
and creates lightweight keyword-based candidate links.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import os
import re
import sqlite3
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

SOURCE_DB = Path('/Users/seohoseong/Documents/codex/lee_jm_president_remarks_db/lee_jm_president_remarks.sqlite')
DEFAULT_OUT = Path('/Users/seohoseong/Documents/codex/cabinet-question-radar/data/cabinet_question_radar.sqlite')

MINISTRY_QUERIES = [
    '교육부', '보건복지부', '국토교통부', '행정안전부', '기획재정부', '고용노동부',
    '중소벤처기업부', '금융위원회', '법무부', '환경부', '농림축산식품부', '과학기술정보통신부',
]
TOPIC_QUERIES = [
    '초등학교 현장체험학습', '소풍 수학여행 교사 책임', '의료 대란', '부동산 공급',
    '전세사기', '물가 민생', '산불 재난', '청년 일자리', '저출생 돌봄', '국립대병원',
]

QUESTION_PATTERNS = [
    '어떤', '어떻', '가능', '되나', '됐나', '되는지', '검토', '대안', '예산',
    '협의', '챙겨', '필요', '문제', '부담', '지원', '방안', '결과', '?',
]
STOPWORDS = set('있는 없는 하는 되는 위해 대한 관련 그리고 그러나 그래서 이번 지금 우리 정부 국민 부처 장관 대통령'.split())


def strip_tags(s: str) -> str:
    return re.sub(r'<[^>]+>', '', html.unescape(s or '')).strip()


def tokenize_ko(text: str) -> set[str]:
    toks = re.findall(r'[가-힣A-Za-z0-9]{2,}', text or '')
    out = set()
    for t in toks:
        if t in STOPWORDS:
            continue
        if len(t) >= 2:
            out.add(t.lower())
    return out


def infer_ministry(text: str) -> str:
    for q in MINISTRY_QUERIES:
        short = q.replace('보건복지부', '복지부').replace('국토교통부', '국토부').replace('행정안전부', '행안부').replace('기획재정부', '기재부').replace('고용노동부', '고용부')
        if q in text or short in text:
            return q
    return ''


def question_type(text: str) -> str:
    if any(k in text for k in ['예산', '비용', '재정']):
        return '예산/재정 확인'
    if any(k in text for k in ['협의', '조정', '타 부처']):
        return '부처협의 확인'
    if any(k in text for k in ['대안', '방안', '지원', '가능']):
        return '대안 요구'
    if any(k in text for k in ['검토', '결과', '어땠']):
        return '검토결과 확인'
    if any(k in text for k in ['챙겨', '만전', '신경']):
        return '관리 지시'
    return '현황 질문'


def naver_search(query: str, start_date: dt.date, end_date: dt.date, display: int, pause: float, max_pages: int) -> list[dict]:
    cid = os.environ.get('NAVER_CLIENT_ID')
    sec = os.environ.get('NAVER_CLIENT_SECRET')
    if not cid or not sec:
        raise SystemExit('NAVER_CLIENT_ID / NAVER_CLIENT_SECRET env vars are required')
    items = []
    global_rank = 0
    for page in range(max_pages):
        start = page * display + 1
        if start > 1000:
            break
        url = 'https://openapi.naver.com/v1/search/news.json?' + urllib.parse.urlencode({
            'query': query,
            'display': display,
            'start': start,
            'sort': 'date',
        })
        req = urllib.request.Request(url, headers={
            'X-Naver-Client-Id': cid,
            'X-Naver-Client-Secret': sec,
            'User-Agent': 'Mozilla/5.0',
        })
        with urllib.request.urlopen(req, timeout=15) as res:
            data = json.load(res)
        time.sleep(pause)
        batch = data.get('items', [])
        if not batch:
            break
        oldest = None
        for it in batch:
            global_rank += 1
            pub_raw = it.get('pubDate', '')
            try:
                pub_dt = dt.datetime.strptime(pub_raw, '%a, %d %b %Y %H:%M:%S %z').date()
            except Exception:
                pub_dt = None
            if pub_dt:
                oldest = pub_dt if oldest is None else min(oldest, pub_dt)
            if pub_dt and not (start_date <= pub_dt <= end_date):
                continue
            title = strip_tags(it.get('title', ''))
            desc = strip_tags(it.get('description', ''))
            url_key = it.get('originallink') or it.get('link') or title
            news_id = hashlib.sha1((query + '|' + url_key).encode()).hexdigest()[:16]
            items.append({
                'news_id': news_id,
                'query': query,
                'rank': global_rank,
                'title': title,
                'description': desc,
                'pub_date': pub_dt.isoformat() if pub_dt else '',
                'link': it.get('link', ''),
                'originallink': it.get('originallink', ''),
            })
        if oldest and oldest < start_date:
            break
    return items


def init_db(conn: sqlite3.Connection):
    conn.executescript('''
    create table if not exists meetings (
      meeting_code text primary key,
      meeting_date text,
      meeting_no integer,
      meeting_title text,
      source_file_name text
    );
    create table if not exists presidential_question_candidates (
      question_id text primary key,
      meeting_code text,
      remark_id integer,
      remark_order integer,
      speaker text,
      ministry text,
      question_type text,
      text text,
      keywords_json text
    );
    create table if not exists pre_meeting_news (
      news_id text primary key,
      meeting_code text,
      window_start text,
      window_end text,
      query text,
      api_rank integer,
      pub_date text,
      title text,
      description text,
      link text,
      originallink text,
      keywords_json text
    );
    create table if not exists issue_question_links (
      link_id text primary key,
      meeting_code text,
      news_id text,
      question_id text,
      score real,
      shared_keywords_json text,
      rationale text
    );
    create table if not exists run_meta (key text primary key, value text);
    ''')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source-db', type=Path, default=SOURCE_DB)
    ap.add_argument('--out-db', type=Path, default=DEFAULT_OUT)
    ap.add_argument('--limit-meetings', type=int, default=5)
    ap.add_argument('--window-days', type=int, default=7)
    ap.add_argument('--display', type=int, default=20)
    ap.add_argument('--pause', type=float, default=0.2)
    ap.add_argument('--max-pages', type=int, default=5)
    ap.add_argument('--queries', nargs='*', default=None)
    ap.add_argument('--daily-date-queries', action='store_true', help='also query YYYY.MM.DD + each base query for every day in the pre-meeting window')
    ap.add_argument('--date-query-days', type=int, default=None, help='limit daily date queries to the last N days before the meeting')
    args = ap.parse_args()

    args.out_db.parent.mkdir(parents=True, exist_ok=True)
    source = sqlite3.connect(args.source_db)
    source.row_factory = sqlite3.Row
    out = sqlite3.connect(args.out_db)
    out.row_factory = sqlite3.Row
    init_db(out)

    meetings = source.execute('''
      select meeting_code, meeting_date, meeting_no, meeting_title, source_file_name
      from meetings order by meeting_date desc limit ?
    ''', (args.limit_meetings,)).fetchall()

    queries = args.queries or (MINISTRY_QUERIES[:8] + TOPIC_QUERIES[:8])
    news_seen = set()
    q_count = n_count = l_count = 0

    for m in meetings:
        out.execute('insert or replace into meetings values (?,?,?,?,?)', tuple(m))
        mdate = dt.date.fromisoformat(m['meeting_date'])
        ws = mdate - dt.timedelta(days=args.window_days)
        we = mdate - dt.timedelta(days=1)

        remarks = source.execute('''
          select id, meeting_code, remark_order, speaker, text
          from remarks
          where meeting_code=? and speaker like '대통령%'
          order by remark_order
        ''', (m['meeting_code'],)).fetchall()
        questions = []
        for r in remarks:
            text = r['text']
            if not any(p in text for p in QUESTION_PATTERNS):
                continue
            if len(text) < 15:
                continue
            keywords = sorted(tokenize_ko(text))[:80]
            qid = f"{m['meeting_code']}-{r['id']}"
            rec = {
                'question_id': qid, 'meeting_code': m['meeting_code'], 'remark_id': r['id'],
                'remark_order': r['remark_order'], 'speaker': r['speaker'],
                'ministry': infer_ministry(text), 'question_type': question_type(text),
                'text': text, 'keywords': set(keywords),
            }
            questions.append(rec)
            out.execute('''insert or replace into presidential_question_candidates
              values (?,?,?,?,?,?,?,?,?)''', (
                qid, m['meeting_code'], r['id'], r['remark_order'], r['speaker'], rec['ministry'],
                rec['question_type'], text, json.dumps(keywords, ensure_ascii=False)
            ))
            q_count += 1

        meeting_queries = list(queries)
        if args.daily_date_queries:
            date_days = args.date_query_days or args.window_days
            date_start = max(ws, mdate - dt.timedelta(days=date_days))
            day_count = (we - date_start).days + 1
            for i in range(day_count):
                day = date_start + dt.timedelta(days=i)
                meeting_queries.extend([f"{day:%Y.%m.%d} {q}" for q in queries])
        # preserve order while removing duplicates
        meeting_queries = list(dict.fromkeys(meeting_queries))

        for query in meeting_queries:
            try:
                items = naver_search(query, ws, we, args.display, args.pause, args.max_pages)
            except Exception as e:
                print(f"WARN search failed {m['meeting_code']} {query}: {e}")
                continue
            for it in items:
                key = (m['meeting_code'], it['news_id'])
                if key in news_seen:
                    continue
                news_seen.add(key)
                nkw = sorted(tokenize_ko(it['title'] + ' ' + it['description']))[:80]
                out.execute('''insert or replace into pre_meeting_news
                  values (?,?,?,?,?,?,?,?,?,?,?,?)''', (
                    it['news_id'], m['meeting_code'], ws.isoformat(), we.isoformat(), it['query'], it['rank'],
                    it['pub_date'], it['title'], it['description'], it['link'], it['originallink'],
                    json.dumps(nkw, ensure_ascii=False)
                ))
                n_count += 1
                nset = set(nkw)
                for q in questions:
                    shared = sorted(nset & q['keywords'])
                    ministry_bonus = 0.2 if q['ministry'] and q['ministry'] in (it['title'] + it['description'] + it['query']) else 0
                    score = len(shared) / 8 + ministry_bonus
                    if score >= 0.35 and len(shared) >= 3:
                        lid = hashlib.sha1((m['meeting_code'] + it['news_id'] + q['question_id']).encode()).hexdigest()[:16]
                        out.execute('''insert or replace into issue_question_links values (?,?,?,?,?,?,?)''', (
                            lid, m['meeting_code'], it['news_id'], q['question_id'], round(score, 3),
                            json.dumps(shared[:20], ensure_ascii=False),
                            'keyword overlap + optional ministry bonus'
                        ))
                        l_count += 1
        out.commit()
        print(f"{m['meeting_date']} #{m['meeting_no']}: questions={len(questions)} news_total={n_count} links_total={l_count}", flush=True)

    out.execute('insert or replace into run_meta values (?,?)', ('built_at', dt.datetime.now().isoformat()))
    out.execute('insert or replace into run_meta values (?,?)', ('source_db', str(args.source_db)))
    out.execute('insert or replace into run_meta values (?,?)', ('queries', json.dumps(queries, ensure_ascii=False)))
    out.execute('insert or replace into run_meta values (?,?)', ('daily_date_queries', str(args.daily_date_queries)))
    out.commit()
    print(f"DONE out={args.out_db} meetings={len(meetings)} questions={q_count} news={n_count} links={l_count}", flush=True)

if __name__ == '__main__':
    main()
