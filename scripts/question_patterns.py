#!/usr/bin/env python3
"""Presidential question synthesis layer.

This is not a flat template. It turns issue signals into a small set of
question moves, using patterns observed in historical cabinet-meeting remarks:
- factual grounding
- causality and responsibility split
- coordination/accountability
- resource/legal bottleneck
- field burden
- public-facing outcome
- follow-up instruction

The synthesizer selects and orders these moves by issue type and current news
signals so each packet is compact and cabinet-like rather than a checklist.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRIORS_PATH = ROOT / 'data' / 'historical_question_priors.json'

ISSUE_FOCUS = {
    'school_field_trip': {
        'subject': '현장체험학습·소풍 축소 문제',
        'actors': '교사·학교장·교육청·학부모',
        'bottlenecks': ['교사 형사책임', '안전요원', '보험·공제', '법령상 면책 범위'],
        'public': '학생의 교육기회 격차와 학부모 불안',
        'risk': '현장 회피가 교육기회 축소로 굳어지는 것',
        'owner': '교육부',
        'ministry': '교육부',
    },
    'disaster_safety': {
        'subject': '재난·안전 대응 이슈',
        'actors': '행안부·지자체·경찰·소방·도로관리청',
        'bottlenecks': ['실시간 통제정보', '현장 대응 인력', '지자체 역량', '예산'],
        'public': '위험지역 회피와 재난정보 체감도',
        'risk': '사후 수습은 반복되지만 사전 통제가 늦어지는 것',
        'owner': '행안부',
        'ministry': '행정안전부',
    },
    'real_estate': {
        'subject': '부동산 공급·전월세 불안',
        'actors': '국토부·지자체·LH·금융당국',
        'bottlenecks': ['인허가', '착공·입주 시차', '금융', '정비사업 절차'],
        'public': '실수요자 주거비 부담과 입주 가능 물량',
        'risk': '공급 발표와 실제 입주 사이의 시차가 시장 불안으로 이어지는 것',
        'owner': '국토부',
        'ministry': '국토교통부',
    },
    'prices_livelihood': {
        'subject': '물가·민생 부담',
        'actors': '기재부·관계부처·지자체',
        'bottlenecks': ['예산', '집행 속도', '지원대상 선별', '물가 전가 구조'],
        'public': '취약계층과 자영업자의 체감 부담',
        'risk': '지원은 나가지만 체감 물가가 내려가지 않는 것',
        'owner': '기재부',
        'ministry': '기획재정부',
    },
    'finance_rates': {
        'subject': '금리·대출 부담',
        'actors': '금융위·금감원·은행권·서민금융기관',
        'bottlenecks': ['중금리대출 공급', '리스크 관리', '취약차주 지원 재원'],
        'public': '실수요자·취약차주의 상환 부담',
        'risk': '정책금융이 필요한 사람보다 안전한 차주에게만 흐르는 것',
        'owner': '금융위',
        'ministry': '금융위원회',
    },
    'labor_jobs': {
        'subject': '일자리·산재·임금체불 문제',
        'actors': '고용노동부·원청·하청·지자체',
        'bottlenecks': ['원청 책임', '감독 인력', '처벌 실효성', '하도급 구조'],
        'public': '노동자 안전과 임금 지급 체감도',
        'risk': '책임 소재가 하청·현장 노동자에게만 내려가는 것',
        'owner': '고용노동부',
        'ministry': '고용노동부',
    },
    'justice_reform': {
        'subject': '범죄 대응·수사·검찰개혁 이슈',
        'actors': '법무부·검찰·경찰·외교부·재판기관',
        'bottlenecks': ['증거보전', '수사권 조정', '국제공조', '재판 가능성'],
        'public': '피해자 보호와 형사사법 신뢰',
        'risk': '기관 논쟁은 커지지만 피해자 보호와 재판 가능성이 흐려지는 것',
        'owner': '법무부',
        'ministry': '법무부',
    },
    'medical': {
        'subject': '의료 공백·전공의·비상진료 문제',
        'actors': '복지부·병원·전공의·지자체·교육부',
        'bottlenecks': ['의료인력', '병원 재정', '교육·수련', '비상진료 체계'],
        'public': '환자 불편과 지역 의료 접근성',
        'risk': '비상진료가 장기화되며 지역·필수의료 공백이 굳어지는 것',
        'owner': '복지부',
        'ministry': '보건복지부',
    },
}

MOVE_WEIGHTS = {
    'ground_truth': 1.0,
    'causal_split': 1.0,
    'coordination': 0.8,
    'bottleneck': 0.9,
    'field_burden': 0.8,
    'public_outcome': 0.9,
    'instruction': 0.7,
}

SIGNAL_TO_MOVES = {
    '예산': ['bottleneck', 'public_outcome'],
    '추경': ['bottleneck', 'instruction'],
    '지원': ['public_outcome', 'bottleneck'],
    '책임': ['causal_split', 'field_burden'],
    '면책': ['field_burden', 'bottleneck'],
    '안전': ['ground_truth', 'coordination', 'instruction'],
    '재난': ['ground_truth', 'coordination', 'instruction'],
    '침수': ['ground_truth', 'coordination'],
    '산불': ['ground_truth', 'instruction'],
    '공급': ['ground_truth', 'bottleneck', 'public_outcome'],
    '전세': ['public_outcome', 'ground_truth'],
    '금리': ['ground_truth', 'public_outcome'],
    '대출': ['bottleneck', 'public_outcome'],
    '산재': ['field_burden', 'coordination'],
    '임금체불': ['field_burden', 'instruction'],
    '하도급': ['causal_split', 'field_burden'],
    '범죄': ['ground_truth', 'coordination'],
    '수사': ['coordination', 'bottleneck'],
    '증거': ['bottleneck', 'instruction'],
    '전공의': ['coordination', 'public_outcome'],
    '의료': ['ground_truth', 'public_outcome'],
}

ISSUE_PRIOR_MOVES = {
    'school_field_trip': ['causal_split', 'field_burden', 'bottleneck', 'public_outcome'],
    'disaster_safety': ['ground_truth', 'coordination', 'instruction', 'public_outcome'],
    'real_estate': ['ground_truth', 'bottleneck', 'public_outcome', 'coordination'],
    'prices_livelihood': ['ground_truth', 'bottleneck', 'public_outcome', 'instruction'],
    'finance_rates': ['ground_truth', 'bottleneck', 'public_outcome'],
    'labor_jobs': ['field_burden', 'causal_split', 'coordination', 'instruction'],
    'justice_reform': ['coordination', 'bottleneck', 'ground_truth', 'public_outcome'],
    'medical': ['ground_truth', 'coordination', 'public_outcome', 'bottleneck'],
}


def _load_priors() -> dict:
    if not PRIORS_PATH.exists():
        return {}
    try:
        return json.loads(PRIORS_PATH.read_text())
    except Exception:
        return {}


def _focus(issue_id: str) -> dict:
    return ISSUE_FOCUS.get(issue_id, {
        'subject': '해당 이슈',
        'actors': '담당 부처와 관계기관',
        'bottlenecks': ['예산', '인력', '법령', '집행체계'],
        'public': '국민 체감도',
        'risk': '문제가 반복되는 것',
        'owner': '담당 부처',
    })


def _score_moves(issue_id: str, signals: list[str] | None, priority: int | float = 0, count: int = 0) -> tuple[list[str], dict[str, float]]:
    f = _focus(issue_id)
    scores = {k: v for k, v in MOVE_WEIGHTS.items()}
    components = {k: 0.0 for k in MOVE_WEIGHTS}

    # 1) Issue prior: what this policy field normally asks.
    for i, move in enumerate(ISSUE_PRIOR_MOVES.get(issue_id, [])):
        boost = 1.2 - i * 0.12
        scores[move] = scores.get(move, 0) + boost
        components[move] = components.get(move, 0) + boost

    # 2) Current signal prior: what today's article terms imply.
    for sig in signals or []:
        for move in SIGNAL_TO_MOVES.get(sig, []):
            scores[move] = scores.get(move, 0) + 0.7
            components[move] = components.get(move, 0) + 0.7

    # 3) Historical prior: learned from extracted presidential question candidates.
    priors = _load_priors()
    ministry = f.get('ministry')
    hist = (priors.get('ministry_move_prior', {}) or {}).get(ministry) or priors.get('global_move_prior', {}) or {}
    for move, weight in hist.items():
        if move in scores:
            boost = float(weight) * 2.2
            scores[move] += boost
            components[move] = components.get(move, 0) + boost

    # 4) Salience: urgent/high-volume issues more often turn into instruction/coordination.
    if priority >= 300 or count >= 25:
        scores['instruction'] += 0.5
        scores['coordination'] += 0.3
        components['instruction'] += 0.5
        components['coordination'] += 0.3

    ordered = sorted(scores, key=lambda m: scores[m], reverse=True)
    # Cabinet-style packets should be compact. Keep strongest 4 moves, always include public outcome.
    keep = ordered[:4]
    if 'public_outcome' not in keep:
        keep[-1] = 'public_outcome'
    return keep, {k: round(scores[k], 3) for k in ordered}


def _sentence(move: str, f: dict, signals: list[str] | None) -> str:
    subject = f['subject']; actors = f['actors']; public = f['public']; risk = f['risk']
    # Presidential questions should stay macro-level: direction, responsibility,
    # coordination, public impact, and priority. Statistics/laws belong in the
    # minister's answer evidence layer, not in the literal question wording.
    if move == 'ground_truth':
        return f"이 사안이 일시적 보도 이슈가 아니라 국민 생활과 국정 운영에 영향을 주는 구조적 문제라면, 정부는 무엇을 우선순위로 보고 있습니까?"
    if move == 'causal_split':
        return f"이 사안을 개별 사건으로 볼 것인지, 제도와 현장의 구조 문제로 볼 것인지 정부의 판단은 무엇입니까?"
    if move == 'coordination':
        return f"{actors}의 책임과 역할이 흩어지지 않도록 정부 전체 차원에서 어떻게 조정하고 있습니까?"
    if move == 'bottleneck':
        return f"대책이 발표에 그치지 않고 실제 변화로 이어지려면 가장 먼저 풀어야 할 제도적·현장적 병목은 무엇입니까?"
    if move == 'field_burden':
        return f"현장에 책임만 내려가는 방식이 반복되지 않도록 정부가 권한과 보호장치를 어떻게 함께 설계하겠습니까?"
    if move == 'public_outcome':
        return f"국민이 실제 변화를 체감하려면 정부가 {public}과 관련해 어떤 변화를 약속해야 합니까?"
    if move == 'instruction':
        return f"{risk}을 막기 위해 {f['owner']}가 관계부처와 함께 우선 조치할 과제는 무엇입니까?"
    return f"{subject}에 대해 정부가 우선 정리해야 할 국정 쟁점은 무엇입니까?"


MOVE_KO = {
    'ground_truth': '국정 우선순위',
    'causal_split': '구조 판단',
    'coordination': '부처 간 조정',
    'bottleneck': '병목 해소',
    'field_burden': '현장 부담 완화',
    'public_outcome': '국민 체감 성과',
    'instruction': '후속 조치 지시',
}

MOVE_DIAGNOSIS = {
    'ground_truth': '국정 운영상 무엇을 우선순위로 둘지 분명히 해야 합니다',
    'causal_split': '개별 사건인지 구조 문제인지 정부 판단을 설명해야 합니다',
    'coordination': '관계 부처와 기관의 역할 분담을 명확히 해야 합니다',
    'bottleneck': '발표가 실제 변화로 이어지도록 병목을 설명해야 합니다',
    'field_burden': '현장에 책임만 전가되지 않도록 권한과 보호장치를 함께 제시해야 합니다',
    'public_outcome': '국민이 체감할 변화를 중심으로 답변을 준비해야 합니다',
    'instruction': '단기 점검과 후속 보고 일정을 분명히 해야 합니다',
}


def synthesize_questions(issue_id: str, signals: list[str] | None = None, *, priority: int | float = 0, count: int = 0) -> dict:
    """Return a compact, weighted question packet.

    Output fields are intentionally report-friendly and JSON-stable.
    """
    f = _focus(issue_id)
    moves, scores = _score_moves(issue_id, signals, priority, count)
    questions = [{'move': m, 'move_label': MOVE_KO.get(m, m), 'question': _sentence(m, f, signals), 'score': scores.get(m)} for m in moves]
    top_move = moves[0] if moves else 'ground_truth'
    diagnosis = f"{f['subject']}의 핵심 리스크는 {f['risk']}입니다. 오늘 보도 흐름과 과거 국무회의 질문 패턴을 함께 보면, {MOVE_DIAGNOSIS.get(top_move, '핵심 쟁점을 정리해야 합니다')} ."
    diagnosis = diagnosis.replace(' .', '.')
    follow_up = _sentence('instruction', f, signals)
    return {
        'diagnosis': diagnosis,
        'moves': moves,
        'move_labels': [MOVE_KO.get(m, m) for m in moves],
        'move_scores': scores,
        'questions': questions,
        'follow_up': follow_up,
    }

# Backward-compatible alias used by older generated JSON readers.
def pattern_questions(issue_id: str, signals: list[str] | None = None) -> list[dict[str, str]]:
    packet = synthesize_questions(issue_id, signals)
    return [{'pattern': q['move'], 'question': q['question']} for q in packet['questions']]
