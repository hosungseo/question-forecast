#!/usr/bin/env python3
"""Export a copy-ready daily executive digest for all top packets."""
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
DOCS=ROOT/'docs'
SRC=DATA/'next_meeting_radar_enhanced.json'
OUT=DOCS/'daily-digest.md'


def main():
    data=json.loads(SRC.read_text())
    packets=(data.get('packets') or [])[:5]
    generated=data.get('generated_at','')
    high=[p for p in packets if (p.get('cabinet_question_likelihood') or {}).get('band')=='cabinet_high']
    lines=[
        '# Question Forecast 일일 종합 브리핑', '',
        f'- 생성: {generated}',
        f'- Top 5 중 cabinet_high: {len(high)}건',
        '',
        '## 오늘 먼저 볼 이슈',
    ]
    for i,p in enumerate(packets,1):
        like=p.get('cabinet_question_likelihood') or {}
        synth=p.get('question_synthesis') or {}
        q=((synth.get('questions') or [{}])[0]).get('question','')
        lines += [
            f'### {i}. {p.get("ministry")} — {p.get("issue_id")}',
            f'- 질문 가능성: {like.get("score")} / {like.get("band")}',
            f'- 핵심 판단: {synth.get("diagnosis")}',
            f'- 예상 첫 질문: {q}',
        ]
        oral=p.get('oral_brief') or {}
        if oral.get('thirty_second'):
            lines.append(f'- 30초 보고: {oral.get("thirty_second")}')
        stat=p.get('statistical_evidence') or {}
        if stat.get('answer_frame'):
            lines.append(f'- 답변 근거: {stat.get("answer_frame")}')
        lines.append('')
    lines += ['## 공통 답변 원칙',
        '- 대통령 질문은 통계명이 아니라 정책 책임·병목·현장 부담·국민 체감으로 답한다.',
        '- 통계는 질문 문구에 넣지 않고 장관 답변의 규모·추세·비교 근거로 사용한다.',
        '- 답변은 현재 상황 → 원인 구분 → 조치 계획 → 후속 보고 순서로 준비한다.',
        '',
        '## 링크',
        '- Dashboard: https://hosungseo.github.io/question-forecast/',
        '- Full briefing: https://hosungseo.github.io/question-forecast/briefing.md',
    ]
    OUT.write_text('\n'.join(lines).strip()+'\n')
    print(OUT)

if __name__=='__main__': main()
