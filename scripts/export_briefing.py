#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'data'/'next_meeting_radar.json'
OUT=ROOT/'data'/'next_meeting_briefing.md'
data=json.loads(SRC.read_text())
packets=data['packets'][:5]
lines=['# 다음 국무회의 예상 질문 브리핑','',f"_생성: {data['generated_at']} / 기준일: 최근 7일 뉴스_",'', '> 실제 의중 예측이 아니라, 국무회의 전 장관 답변 준비용 이슈 레이더입니다.','']
for i,p in enumerate(packets,1):
    synthesis=p.get('question_synthesis',{})
    align=p.get('ministry_work_alignment',{})
    like=p.get('cabinet_question_likelihood',{})
    delta=p.get('daily_delta',{})
    stat=p.get('statistical_evidence',{})
    stat_labels=', '.join([c.get('label','') for c in stat.get('candidates',[])[:3]])
    lines += [f"## {i}. {p['ministry']} — {p['issue_id']}", '', f"**왜 올라왔나**: 기사 {p['count']}건, 핵심 신호 `{', '.join(p['signals'][:8])}`", f"**국무회의 질문 가능성**: {like.get('score','-')} / {like.get('band','-')}", f"**연결된 부처 업무**: {', '.join(align.get('function_domains',[])[:4])}", f"**관련 통계 후보**: {stat_labels or '미지정'}", f"**전일 대비**: {delta.get('interpretation','비교 기준 없음')}", '', '**종합 판단**', synthesis.get('diagnosis',''), '', '**대통령 예상 질문: 고도화 로직 기반**']
    for q in synthesis.get('questions', []):
        lines.append(f"- **{q.get('move_label', q.get('move'))}**: {q['question']}")
    if synthesis.get('follow_up'):
        lines += ['', '**후속 지시 후보**', f"- {synthesis['follow_up']}"]
    lines += ['', '**이슈별 보조 질문**']
    for q in p['questions']:
        lines.append(f'- {q}')
    if stat.get('candidates'):
        lines += ['', '**답변에 써야 할 통계 근거**', f"- 답변 프레임: {stat.get('answer_frame','통계는 질문 문구가 아니라 답변 근거로 사용')}"]
        for c in stat.get('answer_evidence_cards',[])[:4]:
            lines.append(f"- **{c.get('stat','통계')}**: {c.get('use_in_answer','')} / 사용법: {c.get('how_to_phrase','')}")
        if stat.get('live_status') != 'ok' and stat.get('live_errors'):
            lines.append(f"- KOSIS live status: {stat.get('live_status')} ({'; '.join(stat.get('live_errors',[])[:2])})")
        for live in stat.get('live_reference_cards',[])[:1]:
            lines.append(f"- 참고 live 값 · {live.get('label')} · latest={live.get('latest_value')} previous={live.get('previous_value')}")
    if p.get('similar_historical_cases'):
        lines += ['', '**과거 유사 질문 사례**']
        for c in p['similar_historical_cases'][:2]:
            lines.append(f"- {c.get('meeting_date','')} · {c.get('question_type','')} · {c.get('excerpt','')}")
    if p.get('question_flow'):
        lines += ['', '**예상 질의 흐름**']
        for f in p['question_flow'][:4]:
            lines.append(f"- {f.get('stage')}: {f.get('question','')}")
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
