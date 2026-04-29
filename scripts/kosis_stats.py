#!/usr/bin/env python3
"""Attach KOSIS/statistical evidence candidates to Question Forecast packets.

KOSIS broad metadata is key-sensitive, so this module is deliberately robust:
- Uses KOSIS_API_KEY when present, otherwise a local known key if configured.
- Fetches only curated high-signal parameter-mode series.
- Falls back to a 'stat to check' card when live fetch fails.
"""
from __future__ import annotations

import json
import os
import subprocess
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
OUT = DATA / 'issue_stat_dictionary.json'

# Curated candidate series. Some are verified KOSIS parameter-mode examples from prior work.
STAT_CATALOG = {
    'prices_livelihood': [
        {'label': '소비자물가지수/생활물가 관련 지표', 'source': 'KOSIS', 'why': '물가·민생 부담의 실제 추세 확인', 'status': 'candidate', 'query_hint': '소비자물가지수 생활물가지수 품목별 물가'},
        {'label': '가계동향/소득분위별 지출', 'source': 'KOSIS', 'why': '부담이 어느 계층에 집중되는지 확인', 'status': 'candidate', 'query_hint': '가계동향 소득분위 지출'},
    ],
    'labor_jobs': [
        {'label': '고용률/실업률/청년고용률', 'source': 'KOSIS', 'why': '일자리 지표와 현장 체감 괴리 확인', 'status': 'candidate', 'query_hint': '고용률 실업률 청년고용률'},
        {'label': '산업재해/임금체불 행정통계', 'source': 'KOSIS/고용부', 'why': '산재·임금체불 이슈의 규모 확인', 'status': 'candidate', 'query_hint': '산업재해 임금체불'},
    ],
    'real_estate': [
        {'label': '주택보급/가구/인구 관련 지표', 'source': 'KOSIS', 'why': '공급 대책과 실수요 기반 비교', 'status': 'candidate', 'query_hint': '주택 가구 인구'},
        {'label': '전월세/주택가격 지표', 'source': 'KOSIS/부동산원', 'why': '전월세 시장 불안의 실제 추세 확인', 'status': 'candidate', 'query_hint': '전세 월세 주택가격'},
    ],
    'disaster_safety': [
        {'label': '화재 발생/재난 피해 통계', 'source': 'KOSIS/재난안전데이터', 'why': '재난·안전 이슈가 실제 피해 추세로 커지는지 확인', 'status': 'candidate', 'query_hint': '화재 발생 자연재해 피해'},
    ],
    'school_field_trip': [
        {'label': '지역별 학교 수/학생 수/교원 수', 'source': 'KOSIS/교육통계', 'why': '체험학습 축소가 어느 규모의 학생·학교에 영향을 주는지 추정', 'status': 'candidate', 'query_hint': '초등학교 학생수 교원수 학교수'},
        {'label': '학교 안전사고/교육활동 침해 관련 통계', 'source': '교육부/학교안전공제', 'why': '교사 책임·안전사고 부담의 실제 근거 확인', 'status': 'candidate', 'query_hint': '학교 안전사고 교육활동 침해'},
    ],
    'finance_rates': [
        {'label': '가계부채/대출금리', 'source': 'KOSIS/ECOS', 'why': '금리·대출 부담의 수치 근거 확인', 'status': 'candidate', 'query_hint': '가계부채 대출금리'},
        {'label': '서민금융/취약차주 지표', 'source': '금융위/금감원', 'why': '정책금융 대상 적합성 확인', 'status': 'candidate', 'query_hint': '서민금융 취약차주 연체율'},
    ],
    'justice_reform': [
        {'label': '범죄 발생/검거/재판 관련 통계', 'source': 'KOSIS/경찰청/법무부', 'why': '범죄 대응 이슈를 실제 발생·처리 지표로 확인', 'status': 'candidate', 'query_hint': '범죄 발생 검거 재판'},
    ],
    'medical': [
        {'label': '의료기관/의사/전공의/응급의료 지표', 'source': 'KOSIS/복지부', 'why': '의료 공백과 지역 접근성의 실제 규모 확인', 'status': 'candidate', 'query_hint': '의료기관 의사 전공의 응급의료'},
    ],
}

