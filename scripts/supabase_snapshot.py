#!/usr/bin/env python3
"""Optional Supabase snapshot uploader.

Requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY. If absent, exits quietly.
"""
from __future__ import annotations
import json, os, urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RADAR=ROOT/'data'/'next_meeting_radar_enhanced.json'


def req(url, key, method='POST', data=None):
    body=json.dumps(data).encode() if data is not None else None
    r=urllib.request.Request(url, data=body, method=method, headers={
        'apikey': key,
        'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json',
        'Prefer': 'return=representation,resolution=merge-duplicates'
    })
    with urllib.request.urlopen(r, timeout=20) as resp:
        return json.loads(resp.read().decode() or '[]')


def main():
    base=os.environ.get('SUPABASE_URL')
    key=os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
    if not base or not key:
        print('supabase_snapshot_skipped: missing SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY')
        return 0
    data=json.loads(RADAR.read_text())
    packets=data.get('packets') or []
    generated=data.get('generated_at')
    high=sum(1 for p in packets[:5] if (p.get('cabinet_question_likelihood') or {}).get('band')=='cabinet_high')
    run_payload={'generated_at':generated,'source':'question-forecast','top_count':len(packets[:5]),'cabinet_high_count':high,'payload':data}
    run=req(f'{base}/rest/v1/daily_runs?on_conflict=generated_at,source', key, data=run_payload)[0]
    run_id=run['id']
    rows=[]
    for i,p in enumerate(packets[:10],1):
        synth=p.get('question_synthesis') or {}
        qs=synth.get('questions') or []
        stat=p.get('statistical_evidence') or {}
        like=p.get('cabinet_question_likelihood') or {}
        rows.append({
            'run_id':run_id,
            'rank':i,
            'issue_id':p.get('issue_id'),
            'ministry':p.get('ministry'),
            'likelihood_score':like.get('score'),
            'likelihood_band':like.get('band'),
            'priority':p.get('priority'),
            'article_count':p.get('count'),
            'diagnosis':synth.get('diagnosis'),
            'first_question':(qs[0] or {}).get('question') if qs else None,
            'answer_frame':stat.get('answer_frame'),
            'payload':p,
        })
    if rows:
        req(f'{base}/rest/v1/issue_packets?on_conflict=run_id,issue_id', key, data=rows)
    print(f'supabase_snapshot_uploaded: run_id={run_id} packets={len(rows)}')
    return 0

if __name__=='__main__': raise SystemExit(main())
