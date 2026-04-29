#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
SRC=Path('/Users/seohoseong/Documents/codex/cabinet-question-radar/data/next_meeting_radar.json')
OUT=Path('/Users/seohoseong/Documents/codex/cabinet-question-radar/data/next_meeting_briefing.md')
data=json.loads(SRC.read_text())
packets=data['packets'][:5]
lines=['# 다음 국무회의 예상 질문 브리핑','',f"_생성: {data['generated_at']} / 기준일: 최근 7일 뉴스_",'', '> 실제 의중 예측이 아니라, 국무회의 전 장관 답변 준비용 이슈 레이더입니다.','']
for i,p in enumerate(packets,1):
    lines += [f"## {i}. {p['ministry']} — {p['issue_id']}", '', f"**왜 올라왔나**: 기사 {p['count']}건, 핵심 신호 `{', '.join(p['signals'][:8])}`", '', '**대통령 예상 질문**']
    for q in p['questions']:
        lines.append(f'- {q}')
    lines += ['', '**장관이 바로 준비할 답변 포인트**']
    if p['issue_id']=='school_field_trip':
        lines += ['- 축소 원인 분해: 교사 형사책임 / 안전요원 부족 / 비용 / 학부모 민원 / 학교장 부담', '- 법·제도 대안: 교사 면책 범위, 학교안전공제, 안전요원 예산, 표준 매뉴얼', '- 형평성: 학교·지역별 체험학습 실시율 격차와 보완책']
    elif p['issue_id']=='disaster_safety':
        lines += ['- 최근 산불·침수·지하차도 안전 신호별 현황', '- 지자체/경찰/소방/행안부 역할 분담', '- 국민 안내 체계: 내비·재난문자·통제정보 실시간성']
    elif p['issue_id']=='prices_livelihood':
        lines += ['- 물가 부담 품목과 계층별 체감 지표', '- 직접지원/보증/세제/예산집행 비교', '- 재정소요와 부작용 관리 방안']
    elif p['issue_id']=='finance_rates':
        lines += ['- 중금리대출·전세대출·중소기업 근로자 대출 변화', '- 취약차주 부담 완화와 금융권 수익성 사이 균형', '- 생산적 금융·민생금융으로 흐르게 하는 장치']
    elif p['issue_id']=='justice_reform':
        lines += ['- 범죄·수사·증거보전 관련 현안 구분', '- 수사기관 개편/중수청 준비 상황', '- 재판 가능성·증거 확보·피해자 보호 체계']
    else:
        lines += ['- 최신 지표', '- 현장 애로', '- 단기 대책과 구조 대책 구분']
    lines += ['', '**대표 기사**']
    for it in p['items'][:3]:
        lines.append(f"- {it['pub_date']} · {it.get('relevance_score',0)}점 · {it['title']}")
    lines.append('')
OUT.write_text('\n'.join(lines))
print(OUT)
