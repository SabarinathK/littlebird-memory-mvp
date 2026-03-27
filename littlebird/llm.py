import json

from .config import CONFIG, log
from .utils import default_extraction_result, require


class GroqClient:
    def __init__(self):
        require("groq")
        from groq import Groq

        self.client = Groq(api_key=CONFIG["groq_api_key"])
        self.model = CONFIG["groq_model"]
        log.info(f"Groq client ready - model: {self.model}")

    def extract_entities(self, text: str, source_app: str) -> dict:
        prompt = self._build_extraction_prompt(text, source_app)
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=800,
            )
            raw = response.choices[0].message.content.strip()
            return self._parse_extraction_response(raw)
        except Exception as error:
            log.warning(f"Entity extraction failed: {error}")
            return default_extraction_result()

    def answer_question(self, question: str, context_chunks: list) -> str:
        context_text = self._build_context_text(context_chunks)
        prompt = self._build_answer_prompt(question, context_text)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=600,
            )
            return response.choices[0].message.content.strip()
        except Exception as error:
            return f"Error generating answer: {error}"

    def _build_extraction_prompt(self, text: str, source_app: str) -> str:
        return f"""You are an entity extractor for a personal AI memory system.
Extract structured information from this screen capture.

Source app: {source_app}
Content:
{text[:2000]}

Return ONLY valid JSON (no markdown, no explanation):
{{
  "entities": [
    {{"type": "person|project|decision|topic|action|deadline", "value": "..."}}
  ],
  "relationships": [
    {{"from": "entity_value", "relation": "owns|works_on|decided|mentioned|assigned_to", "to": "entity_value"}}
  ],
  "summary": "one sentence summary of what this content is about",
  "is_sensitive": false
}}

Rules:
- Skip if content is a password manager, login form, or banking app
- Only extract meaningful entities (ignore boilerplate UI text)
- Keep entity values concise (< 60 chars)
- Return empty arrays if nothing meaningful found
"""

    def _build_context_text(self, context_chunks: list) -> str:
        return "\n\n---\n\n".join(
            [
                f"[{chunk.get('timestamp', '')[:19]}] [{chunk.get('source_app', '')}]\n"
                f"{chunk.get('text', chunk.get('content', ''))}"
                for chunk in context_chunks
            ]
        )

    def _build_answer_prompt(self, question: str, context_text: str) -> str:
        return f"""You are a personal AI assistant with access to the user's work memory.
Answer the question using ONLY the context provided below.
Be specific, cite the source app and time when relevant.
If the answer is not in the context, say so clearly.

MEMORY CONTEXT:
{context_text}

QUESTION: {question}

Answer concisely and helpfully:"""

    def _strip_markdown_fences(self, raw: str) -> str:
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return raw

    def _parse_extraction_response(self, raw: str) -> dict:
        cleaned = self._strip_markdown_fences(raw).strip()
        if cleaned:
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass

        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(cleaned[start : end + 1])

        raise json.JSONDecodeError("No JSON object found in model response", cleaned, 0)
