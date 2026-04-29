from http.server import BaseHTTPRequestHandler
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data' / 'next_meeting_radar_enhanced.json'

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            data = json.loads(DATA.read_text())
            body = json.dumps({
                'generated_at': data.get('generated_at'),
                'enhancement_note': data.get('enhancement_note'),
                'packets': (data.get('packets') or [])[:10]
            }, ensure_ascii=False).encode('utf-8')
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
