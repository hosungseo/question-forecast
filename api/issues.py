from http.server import BaseHTTPRequestHandler
import json
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data' / 'next_meeting_radar_enhanced.json'

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            qs = parse_qs(urlparse(self.path).query)
            ministry = (qs.get('ministry') or [None])[0]
            issue_id = (qs.get('issue_id') or [None])[0]
            data = json.loads(DATA.read_text())
            packets = data.get('packets') or []
            if ministry:
                packets = [p for p in packets if p.get('ministry') == ministry]
            if issue_id:
                packets = [p for p in packets if p.get('issue_id') == issue_id]
            body = json.dumps({'generated_at': data.get('generated_at'), 'count': len(packets), 'packets': packets}, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 's-maxage=300, stale-while-revalidate=3600')
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            body = json.dumps({'error': str(e)}, ensure_ascii=False).encode('utf-8')
            self.send_response(500)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(body)
