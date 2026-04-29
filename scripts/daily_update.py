#!/usr/bin/env python3
"""Daily local updater for Question Forecast.

Runs the latest-news radar, exports the briefing, syncs docs for GitHub Pages,
and commits/pushes only when generated outputs changed.

Secrets are read from local .env or process env. Do not commit .env.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
DOCS = ROOT / 'docs'
STATUS = DATA / 'daily_update_status.json'


def load_env() -> None:
    env_path = ROOT / '.env'
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=check)


def copy_docs() -> None:
    DOCS.mkdir(exist_ok=True)
    mapping = {
        DATA / 'next_meeting_briefing.md': DOCS / 'briefing.md',
        DATA / 'next_meeting_radar.md': DOCS / 'radar.md',
        DATA / 'gold_v1.md': DOCS / 'gold-v1.md',
        DATA / 'threshold_report.md': DOCS / 'threshold.md',
    }
    for src, dst in mapping.items():
        if src.exists():
            shutil.copyfile(src, dst)


def git_changed() -> bool:
    out = run(['git', 'status', '--porcelain'], check=True).stdout.strip()
    return bool(out)


def top_issues() -> list[dict]:
    radar = DATA / 'next_meeting_radar.json'
    if not radar.exists():
        return []
    data = json.loads(radar.read_text())
    return [
        {
            'rank': i + 1,
            'issue_id': p.get('issue_id'),
            'ministry': p.get('ministry'),
            'priority': p.get('priority'),
            'count': p.get('count'),
        }
        for i, p in enumerate(data.get('packets', [])[:5])
    ]


def main() -> int:
    load_env()
    missing = [k for k in ['NAVER_CLIENT_ID', 'NAVER_CLIENT_SECRET'] if not os.environ.get(k)]
    if missing:
        print(f"Missing env vars: {', '.join(missing)}", file=sys.stderr)
        return 2

    before_top = top_issues()
    run([sys.executable, 'scripts/derive_historical_priors.py'])
    run([sys.executable, 'scripts/predict_next_meeting.py'])
    run([sys.executable, 'scripts/export_briefing.py'])
    copy_docs()
    after_top = top_issues()

    changed = git_changed()
    commit_hash = None
    pushed = False
    if changed:
        run(['git', 'add', 'data/historical_question_priors.json', 'data/next_meeting_radar.json', 'data/next_meeting_radar.md', 'data/next_meeting_briefing.md', 'docs/briefing.md', 'docs/radar.md'])
        stamp = dt.datetime.now().strftime('%Y-%m-%d %H:%M KST')
        run(['git', 'commit', '-m', f'Daily forecast update ({stamp})'])
        run(['git', 'push'])
        commit_hash = run(['git', 'rev-parse', '--short', 'HEAD']).stdout.strip()
        pushed = True

    status = {
        'ran_at': dt.datetime.now().isoformat(),
        'changed': changed,
        'pushed': pushed,
        'commit': commit_hash,
        'before_top': before_top,
        'after_top': after_top,
    }
    STATUS.write_text(json.dumps(status, ensure_ascii=False, indent=2))
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
