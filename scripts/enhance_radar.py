#!/usr/bin/env python3
"""Enhance Question Forecast radar packets.

Adds:
- ministry work dictionary alignment
- cabinet-question likelihood score
- similar historical cases
- question flow / follow-up scenario
- daily delta vs previous radar snapshot
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from historical_retrieval import similar_cases

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
RADAR = DATA / 'next_meeting_radar.json'
PREV = DATA / 'previous_next_meeting_radar.json'
DICT = DATA / 'ministry_work_dictionary.json'
STATS = DATA / 'issue_stat_dictionary.json'
OUT = DATA / 'next_meeting_radar_enhanced.json'


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def work_alignment(packet: dict, dictionary: dict) -> dict:
    ministry = packet.get('ministry')
    info = (dictionary.get('ministries') or {}).get(ministry, {})
    text = ' '.join(packet.get('signals', []) + packet.get('terms', []))
    domains = []
    for d in info.get('function_domains', []):
        if any(part and part in text for part in re.findall(r'[가-힣A-Za-z0-9]+', d)):
            domains.append(d)
    if not domains:
        # fallback: choose first two domains as likely work anchors for this issue.
        domains = info.get('function_domains', [])[:2]
    matched_signals = [s for s in info.get('work_signals', []) if s in text]
    return {
        'function_domains': domains,
        'matched_work_signals': matched_signals,
        'accountability_questions': info.get('accountability_questions', []),
        'source_hooks': info.get('org_decree_queries', []),
    }


def likelihood(packet: dict, align: dict) -> dict:
    priority = float(packet.get('priority') or 0)
    count = float(packet.get('count') or 0)
    signal_count = len(packet.get('signals') or [])
    work_hits = len(align.get('matched_work_signals') or [])
    synthesis = packet.get('question_synthesis') or {}
    moves = synthesis.get('moves') or []
    high_value_moves = {'bottleneck', 'coordination', 'field_burden', 'public_outcome', 'instruction'}
    move_score = sum(1 for m in moves if m in high_value_moves)
    raw = 0
    raw += min(priority / 420, 1) * 30
    raw += min(count / 35, 1) * 16
    raw += min(signal_count / 8, 1) * 14
    raw += min(work_hits / 4, 1) * 15
    raw += min(move_score / 4, 1) * 20
    raw += 5 if align.get('function_domains') else 0
    score = round(min(100, raw), 1)
    if score >= 78: band = 'cabinet_high'
    elif score >= 60: band = 'cabinet_review'
    elif score >= 42: band = 'monitor'
    else: band = 'low'
    return {'score': score, 'band': band, 'drivers': {'priority': priority, 'article_count': count, 'signal_count': signal_count, 'work_signal_hits': work_hits, 'question_move_hits': move_score}}


def stat_evidence(packet: dict, stats_dict: dict) -> dict:
    issue_id = packet.get('issue_id')
    candidates = (stats_dict.get('issue_stats') or {}).get(issue_id, [])
    smoke = stats_dict.get('kosis_live_smoke') or []
    live_ok = [s for s in smoke if s.get('ok')]
    live_errors = [s.get('error') for s in smoke if not s.get('ok') and s.get('error')]
    evidence_cards = []
    for c in candidates[:3]:
        evidence_cards.append({
            'stat': c.get('label','관련 통계'),
            'use_in_answer': c.get('why','실제 추세 확인'),
            'how_to_phrase': '통계명 자체를 질문에 넣지 말고, 답변에서 규모·추세·비교 근거로 사용',
            'query_hint': c.get('query_hint',''),
        })
    answer_frame = '최신 통계로 규모·추세·대상집단을 확인한 뒤, 즉시 조치와 제도 개선을 구분해 답변해야 합니다.'
    if issue_id == 'prices_livelihood':
        answer_frame = '물가 부담은 체감 품목과 취약계층을 통계로 확인해, 지원 필요성과 재정수단 선택의 근거로 써야 합니다.'
    elif issue_id == 'school_field_trip':
        answer_frame = '체험학습 축소의 정책 대상 규모와 안전사고·교권 부담 근거를 통계로 받쳐, 면책·보험·안전요원 설계를 설명해야 합니다.'
    elif issue_id == 'disaster_safety':
        answer_frame = '재난 보도가 실제 위험 증가인지 제도보완 국면인지 통계로 구분해, 현장 통제와 국민 안내 대책의 필요성을 설명해야 합니다.'
    return {
        'candidates': candidates,
        'answer_evidence_cards': evidence_cards[:4],
        'answer_frame': answer_frame,
        'live_reference_cards': live_ok[:2],
        'live_status': 'ok' if live_ok else 'blocked_or_unavailable',
        'live_errors': sorted(set(live_errors))[:3],
        'ground_truth_prompt': '통계는 대통령 질문 문구가 아니라 장관 답변의 근거로 사용합니다.' if candidates else '연결된 통계 후보가 아직 없습니다.',
    }


def oral_brief(packet: dict, align: dict, like: dict) -> dict:
    ministry = packet.get('ministry')
    issue_id = packet.get('issue_id')
    synth = packet.get('question_synthesis') or {}
    stat = packet.get('statistical_evidence') or {}
    q = (synth.get('questions') or [{}])[0].get('question','')
    work = ', '.join((align.get('function_domains') or [])[:2])
    evidence = ', '.join(c.get('stat','') for c in (stat.get('answer_evidence_cards') or [])[:2])
    score = like.get('score')
    return {
        'thirty_second': f"{ministry} 소관 {issue_id}는 질문 가능성 {score}점입니다. 핵심은 {work or '소관 업무'}와 연결된 현장 부담·병목을 어떻게 풀 것인지이며, 답변은 {evidence or '관련 통계'}로 규모와 추세를 뒷받침해야 합니다.",
        'answer_skeleton': [
            '현재 상황: 기사 신호가 실제 현장 문제인지 규모와 추세로 확인',
            '원인 구분: 제도 문제, 현장 관행, 예산·인력 병목을 분리',
            '조치 계획: 즉시 조치와 법령·예산이 필요한 과제를 구분',
            '후속 보고: 점검 일정과 책임 부처·기관을 명확히 제시',
        ],
        'likely_first_question': q,
        'evidence_gap': '실제 live 통계값이 없는 항목은 최신값·전년 대비·지역/계층별 비교를 보강해야 합니다.'
    }


def question_flow(packet: dict, align: dict, like: dict) -> list[dict]:
    synth = packet.get('question_synthesis') or {}
    qs = synth.get('questions') or []
    first = qs[0]['question'] if qs else f"{packet.get('issue_id')}의 실제 현황은 무엇입니까?"
    second = qs[1]['question'] if len(qs) > 1 else '원인과 책임 소재를 어떻게 구분했습니까?'
    third = qs[2]['question'] if len(qs) > 2 else '예산·인력·법령 중 병목은 무엇입니까?'
    prep = []
    prep.extend(align.get('accountability_questions') or [])
    prep.append('최근 7일 기사량·대표기사·부처 소관 근거')
    if packet.get('statistical_evidence', {}).get('candidates'):
        prep.append('관련 통계 최신값과 전월·전년 대비 변화')
    prep.append('즉시 조치/법령개정/예산소요를 구분한 답변')
    return [
        {'stage': '첫 질문', 'question': first},
        {'stage': '후속 압박', 'question': second},
        {'stage': '병목 확인', 'question': third},
        {'stage': '지시 전환', 'question': synth.get('follow_up') or '이번 주 안에 보완해 다시 보고할 항목은 무엇입니까?'},
        {'stage': '장관 준비', 'items': prep[:5], 'likelihood_band': like['band']},
    ]


def delta(packet: dict, prev_by_issue: dict) -> dict:
    prev = prev_by_issue.get(packet.get('issue_id'))
    if not prev:
        return {'status': 'new_or_unseen', 'priority_change': None, 'rank_change': None, 'interpretation': '이전 스냅샷에 없던 이슈이거나 비교 기준이 없습니다.'}
    pc = (packet.get('priority') or 0) - (prev.get('priority') or 0)
    rc = (packet.get('rank') or 0) - (prev.get('rank') or 0)
    old_moves = set(((prev.get('question_synthesis') or {}).get('moves')) or [])
    new_moves = set(((packet.get('question_synthesis') or {}).get('moves')) or [])
    if pc > 30: interp = '기사 신호와 정책 관련성이 빠르게 커졌습니다.'
    elif pc < -30: interp = '이슈 강도가 낮아지고 있습니다.'
    elif old_moves != new_moves: interp = '순위보다 질문 프레임이 바뀐 이슈입니다.'
    else: interp = '전일 대비 큰 변화는 없습니다.'
    return {'status': 'compared', 'priority_change': pc, 'rank_change': rc, 'move_change': {'from': sorted(old_moves), 'to': sorted(new_moves)}, 'interpretation': interp}


def main() -> int:
    radar = load_json(RADAR, {})
    dictionary = load_json(DICT, {'ministries': {}})
    stats_dict = load_json(STATS, {'issue_stats': {}})
    prev = load_json(PREV, {})
    prev_packets = prev.get('packets') or []
    prev_by_issue = {p.get('issue_id'): {**p, 'rank': i + 1} for i, p in enumerate(prev_packets)}
    packets = radar.get('packets') or []
    enhanced = []
    for i, p in enumerate(packets, 1):
        p = dict(p)
        p['rank'] = i
        align = work_alignment(p, dictionary)
        like = likelihood(p, align)
        p['ministry_work_alignment'] = align
        p['cabinet_question_likelihood'] = like
        p['statistical_evidence'] = stat_evidence(p, stats_dict)
        p['similar_historical_cases'] = similar_cases(p)
        p['oral_brief'] = oral_brief(p, align, like)
        p['question_flow'] = question_flow(p, align, like)
        p['daily_delta'] = delta(p, prev_by_issue)
        enhanced.append(p)
    radar['packets'] = enhanced
    radar['enhancement_note'] = 'v4: ministry work dictionary + cabinet likelihood + hybrid historical retrieval + similar cases + question flow + daily delta'
    OUT.write_text(json.dumps(radar, ensure_ascii=False, indent=2))
    # Also replace base JSON so docs/briefing can use enhanced fields if desired.
    RADAR.write_text(json.dumps(radar, ensure_ascii=False, indent=2))
    print(OUT)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
