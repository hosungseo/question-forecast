#!/usr/bin/env python3
"""Derive lightweight historical question priors from cabinet remarks DB.

The source labels are coarse, so this builds usable priors by mapping historical
question_type + text cues to synthesis moves. Output is a JSON file consumed by
question_patterns.py when present.
"""
from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / 'data' / 'cabinet_question_radar.sqlite'
OUT = ROOT / 'data' / 'historical_question_priors.json'

TYPE_TO_MOVES = {
    '현황 질문': ['ground_truth'],
    '대안 요구': ['instruction', 'public_outcome'],
    '예산/재정 확인': ['bottleneck', 'public_outcome'],
    '검토결과 확인': ['ground_truth', 'causal_split'],
    '부처협의 확인': ['coordination'],
    '관리 지시': ['instruction', 'coordination'],
}

CUE_TO_MOVES = [
    (re.compile(r'예산|재정|추경|비용|돈|지원금|재원'), ['bottleneck', 'public_outcome']),
    (re.compile(r'협의|관계\s*부처|의견|조정|같이|공동'), ['coordination']),
    (re.compile(r'검토|확인|현황|자료|통계|수치|지표|실제'), ['ground_truth']),
    (re.compile(r'원인|이유|왜|구조|문제'), ['causal_split']),
    (re.compile(r'현장|공무원|교사|지자체|책임|부담|안전'), ['field_burden']),
    (re.compile(r'국민|체감|민생|소상공인|취약|피해|환자|학생'), ['public_outcome']),
    (re.compile(r'바람|챙겨|점검|준비|대책|방안|해야|하라'), ['instruction']),
]

MINISTRY_HINTS = {
    '교육부': re.compile(r'교육|교사|학생|학교|대학|의대|수학여행|현장체험'),
    '행정안전부': re.compile(r'재난|안전|지자체|지방|행안부|소방|산불|침수'),
    '기획재정부': re.compile(r'예산|재정|추경|물가|경제|세제|지원금'),
    '국토교통부': re.compile(r'주택|부동산|전세|공급|건설|교통|도로'),
    '금융위원회': re.compile(r'금융|대출|금리|은행|채무|서민금융'),
    '고용노동부': re.compile(r'노동|산재|임금|일자리|고용|하도급|원청'),
    '법무부': re.compile(r'법무|검찰|수사|범죄|재판|형사|증거'),
    '보건복지부': re.compile(r'의료|복지|환자|전공의|병원|건강|의대'),
}


def text_moves(text: str, qtype: str | None) -> Counter:
    c = Counter()
    for m in TYPE_TO_MOVES.get(qtype or '', []):
        c[m] += 2
    for rx, moves in CUE_TO_MOVES:
        if rx.search(text or ''):
            for m in moves:
                c[m] += 1
    return c


def normalize(counter: Counter) -> dict[str, float]:
    if not counter:
        return {}
    total = sum(counter.values())
    return {k: round(v / total, 4) for k, v in counter.most_common()}


def main() -> int:
    if not DB.exists():
        raise SystemExit(f'Missing DB: {DB}')
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = con.execute('select question_type, text from presidential_question_candidates').fetchall()
    global_c = Counter()
    ministry_c = defaultdict(Counter)
    type_counts = Counter()
    for r in rows:
        text = r['text'] or ''
        qtype = r['question_type'] or ''
        type_counts[qtype] += 1
        moves = text_moves(text, qtype)
        global_c.update(moves)
        for ministry, rx in MINISTRY_HINTS.items():
            if rx.search(text):
                ministry_c[ministry].update(moves)
    data = {
        'source': str(DB),
        'total_candidates': len(rows),
        'question_type_counts': dict(type_counts.most_common()),
        'global_move_prior': normalize(global_c),
        'ministry_move_prior': {k: normalize(v) for k, v in sorted(ministry_c.items())},
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(OUT)
    print(json.dumps(data['global_move_prior'], ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
