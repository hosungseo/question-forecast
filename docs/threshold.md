# Cabinet Question Radar — threshold calibration

Gold v1 기준으로 candidate_score/evidence_score threshold를 간단 점검한 표다.

## candidate_score thresholds

| threshold | selected | TP | FP | precision | recall |
|---:|---:|---:|---:|---:|---:|
| 0.50 | 32 | 8 | 24 | 0.25 | 1.00 |
| 0.52 | 24 | 7 | 17 | 0.29 | 0.88 |
| 0.54 | 24 | 7 | 17 | 0.29 | 0.88 |
| 0.56 | 17 | 4 | 13 | 0.24 | 0.50 |
| 0.58 | 17 | 4 | 13 | 0.24 | 0.50 |
| 0.60 | 4 | 3 | 1 | 0.75 | 0.38 |
| 0.62 | 3 | 2 | 1 | 0.67 | 0.25 |

## evidence_score thresholds

| threshold | selected | TP | FP | precision | recall |
|---:|---:|---:|---:|---:|---:|
| 2 | 32 | 8 | 24 | 0.25 | 1.00 |
| 3 | 32 | 8 | 24 | 0.25 | 1.00 |
| 4 | 32 | 8 | 24 | 0.25 | 1.00 |
| 5 | 6 | 2 | 4 | 0.33 | 0.25 |
| 6 | 3 | 2 | 1 | 0.67 | 0.25 |
| 7 | 0 | 0 | 0 | 0.00 | 0.00 |

## Recommendation

- 현재 gold v1이 8 positive / 24 negative로 작으므로 수치는 방향성만 본다.
- `evidence_score >= 4`는 recall은 높지만 precision이 낮다.
- `candidate_score >= 0.54` 부근이 작은 gold set에서 균형점으로 보이나, 최종 운영은 LLM/human adjudication을 2차 단계로 두는 것이 안전하다.