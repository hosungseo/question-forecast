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

ISSUE_FOCUS = {
    'school_field_trip': {
        'subject': '현장체험학습·소풍 축소 문제',
        'actors': '교사·학교장·교육청·학부모',
        'bottlenecks': ['교사 형사책임', '안전요원', '보험·공제', '법령상 면책 범위'],
        'public': '학생의 교육기회 격차와 학부모 불안',
        'risk': '현장 회피가 교육기회 축소로 굳어지는 것',
        'owner': '교육부',
    },
    'disaster_safety': {
        'subject': '재난·안전 대응 이슈',
        'actors': '행안부·지자체·경찰·소방·도로관리청',
        'bottlenecks': ['실시간 통제정보', '현장 대응 인력', '지자체 역량', '예산'],
        'public': '위험지역 회피와 재난정보 체감도',
        'risk': '사후 수습은 반복되지만 사전 통제가 늦어지는 것',
        'owner': '행안부',
    },
    'real_estate': {
        'subject': '부동산 공급·전월세 불안',
        'actors': '국토부·지자체·LH·금융당국',
        'bottlenecks': ['인허가', '착공·입주 시차', '금융', '정비사업 절차'],
        'public': '실수요자 주거비 부담과 입주 가능 물량',
        'risk': '공급 발표와 실제 입주 사이의 시차가 시장 불안으로 이어지는 것',
        'owner': '국토부',
    },
    'prices_livelihood': {
        'subject': '물가·민생 부담',
        'actors': '기재부·관계부처·지자체',
        'bottlenecks': ['예산', '집행 속도', '지원대상 선별', '물가 전가 구조'],
        'public': '취약계층과 자영업자의 체감 부담',
        'risk': '지원은 나가지만 체감 물가가 내려가지 않는 것',
        'owner': '기재부',
    },
    'finance_rates': {
        'subject': '금리·대출 부담',
        'actors': '금융위·금감원·은행권·서민금융기관',
        'bottlenecks': ['중금리대출 공급', '리스크 관리', '취약차주 지원 재원'],
        'public': '실수요자·취약차주의 상환 부담',
        'risk': '정책금융이 필요한 사람보다 안전한 차주에게만 흐르는 것',
        'owner': '금융위',
    },
    'labor_jobs': {
        'subject': '일자리·산재·임금체불 문제',
        'actors': '고용노동부·원청·하청·지자체',
        'bottlenecks': ['원청 책임', '감독 인력', '처벌 실효성', '하도급 구조'],
        'public': '노동자 안전과 임금 지급 체감도',
        'risk': '책임 소재가 하청·현장 노동자에게만 내려가는 것',
        'owner': '고용노동부',
    },
    'justice_reform': {
        'subject': '범죄 대응·수사·검찰개혁 이슈',
        'actors': '법무부·검찰·경찰·외교부·재판기관',
        'bottlenecks': ['증거보전', '수사권 조정', '국제공조', '재판 가능성'],
        'public': '피해자 보호와 형사사법 신뢰',
        'risk': '기관 논쟁은 커지지만 피해자 보호와 재판 가능성이 흐려지는 것',
        'owner': '법무부',
    },
    'medical': {
        'subject': '의료 공백·전공의·비상진료 문제',
        'actors': '복지부·병원·전공의·지자체·교육부',
        'bottlenecks': ['의료인력', '병원 재정', '교육·수련', '비상진료 체계'],
        'public': '환자 불편과 지역 의료 접근성',
        'risk': '비상진료가 장기화되며 지역·필수의료 공백이 굳어지는 것',
        'owner': '복지부',
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


def _focus(issue_id: str) -> dict:
    return ISSUE_FOCUS.get(issue_id, {
        'subject': '해당 이슈',
        'actors': '담당 부처와 관계기관',
        'bottlenecks': ['예산', '인력', '법령', '집행체계'],
        'public': '국민 체감도',
        'risk': '문제가 반복되는 것',
        'owner': '담당 부처',
    })


def _score_moves(issue_id: str, signals: list[str] | None, priority: int | float = 0, count: int = 0) -> list[str]:
    scores = {k: v for k, v in MOVE_WEIGHTS.items()}
    for i, move in enumerate(ISSUE_PRIOR_MOVES.get(issue_id, [])):
        scores[move] = scores.get(move, 0) + 1.2 - i * 0.12
    for sig in signals or []:
        for move in SIGNAL_TO_MOVES.get(sig, []):
            scores[move] = scores.get(move, 0) + 0.7
    if priority >= 300 or count >= 25:
        scores['instruction'] += 0.5
        scores['coordination'] += 0.3
    ordered = sorted(scores, key=lambda m: scores[m], reverse=True)
    # Cabinet-style packets should be compact. Keep strongest 4 moves, always include public outcome.
    keep = ordered[:4]
    if 'public_outcome' not in keep:
        keep[-1] = 'public_outcome'
    return keep


def _sentence(move: str, f: dict, signals: list[str] | None) -> str:
    sig = ', '.join((signals or [])[:4])
    subject = f['subject']; actors = f['actors']; bottlenecks = ', '.join(f['bottlenecks']); public = f['public']; risk = f['risk']
    if move == 'ground_truth':
        return f"{subject}은 기사상 신호({sig})보다 실제 현장 지표가 중요합니다. 현재 규모·추세·피해 범위를 어느 자료로 확인했습니까?"
    if move == 'causal_split':
        return f"이 사안을 단순 사건으로 볼 것인지 구조 문제로 볼 것인지 먼저 갈라야 합니다. 원인을 제도·현장 관행·이해관계자 부담으로 나누면 무엇이 핵심입니까?"
    if move == 'coordination':
        return f"{actors}가 각각 무엇을 맡는지 불분명하면 대책이 흩어집니다. 협의가 끝난 쟁점과 아직 조정이 필요한 쟁점은 무엇입니까?"
    if move == 'bottleneck':
        return f"해결을 막는 병목이 {bottlenecks} 중 어디에 있습니까? 바로 조치할 것과 법령·예산이 필요한 것을 구분해 보고했습니까?"
    if move == 'field_burden':
        return f"현장에 책임만 내려보내는 방식이면 다시 회피가 생깁니다. 현장 담당자에게 권한·보호장치·자원을 같이 주는 설계가 있습니까?"
    if move == 'public_outcome':
        return f"결국 국민이 체감할 변화가 있어야 합니다. {public}을 언제까지 어떤 지표로 개선하겠다고 설명할 수 있습니까?"
    if move == 'instruction':
        return f"{risk}을 막기 위해 {f['owner']}가 이번 주 안에 점검·보완해서 다시 보고할 항목은 무엇입니까?"
    return f"{subject}에 대해 추가 검토가 필요한 쟁점은 무엇입니까?"


def synthesize_questions(issue_id: str, signals: list[str] | None = None, *, priority: int | float = 0, count: int = 0) -> dict:
    """Return a compact, weighted question packet.

    Output fields are intentionally report-friendly and JSON-stable.
    """
    f = _focus(issue_id)
    moves = _score_moves(issue_id, signals, priority, count)
    questions = [{'move': m, 'question': _sentence(m, f, signals)} for m in moves]
    diagnosis = f"{f['subject']}은 '{f['risk']}'이 핵심 리스크입니다. 따라서 질문은 사실확인보다 책임·병목·체감성과를 함께 묶어야 합니다."
    follow_up = _sentence('instruction', f, signals)
    return {
        'diagnosis': diagnosis,
        'moves': moves,
        'questions': questions,
        'follow_up': follow_up,
    }

# Backward-compatible alias used by older generated JSON readers.
def pattern_questions(issue_id: str, signals: list[str] | None = None) -> list[dict[str, str]]:
    packet = synthesize_questions(issue_id, signals)
    return [{'pattern': q['move'], 'question': q['question']} for q in packet['questions']]
