import json
from datetime import datetime
from typing import Dict, Any, List, Optional

from tools import SerperClient, NLUParser
from ui import inventory_tool, feature_match_tool, schedule_test_drive, generate_and_send_emails_bg

class AgentTools:
    def __init__(self):
        self.serper = SerperClient()
        self.nlu = NLUParser()

    def serper_search(self, query: str) -> str:
        result = self.serper.search(query)
        return result.get('summary', 'No results found.')

    def inventory_lookup(self, payload: str) -> str:
        # payload: 'zipcode=XXXXX;model=ModelName'
        parts = dict([p.split('=') for p in payload.split(';') if '=' in p])
        zipcode = parts.get('zipcode', '')
        model = parts.get('model')
        items = inventory_tool(zipcode, model)
        if not items:
            return 'No inventory found near the provided ZIP code.'
        brief = []
        for it in items[:10]:
            brief.append(f"{it['model']} {it['trim']} at {it['dealership_name']} (VIN:{it['vin']}) - {it['available_status']}")
        return '\n'.join(brief)

    def feature_match(self, payload: str) -> str:
        try:
            p = json.loads(payload)
            feats = p.get('features', [])
            zipcode = p.get('zipcode', '')
        except Exception:
            return 'Invalid payload for feature_match'
        candidates = inventory_tool(zipcode)
        matched = feature_match_tool(feats, candidates)
        if not matched:
            return 'No similar models found nearby.'
        out = []
        for m in matched[:8]:
            out.append(f"{m['model']} {m['trim']} @ {m['dealership_name']} (VIN:{m['vin']}) — features: {', '.join(m.get('features',[]))}")
        return '\n'.join(out)

    def schedule_drive(self, payload: str) -> str:
        try:
            p = json.loads(payload)
            dt = datetime.fromisoformat(p['date'] + 'T' + p['time'])
            res = schedule_test_drive(p['name'], p['email'], p['phone'], p['zipcode'], int(p['inventory_id']), int(p['dealership_id']), p.get('salesperson_id'), dt, p.get('special_request',''))
            dealership = {"dealership_name": p.get('dealership_name',''), "address": p.get('dealership_address',''), "dealership_email": p.get('dealership_email')}
            generate_and_send_emails_bg(p['name'], p['email'], p['phone'], p.get('model','Unknown'), p.get('trim',''), dealership, res['date'], res['time'], p.get('salesperson_name','Sales Team'))
            return f"Scheduled test drive on {res['date']} at {res['time']} (id: {res['testdrive_id']}). Confirmation emails sent."
        except Exception as e:
            return f"Error scheduling test drive: {e}"

    def parse_intent(self, user_text: str) -> Dict[str, Any]:
        return self.nlu.parse_intent(user_text)
    
    