# Verified parameter-mode examples from prior KOSIS work. Used as smoke/liveness cards, not always issue-specific.
SMOKE_SERIES = [
    {'label': '주민등록인구(예시)', 'orgId': '101', 'tblId': 'DT_1B040A3', 'itmId': 'T20', 'objL1': '36', 'startPrdDe': '2024', 'endPrdDe': '2026'},
    {'label': '가구수(예시)', 'orgId': '101', 'tblId': 'DT_1B040B3', 'itmId': 'T1', 'objL1': '00', 'startPrdDe': '2024', 'endPrdDe': '2026'},
]


def api_key() -> str | None:
    return os.environ.get('KOSIS_API_KEY') or os.environ.get('KOSIS_KEY') or os.environ.get('KOSIS_APIKEY')


def redact_url(url: str, key: str) -> str:
    return url.replace(key, '***').replace(urllib.parse.quote_plus(key), '***').replace(urllib.parse.quote(key, safe=''), '***')


def fetch_param_series(series: dict) -> dict:
    key = api_key()
    if not key:
        return {'ok': False, 'error': 'missing KOSIS_API_KEY'}
    params = {
        'method': 'getList', 'apiKey': key, 'format': 'json', 'jsonVD': 'Y',
        'orgId': series['orgId'], 'tblId': series['tblId'], 'itmId': series['itmId'],
        'objL1': series.get('objL1', ''), 'objL2': series.get('objL2', ''), 'objL3': series.get('objL3', ''),
        'startPrdDe': series.get('startPrdDe', '2024'), 'endPrdDe': series.get('endPrdDe', '2026'),
        'prdSe': series.get('prdSe', 'Y'), 'loadGubun': '2',
    }
    url = 'https://kosis.kr/openapi/Param/statisticsParameterData.do?' + urllib.parse.urlencode({k: v for k, v in params.items() if v != ''})
    safe_url = redact_url(url, key)
    try:
        # curl -sk is more reliable with KOSIS SSL in this environment.
        cp = subprocess.run(['curl', '-skL', '--max-time', '20', url], text=True, capture_output=True, check=False)
        if cp.returncode != 0 or not cp.stdout.strip():
            return {'ok': False, 'error': cp.stderr.strip() or 'empty response', 'url': safe_url}
        data = json.loads(cp.stdout)
        if isinstance(data, dict) and data.get('err'):
            return {'ok': False, 'error': data.get('errMsg') or data.get('err'), 'url': safe_url}
        rows = data if isinstance(data, list) else data.get('data', []) if isinstance(data, dict) else []
        latest = rows[-1] if rows else None
        prev = rows[-2] if len(rows) >= 2 else None
        def val(row):
            if not row: return None
            for k in ['DT', 'dt', 'DATA_VALUE', 'value']:
                if k in row:
                    try: return float(str(row[k]).replace(',', ''))
                    except Exception: return row[k]
            return None
        return {'ok': True, 'label': series['label'], 'url': safe_url, 'latest': latest, 'previous': prev, 'latest_value': val(latest), 'previous_value': val(prev), 'rows': rows[-5:]}
    except Exception as e:
        return {'ok': False, 'error': str(e), 'url': safe_url}


def build() -> dict:
    smoke = [fetch_param_series(s) for s in SMOKE_SERIES]
    return {
        'source_note': 'KOSIS/statistical evidence dictionary for Question Forecast. Curated issue-level candidates plus live KOSIS smoke cards when available.',
        'kosis_live_smoke': smoke,
        'issue_stats': STAT_CATALOG,
    }


def main() -> int:
    data = build()
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(OUT)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
