# Question Forecast — Codex Handoff

## Current state

Question Forecast is a public GitHub Pages project that turns daily news into cabinet-meeting preparation packets.

- Repo: https://github.com/hosungseo/question-forecast
- Live: https://hosungseo.github.io/question-forecast/
- Local path: `/Users/seohoseong/Documents/codex/question-forecast`

## Core concept

This is not a generic news summarizer. It is:

```text
daily news monitoring
→ ministry/work-domain routing
→ cabinet-question likelihood scoring
→ historical presidential question-pattern synthesis
→ minister answer-prep packet
```

Important framing:

- The President does **not** ask statistics by name.
- Questions should stay in natural policy language.
- Statistics are used as **minister answer evidence**, not as literal question text.

## Daily automation

OpenClaw local cron runs daily at 07:30 KST.

Script:

```bash
python3 scripts/daily_update.py
```

The script:

1. saves previous radar snapshot locally,
2. builds ministry work dictionary,
3. builds KOSIS/stat evidence dictionary,
4. derives historical question priors,
5. generates next-meeting radar,
6. enhances packets,
7. exports briefing,
8. copies docs,
9. commits/pushes if generated outputs changed.

Local `.env` contains API keys and is gitignored. Do not commit secrets.

## Main scripts

- `scripts/daily_update.py` — full daily pipeline
- `scripts/predict_next_meeting.py` — recent-news issue radar
- `scripts/question_patterns.py` — question synthesis engine
- `scripts/derive_historical_priors.py` — historical move priors from cabinet remarks DB
- `scripts/ministry_knowledge.py` — ministry work dictionary + official-source hooks
- `scripts/kosis_stats.py` — statistical evidence dictionary + KOSIS smoke checks
- `scripts/enhance_radar.py` — v3 packet enrichment
- `scripts/export_briefing.py` — human-readable briefing

## Main generated files

- `data/next_meeting_briefing.md`
- `data/next_meeting_radar.json`
- `data/next_meeting_radar_enhanced.json`
- `data/ministry_work_dictionary.json`
- `data/historical_question_priors.json`
- `data/issue_stat_dictionary.json`
- `docs/briefing.md`
- `docs/radar.md`

## Current model logic

Question synthesis combines:

```text
issue prior
+ current article signals
+ ministry historical prior
+ global presidential prior
+ salience(priority/count)
= selected question moves
```

Question moves:

- `ground_truth`
- `causal_split`
- `coordination`
- `bottleneck`
- `field_burden`
- `public_outcome`
- `instruction`

The output includes:

- ministry work alignment,
- cabinet-question likelihood score/band,
- similar historical cabinet questions,
- question flow,
- daily delta,
- answer evidence cards from statistics.

## Current top packet shape

Briefing sections currently include:

- why this issue rose,
- cabinet-question likelihood,
- connected ministry work,
- related stat candidates,
- daily delta,
- synthesis diagnosis,
- expected presidential questions,
- follow-up instruction candidate,
- issue-specific auxiliary questions,
- statistics to use in the minister answer,
- similar historical questions,
- expected question flow,
- minister answer prep points,
- representative articles.

## Recent important correction

The statistical layer was corrected after user feedback:

> “대통령은 통계를 묻지 않아. 답변을 통계를 써서 해야하는거야.”

So do not write presidential questions like “Did you check CPI?” Instead write:

- question: “물가 부담이 어느 계층에 집중되고 있습니까?”
- answer evidence: CPI/living CPI/household expenditure should support the minister's answer.

## Next good tasks

1. Replace seeded ministry work dictionary with official MOLEG law.go.kr organization-decree extracts where available.
2. Wire Public Data Portal central-agency function classification into `ministry_work_dictionary.json`.
3. Expand KOSIS from smoke/candidate cards to issue-specific live series mappings.
4. Improve similar-case retrieval with embeddings or BM25 instead of token overlap.
5. Add a compact dashboard page to `docs/index.html` showing latest top 5 packets directly, not just markdown links.

## Verification commands

```bash
python3 scripts/daily_update.py
python3 -m py_compile scripts/*.py
git status --short
```

Check live page:

```bash
curl -L -s -o /tmp/qf.html -w 'HTTP %{http_code}\n' https://hosungseo.github.io/question-forecast/
```
