# Question Forecast

국무회의 회의록 DB와 회의 전 네이버 뉴스 API 결과를 연결해, 어떤 뉴스 이슈가 대통령 질문/지시로 올라오는지 분석하기 위한 로컬 파일럿 DB.

## 입력

- 국무회의 대통령 발언 SQLite  
  `/Users/seohoseong/Documents/codex/lee_jm_president_remarks_db/lee_jm_president_remarks.sqlite`

## 산출

- `data/cabinet_question_radar.sqlite`

주요 테이블:

- `meetings`: 분석 대상 국무회의
- `presidential_question_candidates`: 대통령 질문/지시 후보 발언
- `pre_meeting_news`: 회의일 D-7~D-1 네이버 뉴스 후보 기사
- `issue_question_links`: 뉴스와 질문 후보의 키워드 기반 연결 후보
- `run_meta`: 실행 메타데이터

## 실행 예시

```bash
NAVER_CLIENT_ID=... NAVER_CLIENT_SECRET=... \
python3 scripts/build_radar.py --limit-meetings 5 --display 5
```

초기 MVP는 예측 모델이 아니라 관측 데이터셋을 만든다. 즉 “회의 전 뉴스 → 실제 국무회의 대통령 질문/지시”의 후보 링크를 쌓은 뒤, 반영률·지연일·부처별 패턴을 분석한다.
