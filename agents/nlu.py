import os
from typing import Tuple, Dict
import openai
import json
from dotenv import load_dotenv
load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

INTENT_PROMPT = '''
You are an intent classifier. Given a user message, return JSON with keys: 
intent (one of check_inventory, schedule_test_drive, get_specs, compare_models, general), 
and metadata like model if present.

Examples:
"I want to schedule a test drive for a RAV4 tomorrow" -> {"intent":"schedule_test_drive", "model":"RAV4"}
"Is RAV4 available near 90012?" -> {"intent":"check_inventory","model":"RAV4","zipcode":"90012"}

Only output valid JSON.

Message: "{message}"
'''

def classify_intent(message: str) -> Tuple[str, Dict]:
    if not openai.api_key:
        # fallback deterministic rules
        q = message.lower()
        if 'test drive' in q or 'schedule' in q or 'book' in q:
            return 'schedule_test_drive', {}
        if 'available' in q or 'inventory' in q or 'stock' in q:
            return 'check_inventory', {}
        if 'compare' in q or 'vs' in q:
            return 'compare_models', {}
        return 'general', {}

    prompt = INTENT_PROMPT.replace('{message}', message)
    res = openai.ChatCompletion.create(
        model='gpt-4o-mini',
        messages=[{'role':'user','content':prompt}],
        max_tokens=200,
        temperature=0
    )
    text = res['choices'][0]['message']['content']
    try:
        data = json.loads(text)
        intent = data.get('intent','general')
        meta = {k:v for k,v in data.items() if k != 'intent'}
        return intent, meta
    except Exception:
        return 'general', {}
