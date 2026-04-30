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

PRESIDENTIAL_STYLE = {
    'school_field_trip': [
        '소풍이나 수학여행도 수업의 일부인데, 안전사고가 걱정된다고 아예 안 가는 식으로 굳어지면 교육 기회를 줄이는 것 아닌지?',
        '현장에서는 교사가 책임질까 봐 못 움직이고, 학부모는 아이가 못 가서 불만이면 결국 제도 설계가 현장을 막고 있는 것 아닌지?',
        '교사에게 책임만 묻고 권한과 보호장치는 안 주면 학교가 당연히 몸을 사릴 텐데, 이 구조를 그대로 둘 것인지?',
        '아이들이 학교에 따라 어떤 곳은 가고 어떤 곳은 못 가면, 이것도 교육 격차가 되는 것 아닌지?'
    ],
    'disaster_safety': [
        '침수나 산불 같은 것은 일이 터진 뒤 수습하는 것보다, 국민이 미리 피하게 만드는 게 국가의 역할 아닌지?',
        '지자체가 현장을 제일 잘 안다고 하지만, 역량이 부족한 곳에서 사고가 반복되면 중앙정부가 그냥 지켜볼 수는 없는 것 아닌지?',
        '위험 정보가 있는데도 국민 휴대전화와 내비게이션까지 제때 가지 않으면, 시스템이 있어도 없는 것과 같은 것 아닌지?',
        '재난 때마다 매뉴얼은 있다고 하는데 현장에서 안 움직이면, 매뉴얼 문제가 아니라 책임 구조 문제 아닌지?'
    ],
    'real_estate': [
        '공급 대책을 발표해도 실제 입주까지 시간이 오래 걸리면, 국민 입장에서는 대책이 없는 것처럼 느끼는 것 아닌지?',
        '집값과 전월세 문제는 숫자보다 불안 심리가 먼저 움직이는데, 정부가 시장의 기대를 어떻게 잡을 것인지?',
        '수도권과 지방 문제가 전혀 다른데 하나의 처방으로 해결하려고 하면 효과가 떨어지는 것 아닌지?',
        '공급을 늘린다고 했는데 국민이 들어가 살 집으로 이어지지 않으면 결국 행정 절차만 돈 것 아닌지?'
    ],
    'prices_livelihood': [
        '국민은 평균 물가가 아니라 장바구니와 기름값으로 고통을 느끼는데, 정부 대책도 그 체감 지점에서 출발해야 하는 것 아닌지?',
        '지원은 했다고 하는데 실제 부담이 그대로면, 정책이 국민에게 도착하지 못한 것 아닌지?',
        '어려울 때 쓰려고 재정이라는 제도가 있는 것인데, 지금 무엇을 아끼고 무엇은 과감히 써야 하는지 정리해야 하는 것 아닌지?',
        '대책이 부처별로 흩어지면 국민은 아무도 책임지지 않는다고 느낄 텐데, 민생 대응의 중심을 어디에 둘 것인지?'
    ],
    'finance_rates': [
        '금융이 필요한 사람에게는 안 가고 안전한 사람에게만 가면, 정책금융이라는 이름이 무색한 것 아닌지?',
        '서민금융을 늘린다고 해도 실제로 부담이 줄지 않으면 은행권 관리만 한 것이지 국민을 도운 것은 아닌 것 아닌지?',
        '금융 지원이 투기 쪽으로 흐르지 않고 생산과 민생으로 가게 하는 장치가 핵심 아닌지?',
        '돈이 필요한 곳은 막히고 돈이 넘치는 곳에는 더 몰리면, 금융정책이 불평등을 키우는 것 아닌지?'
    ],
    'labor_jobs': [
        '현장에서 다치고 임금을 못 받는 사람이 계속 나오면, 숫자가 좋아도 국민은 좋아졌다고 느끼기 어려운 것 아닌지?',
        '원청은 이익을 가져가고 책임은 하청과 노동자에게 내려가면, 그 구조를 그냥 시장 문제라고 볼 수는 없는 것 아닌지?',
        '제재를 받아도 계속하는 게 이익이면, 제도가 오히려 위반을 허용하는 것 아닌지?',
        '일하는 사람이 제일 약한 고리로 남아 있으면, 정부가 말하는 노동 보호가 현장에서는 빈말이 되는 것 아닌지?'
    ],
    'justice_reform': [
        '기관 권한을 어떻게 나눌지가 아니라, 국민 입장에서 범죄 피해를 막고 재판까지 가게 하는 힘이 약해지면 안 되는 것 아닌지?',
        '수사체계를 고친다고 하면서 실제 범죄 대응력이 떨어지면, 제도개혁의 목적을 놓치는 것 아닌지?',
        '피해자 보호보다 기관 논쟁이 앞서면 국민은 국가가 누구 편인지 묻게 되는 것 아닌지?',
        '권한을 나누는 문제보다 나쁜 사람이 빠져나가지 못하게 하는 것이 먼저 아닌지?'
    ],
    'medical': [
        '의료 문제는 제도 논쟁도 중요하지만, 국민 입장에서는 지금 아플 때 치료받을 수 있느냐가 먼저 아닌지?',
        '비상진료가 오래가면 비상이 아니라 일상이 되는 것인데, 그렇게 두면 지역과 필수의료가 더 약해지는 것 아닌지?',
        '의료인력 문제를 서로 책임 공방으로만 끌고 가면 환자 불편은 누가 책임지는 것인지?',
        '지역에서는 병원을 찾아다니는 것 자체가 고통인데, 이걸 단순한 의료계 갈등으로만 볼 수는 없는 것 아닌지?'
    ],
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


def _persona_questions(issue_id: str, moves: list[str], scores: dict[str, float], signals: list[str] | None) -> list[dict]:
    style = PRESIDENTIAL_STYLE.get(issue_id, [])
    questions: list[dict] = []
    for i, text in enumerate(style):
        move = moves[i % len(moves)] if moves else 'ground_truth'
        questions.append({
            'move': move,
            'move_label': MOVE_KO.get(move, move),
            'question': text,
            'score': scores.get(move),
            'style': 'presidential_tail_wags_head',
        })
    # Add one generic macro follow-up if the issue-specific bank is short.
    if len(questions) < 4:
        for move in moves:
            questions.append({
                'move': move,
                'move_label': MOVE_KO.get(move, move),
                'question': _sentence(move, _focus(issue_id), signals),
                'score': scores.get(move),
                'style': 'macro_follow_up',
            })
            if len(questions) >= 4:
                break
    return questions[:5]


def synthesize_questions(issue_id: str, signals: list[str] | None = None, *, priority: int | float = 0, count: int = 0) -> dict:
    """Return a compact, weighted question packet.

    Output fields are intentionally report-friendly and JSON-stable.
    """
    f = _focus(issue_id)
    moves, scores = _score_moves(issue_id, signals, priority, count)
    questions = _persona_questions(issue_id, moves, scores, signals)
    top_move = moves[0] if moves else 'ground_truth'
    diagnosis = f"{f['subject']}의 핵심 리스크는 {f['risk']}입니다. 과거 국무회의 질문 패턴상 작은 사례에서 제도 전체의 허점을 묻는 방식으로, {MOVE_DIAGNOSIS.get(top_move, '핵심 쟁점을 정리해야 합니다')} ."
    diagnosis = diagnosis.replace(' .', '.')
    follow_up = _sentence('instruction', f, signals)
    return {
        'diagnosis': diagnosis,
        'moves': moves,
        'move_labels': [MOVE_KO.get(m, m) for m in moves],
        'move_scores': scores,
        'questions': questions,
        'follow_up': follow_up,
        'style_note': '과거 대통령 질문 데이터의 말맛을 반영해, 작은 사례로 제도 전체를 흔드는 tail-wags-head형 질문을 우선 생성합니다. 통계·법령은 질문 문구가 아니라 장관 답변 근거로 둡니다.',
    }

# Backward-compatible alias used by older generated JSON readers.
def pattern_questions(issue_id: str, signals: list[str] | None = None) -> list[dict[str, str]]:
    packet = synthesize_questions(issue_id, signals)
    return [{'pattern': q['move'], 'question': q['question']} for q in packet['questions']]
