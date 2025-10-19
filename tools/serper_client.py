import os
import requests
import re
from typing import Dict, Any, List

SERPER_URL = "https://google.serper.dev/search"

def serper_raw_search(q: str, location: str = None) -> Dict[str, Any]:
    """Call Serper API with secure API key"""
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        raise RuntimeError("SERPER_API_KEY not set")
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    payload = {"q": q}
    if location:
        payload["location"] = location
    resp = requests.post(SERPER_URL, headers=headers, json=payload, timeout=10)
    resp.raise_for_status()
    return resp.json()

def extract_features_from_text(text: str) -> List[str]:
    """Heuristic extraction of car features from text"""
    features = []
    m = re.search(r"[Ff]eatures?:\s*([\w\s,\-()\/]+)", text)
    if m:
        parts = [p.strip() for p in m.group(1).split(",") if p.strip()]
        features.extend(parts)
    # fallback keywords
    keywords = ["hybrid","awd","panoramic","heated","sunroof","leather","safety","infotainment","mpg","turbo"]
    for k in keywords:
        if k in text.lower() and k.capitalize() not in features:
            features.append(k.capitalize())
    return features

def parse_serper_response(resp_json: Dict[str, Any]) -> Dict[str, Any]:
    """Parse Serper JSON and extract summary, features, trims"""
    out = {"summary": "", "features": [], "trims": []}
    # KnowledgeGraph
    kg = resp_json.get("knowledgeGraph")
    if kg:
        out['summary'] += kg.get('description','')
    # Answer box
    ab = resp_json.get('answerBox')
    if ab:
        out['summary'] += '\n' + (ab.get('answer') or ab.get('snippet') or '')
    # Organic results
    for o in resp_json.get('organic', [])[:5]:
        snippet = o.get('snippet','')
        out['summary'] += '\n' + snippet
        out['features'].extend(extract_features_from_text(snippet))
        title = o.get('title','')
        for t in ['XLE','XSE','Limited','Base','LE','TRD']:
            if t in title and t not in out['trims']:
                out['trims'].append(t)
    # Deduplicate
    out['features'] = list(dict.fromkeys(out['features']))
    out['trims'] = list(dict.fromkeys(out['trims']))
    return out

def serper_search_and_parse(q: str, location: str = None) -> Dict[str, Any]:
    """Full pipeline: API call + parsing"""
    raw = serper_raw_search(q, location)
    parsed = parse_serper_response(raw)
    return parsed
