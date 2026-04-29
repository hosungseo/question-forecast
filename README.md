# Question Forecast

회의 전 뉴스와 과거 국무회의록을 연결해, 다음 국무회의에서 나올 수 있는 대통령 질문 후보를 만드는 공개형 분석 실험입니다.

> 실제 의중 예측이 아니라, 장관 답변 준비와 국정현안 점검을 돕는 **review-first issue radar**입니다.

## Live / Reports

- GitHub Pages: <https://hosungseo.github.io/question-forecast/>
- Vercel: <https://question-forecast.vercel.app>
- API latest: <https://question-forecast.vercel.app/api/latest>
- API issues: <https://question-forecast.vercel.app/api/issues>
- Next meeting briefing: [`docs/briefing.md`](docs/briefing.md)
- Full issue radar: [`docs/radar.md`](docs/radar.md)
- Gold v1 labels: [`docs/gold-v1.md`](docs/gold-v1.md)
- Threshold calibration: [`docs/threshold.md`](docs/threshold.md)

## What it does

1. 과거 국무회의 대통령 발언 DB에서 질문/지시 후보를 추출합니다.
2. 회의 전 D-7~D-1 뉴스 이슈를 네이버 뉴스 API로 수집합니다.
3. 뉴스 이슈와 실제 대통령 발언의 연결 후보를 만들고 gold v1으로 보정합니다.
4. 최근 뉴스에서 다음 국무회의 예상 질문 패킷을 생성합니다.
5. 바로 읽을 수 있는 `next_meeting_briefing.md`를 출력합니다.

## Current outputs

- `data/next_meeting_briefing.md` — Top 5 회의 전 준비 브리핑
- `data/next_meeting_radar.md` — 전체 이슈 레이더
- `data/gold_v1.md` — 보수적으로 고정한 positive/negative 학습셋
- `data/threshold_report.md` — 초기 threshold 점검
- `data/cabinet_question_radar.sqlite` — 로컬 분석 DB

## Scripts

- `scripts/build_radar.py` — 과거 회의별 뉴스/질문 후보 DB 생성
- `scripts/enrich_radar.py` — 이슈 클러스터 생성
- `scripts/match_radar.py` — high-recall 이슈→질문 후보 매칭
- `scripts/rerank_matches.py` — 검토 큐 등급화
- `scripts/freeze_gold_v1.py` — 보수적 gold v1 고정
- `scripts/predict_next_meeting.py` — 최근 뉴스 기반 다음 회의 레이더 생성
- `scripts/export_briefing.py` — Top 5 브리핑 생성

## Run

```bash
export NAVER_CLIENT_ID=...
export NAVER_CLIENT_SECRET=...
python3 scripts/predict_next_meeting.py
python3 scripts/export_briefing.py
```

Historical rebuild:

```bash
python3 scripts/build_radar.py --limit-meetings 36 --daily-date-queries --date-query-days 3
python3 scripts/enrich_radar.py
python3 scripts/match_radar.py
python3 scripts/rerank_matches.py
python3 scripts/adjudicate_review_queue.py
python3 scripts/freeze_gold_v1.py
```

## Data note

The project was bootstrapped from a local Cabinet meeting remarks database and generated reports. API credentials are read only from environment variables and are not stored in this repository.
