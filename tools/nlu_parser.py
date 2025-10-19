import os
from langchain_openai import ChatOpenAI

class NLUParser:
    """
    Simple NLU parser using OpenAI LLM for intent classification and entity extraction.
    """
    def __init__(self, temperature: float = 0.0):
        self.llm = ChatOpenAI(temperature=temperature) if os.getenv("OPENAI_API_KEY") else None

    def parse_intent(self, user_text: str) -> dict:
        """
        Returns structured dict: {"intent": str, "entities": dict}
        intents: schedule_test_drive, check_inventory, compare_models, general
        """
        if not self.llm:
            # Fallback rule-based simple matching
            text = user_text.lower()
            if any(k in text for k in ["test drive", "schedule", "book", "drive"]):
                return {"intent": "schedule_test_drive", "entities": {}}
            elif any(k in text for k in ["available", "stock", "inventory", "near", "zip"]):
                return {"intent": "check_inventory", "entities": {}}
            elif any(k in text for k in ["compare", "vs", "difference"]):
                return {"intent": "compare_models", "entities": {}}
            else:
                return {"intent": "general", "entities": {}}

        # LLM-based classification
        prompt = f"""
You are an NLU classifier for a Toyota car dealership chatbot.
Classify the user query into one of: schedule_test_drive, check_inventory, compare_models, general.
Extract any entities like model names, zipcode, or features in JSON format.
User query: {user_text}
Return JSON like {{"intent": "<intent>", "entities": {{"model": "Camry", "zipcode": "90012"}}}}
"""
        try:
            resp = self.llm.predict(prompt)
            # Attempt to parse JSON from response
            import json
            start = resp.find('{')
            end = resp.rfind('}')
            if start != -1 and end != -1:
                data = json.loads(resp[start:end+1])
                return data
        except Exception as e:
            print("NLU parse error:", e)
        # fallback
        return {"intent": "general", "entities": {}}