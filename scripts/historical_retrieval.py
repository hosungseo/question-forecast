#!/usr/bin/env python3
"""Hybrid historical question retrieval for Question Forecast.

This is a small, dependency-free RAG-style layer inspired by the LightRAG idea:
keep retrieval transparent and explainable, but improve beyond exact token overlap.

Signals used:
- lexical token cosine: precise Korean/English keyword overlap
- character trigram cosine: fuzzy semantic-ish overlap for inflected Korean phrases
- ministry hint boost: questions from the same likely policy domain rank higher
- move hint boost: retrieved question type/text should match selected question moves

The output is intentionally report-friendly: every score includes component weights
so reviewers can see why a historical case was attached.
"""
from __future__ import annotations

import json
import math
import re
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / 'data' / 'cabinet_question_radar.sqlite'
PRIORS_PATH = ROOT / 'data' / 'historical_question_priors.json'

STOP = set('관련 대한 하는 되는 있는 없는 정부 대통령 장관 기자 오늘 이번 뉴스 종합 단독 그리고 그러나 이를 통해 우리 해당 문제 이슈'.split())

MINISTRY_HINTS = {
    '교육부': re.compile(r'교육|교사|학생|학교|대학|의대|수학여행|현장체험'),
    '행정안전부': re.compile(r'재난|안전|지자체|지방|행안부|소방|산불|침수|재난문자'),
    '기획재정부': re.compile(r'예산|재정|추경|물가|경제|세제|지원금|민생'),
    '국토교통부': re.compile(r'주택|부동산|전세|월세|공급|건설|교통|도로'),
    '금융위원회': re.compile(r'금융|대출|금리|은행|채무|서민금융'),
    '고용노동부': re.compile(r'노동|산재|임금|일자리|고용|하도급|원청'),
    '법무부': re.compile(r'법무|검찰|수사|범죄|재판|형사|증거'),
    '보건복지부': re.compile(r'의료|복지|환자|전공의|병원|건강|의대'),
}

MOVE_CUES = {
    'ground_truth': re.compile(r'검토|확인|현황|자료|통계|수치|지표|실제|파악'),
    'causal_split': re.compile(r'원인|이유|왜|구조|문제|책임'),
    'coordination': re.compile(r'협의|관계\s*부처|조정|공동|역할|기관'),
    'bottleneck': re.compile(r'예산|재정|인력|법령|절차|병목|재원|비용'),
    'field_burden': re.compile(r'현장|공무원|교사|지자체|부담|안전|책임'),
    'public_outcome': re.compile(r'국민|체감|민생|소상공인|취약|피해|환자|학생|불편'),
    'instruction': re.compile(r'챙겨|점검|준비|대책|방안|해야|하라|보고'),
}


def tokens(text: str) -> Counter:
    return Counter(t for t in re.findall(r'[가-힣A-Za-z0-9]{2,}', text or '') if t not in STOP)


def chargrams(text: str, n: int = 3) -> Counter:
    compact = re.sub(r'\s+', '', text or '')
    if len(compact) < n:
        return Counter([compact]) if compact else Counter()
    return Counter(compact[i:i+n] for i in range(len(compact)-n+1))


def cosine(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    inter = set(a) & set(b)
    dot = sum(a[k] * b[k] for k in inter)
    na = math.sqrt(sum(v*v for v in a.values()))
    nb = math.sqrt(sum(v*v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def infer_ministry(text: str) -> str | None:
    for ministry, rx in MINISTRY_HINTS.items():
        if rx.search(text or ''):
            return ministry
    return None


def move_match(text: str, moves: Iterable[str]) -> float:
    moves = list(moves or [])
    if not moves:
        return 0.0
    hits = sum(1 for m in moves if MOVE_CUES.get(m) and MOVE_CUES[m].search(text or ''))
    return hits / max(len(moves), 1)


def rows() -> list[sqlite3.Row]:
    if not DB.exists():
        return []
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con.execute('''
        select m.meeting_date as meeting_date, q.meeting_code as meeting_code,
               q.question_type as question_type, q.text as text
        from presidential_question_candidates q
        left join meetings m on m.meeting_code = q.meeting_code
    ''').fetchall()


def similar_cases(packet: dict, limit: int = 3) -> list[dict]:
    query_text = ' '.join((packet.get('signals') or []) + (packet.get('terms') or []))
    synth = packet.get('question_synthesis') or {}
    moves = synth.get('moves') or []
    ministry = packet.get('ministry') or infer_ministry(query_text)
    qtoks = tokens(query_text)
    qgrams = chargrams(query_text)
    if not qtoks and not qgrams:
        return []

    scored = []
    for r in rows():
        text = re.sub(r'\s+', ' ', r['text'] or '').strip()
        if not text:
            continue
        lexical = cosine(qtoks, tokens(text))
        fuzzy = cosine(qgrams, chargrams(text))
        row_ministry = infer_ministry(text)
        ministry_boost = 0.12 if ministry and row_ministry == ministry else 0.0
        move_boost = 0.12 * move_match(text + ' ' + (r['question_type'] or ''), moves)
        evidence = lexical + fuzzy
        # Domain/move boosts are tie-breakers, not standalone evidence.
        # Without this guard, a generic same-ministry instruction can outrank a
        # genuinely similar case just because it uses cabinet-like wording.
        if evidence < 0.018:
            continue
        score = lexical * 0.52 + fuzzy * 0.24 + ministry_boost + move_boost
        if score >= 0.045:
            scored.append((score, lexical, fuzzy, ministry_boost, move_boost, row_ministry, r, text))

    scored.sort(key=lambda x: x[0], reverse=True)
    out = []
    seen = set()
    for score, lexical, fuzzy, ministry_boost, move_boost, row_ministry, r, text in scored:
        key = text[:120]
        if key in seen:
            continue
        seen.add(key)
        out.append({
            'score': round(score, 4),
            'components': {
                'lexical': round(lexical, 4),
                'fuzzy_chargram': round(fuzzy, 4),
                'same_ministry_boost': round(ministry_boost, 4),
                'question_move_boost': round(move_boost, 4),
            },
            'retrieval_method': 'hybrid_token_chargram_ministry_move',
            'meeting_date': r['meeting_date'],
            'meeting_code': r['meeting_code'],
            'question_type': r['question_type'],
            'inferred_ministry': row_ministry,
            'excerpt': text[:300],
        })
        if len(out) >= limit:
            break
    return out


def main() -> int:
    sample = {'signals': ['재난', '안전', '침수'], 'terms': ['지자체', '현장'], 'ministry': '행정안전부', 'question_synthesis': {'moves': ['ground_truth', 'coordination', 'instruction']}}
    print(json.dumps(similar_cases(sample, 5), ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
