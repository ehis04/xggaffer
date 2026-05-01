import anthropic
from django.conf import settings
from typing import List, Dict
import json

class LawsLLMParser:
    
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    
    def parse_law_from_images(self, images: List, law_number: int) -> Dict:
        image_data = []
        for img in images:
            from laws.utils.pdf_processor import PDFProcessor
            b64 = PDFProcessor.image_to_base64(img)
            image_data.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": b64
                }
            })
        
        prompt = f"""You are parsing Law {law_number} from the IFAB Laws of the Game PDF.

Extract and structure the following information as JSON:

{{
  "law_number": {law_number},
  "title": "Full title of the law",
  "clauses": [
    {{
      "clause_id": "1.1",
      "heading": "Section heading if present",
      "content": "Main text content",
      "examples": ["Any examples provided"],
      "notes": ["Any interpretations or notes"],
      "order": 1
    }}
  ],
  "key_points": ["List of main points for quiz generation"]
}}

Instructions:
- Preserve the exact hierarchical structure (sections, subsections)
- Include ALL text verbatim for accuracy
- Identify examples clearly (often in boxes or italics)
- Extract any interpretations or guidelines
- Maintain the order of clauses
- For key_points, extract testable facts suitable for quiz questions

Return ONLY valid JSON, no additional text."""

        message = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=16000,
            messages=[{
                "role": "user",
                "content": image_data + [{"type": "text", "text": prompt}]
            }]
        )
        
        response_text = message.content[0].text
        
        try:
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            json_str = response_text[start:end]
            parsed_data = json.loads(json_str)
            return parsed_data
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse LLM response as JSON: {e}\n\nResponse: {response_text}")
    
    def parse_law_from_text(self, text: str, law_number: int) -> Dict:
        prompt = f"""You are parsing Law {law_number} from the IFAB Laws of the Game.

Here is the text content:

{text}

Extract and structure this as JSON following this schema:

{{
  "law_number": {law_number},
  "title": "Full title",
  "clauses": [
    {{
      "clause_id": "1.1",
      "heading": "Section heading",
      "content": "Main text",
      "examples": [],
      "notes": [],
      "order": 1
    }}
  ],
  "key_points": ["Testable facts for quizzes"]
}}

Return ONLY valid JSON."""

        message = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=16000,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        
        response_text = message.content[0].text
        
        start = response_text.find('{')
        end = response_text.rfind('}') + 1
        json_str = response_text[start:end]
        return json.loads(json_str)
    
    def compare_editions(self, old_law_data: Dict, new_law_data: Dict) -> List[Dict]:
        prompt = f"""Compare these two versions of Law {old_law_data.get('law_number')} and identify all changes.

OLD VERSION:
{json.dumps(old_law_data, indent=2)}

NEW VERSION:
{json.dumps(new_law_data, indent=2)}

Return a JSON array of changes in this format:

[
  {{
    "clause_id": "1.1",
    "change_type": "modified|added|removed|clarified",
    "description": "Brief description of the change",
    "old_content": "Previous text (if modified/removed)",
    "new_content": "New text (if modified/added)"
  }}
]

Focus on substantive changes, not minor formatting differences.
Return ONLY valid JSON array."""

        message = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8000,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        
        response_text = message.content[0].text
        start = response_text.find('[')
        end = response_text.rfind(']') + 1
        json_str = response_text[start:end]
        return json.loads(json_str)