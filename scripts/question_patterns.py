#!/usr/bin/env python3
"""Reusable presidential question pattern layer.

The pattern is derived from historical cabinet-meeting question candidates:
현황 → 원인분해 → 협의 → 병목(예산/인력/법령) → 현장책임 → 국민체감.
"""
from __future__ import annotations

PATTERN_LABELS = [
    '현황',
    '원인분해',
    '부처협의',
    '병목',
    '현장책임',
    '국민체감',
]

ISSUE_FOCUS = {
    'school_field_trip': {
        'subject': '현장체험학습·소풍 축소 문제',
        'actors': '교사·학교장·교육청·학부모',
        'bottleneck': '교사 형사책임, 안전요원, 보험·공제, 법령상 면책 범위',
        'public': '학생의 교육기회 격차와 학부모 불안',
    },
    'disaster_safety': {
        'subject': '재난·안전 대응 이슈',
        'actors': '행안부·지자체·경찰·소방·도로관리청',
        'bottleneck': '실시간 통제정보, 현장 대응 인력, 지자체 역량, 예산',
        'public': '위험지역 회피와 재난정보 체감도',
    },
    'real_estate': {
        'subject': '부동산 공급·전월세 불안',
        'actors': '국토부·지자체·LH·금융당국',
        'bottleneck': '인허가, 착공·입주 시차, 금융, 정비사업 절차',
        'public': '실수요자 주거비 부담과 입주 가능 물량',
    },
    'prices_livelihood': {
        'subject': '물가·민생 부담',
        'actors': '기재부·관계부처·지자체',
        'bottleneck': '예산, 집행 속도, 지원대상 선별, 물가 전가 구조',
        'public': '취약계층과 자영업자의 체감 부담',
    },
    'finance_rates': {
        'subject': '금리·대출 부담',
        'actors': '금융위·금감원·은행권·서민금융기관',
        'bottleneck': '중금리대출 공급, 리스크 관리, 취약차주 지원 재원',
        'public': '실수요자·취약차주의 상환 부담',
    },
    'labor_jobs': {
        'subject': '일자리·산재·임금체불 문제',
        'actors': '고용노동부·원청·하청·지자체',
        'bottleneck': '원청 책임, 감독 인력, 처벌 실효성, 하도급 구조',
        'public': '노동자 안전과 임금 지급 체감도',
    },
    'justice_reform': {
        'subject': '범죄 대응·수사·검찰개혁 이슈',
        'actors': '법무부·검찰·경찰·외교부·재판기관',
        'bottleneck': '증거보전, 수사권 조정, 국제공조, 재판 가능성',
        'public': '피해자 보호와 형사사법 신뢰',
    },
    'medical': {
        'subject': '의료 공백·전공의·비상진료 문제',
        'actors': '복지부·병원·전공의·지자체·교육부',
        'bottleneck': '의료인력, 병원 재정, 교육·수련, 비상진료 체계',
        'public': '환자 불편과 지역 의료 접근성',
    },
}


def pattern_questions(issue_id: str, signals: list[str] | None = None) -> list[dict[str, str]]:
    f = ISSUE_FOCUS.get(issue_id, {
        'subject': '해당 이슈',
        'actors': '담당 부처와 관계기관',
        'bottleneck': '예산·인력·법령·집행체계',
        'public': '국민 체감도',
    })
    sig = ', '.join((signals or [])[:5])
    suffix = f' 최근 신호({sig})를 기준으로' if sig else ''
    return [
        {'pattern': '현황', 'question': f"{f['subject']}의 실제 현황은 무엇이며,{suffix} 어느 지표로 확인했는가?"},
        {'pattern': '원인분해', 'question': f"이 문제가 일시적 사건인지 구조적 문제인지, 원인을 어떻게 나누어 보고했는가?"},
        {'pattern': '부처협의', 'question': f"{f['actors']} 사이 역할 분담과 협의는 어디까지 끝났고, 누가 최종 조정하는가?"},
        {'pattern': '병목', 'question': f"해결의 병목이 {f['bottleneck']} 중 무엇인지, 바로 풀 수 있는 것과 시간이 필요한 것을 구분했는가?"},
        {'pattern': '현장책임', 'question': f"현장 담당자나 집행기관에 책임만 전가되는 구조는 아닌지, 필요한 권한·예산·보호장치는 같이 설계했는가?"},
        {'pattern': '국민체감', 'question': f"국민이 체감할 변화는 무엇이며, {f['public']}을 언제 어떤 방식으로 개선할 수 있는가?"},
    ]


def compact_pattern_summary(issue_id: str, signals: list[str] | None = None) -> list[str]:
    return [q['question'] for q in pattern_questions(issue_id, signals)]
