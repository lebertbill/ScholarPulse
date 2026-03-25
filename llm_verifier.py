import json
import os
from llm_utils import _post_with_retry, _ollama_with_retry

class LLMVerifier:
    def __init__(self, mode="local", model="gemma3:27b"):
        self.mode = mode
        self.model = model
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.api_key = os.getenv("OPENROUTER_API_KEY")

    def _get_system_prompt(self, field: str):
        return (
            f"You are an expert scientific literature reviewer. "
            f"Determine if the research article (title and abstract) is strictly relevant to the field: '{field}'. "
            "Respond ONLY in valid JSON format with a single boolean key: \"is_relevant\". "
            "Example: {\"is_relevant\": true}"
        )

    async def verify_relevance(self, title: str, abstract: str, field: str) -> dict:
        """Verifies if an article is relevant to the field using the selected LLM."""
        if not title or title == "No Title":
            return {"is_relevant": False}
        
        user_prompt = f"Title: {title}\nAbstract: {abstract}\n\nIs this relevant?"
        system_prompt = self._get_system_prompt(field)
        
        try:
            if self.mode == "local":
                full_prompt = f"{system_prompt}\n\n{user_prompt}"
                content = await _ollama_with_retry(full_prompt, self.model)
            else:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://scholarpulse.local", 
                    "X-Title": "ScholarPulse"
                }
                payload = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "response_format": {"type": "json_object"}
                }
                data = await _post_with_retry(self.api_url, headers, payload)
                content = data['choices'][0]['message']['content']

            start = content.find('{')
            end = content.rfind('}')
            if start != -1 and end != -1:
                json_str = content[start:end+1]
                return json.loads(json_str)
            

            return json.loads(content.strip())
        except Exception as e:
            print(f"[LLM] Verification error: {e}")
            return {"is_relevant": False}
