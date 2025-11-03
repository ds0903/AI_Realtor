"""
Claude AI Agent для ШІ Ріелтора
"""
import anthropic
import json
import config
from services.google_sheets import sheets_service
from ai.prompts import get_system_prompt, get_context_prompt
from database import async_session, Conversation
from sqlalchemy import select

class ClaudeAgent:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-20250514"
        
    def _get_system_prompt(self):
        """Отримує системний промпт з Google Sheets даними"""
        welcome = sheets_service.get_welcome_messages()
        questions = sheets_service.get_questions()
        objections = sheets_service.get_objections()
        reactions = sheets_service.get_reactions()
        
        return get_system_prompt(welcome, questions, objections, reactions)

    async def _get_conversation_from_db(self, user_id):
        """Отримує конверсацію з БД"""
        async with async_session() as session:
            result = await session.execute(
                select(Conversation).where(Conversation.user_id == user_id)
            )
            return result.scalar_one_or_none()
    
    async def process_message(self, user_id, user_message):
        """Обробляє повідомлення користувача через Claude AI"""
        conversation_record = await self._get_conversation_from_db(user_id)
        
        if not conversation_record:
            messages_history = []
            filters = {}
            questions_asked = []
        else:
            messages_history = conversation_record.messages or []
            filters = conversation_record.filters or {}
            questions_asked = []
        
        context = get_context_prompt(
            messages_history[-10:],
            filters,
            questions_asked
        )
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                temperature=0.7,
                system=self._get_system_prompt(),
                messages=[
                    {
                        "role": "user", 
                        "content": f"{context}\n\nПОВІДОМЛЕННЯ: {user_message}\n\nВІДПОВІДЬ (JSON):"
                    }
                ]
            )
            
            response_text = response.content[0].text.strip()
            
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            try:
                result = json.loads(response_text)
            except:
                result = {
                    "response": response_text,
                    "filters": filters,
                    "questions_asked": questions_asked,
                    "ready_for_contact": False
                }
            
            if result.get("filters"):
                for key, value in result["filters"].items():
                    if value is not None:
                        filters[key] = value
            
            new_questions = result.get("questions_asked", [])
            if new_questions:
                questions_asked = sorted(list(set(questions_asked + new_questions)))
            
            ready_for_contact = len(questions_asked) >= 6 or result.get("ready_for_contact", False)
            
            return {
                "response": result.get("response", "Вибачте, сталася помилка."),
                "filters": filters,
                "questions_asked": questions_asked,
                "ready_for_contact": ready_for_contact
            }
            
        except Exception as e:
            print(f"Claude API error: {e}")
            return {
                "response": "Вибачте, виникла технічна проблема.",
                "filters": filters,
                "questions_asked": questions_asked,
                "ready_for_contact": False
            }

claude_agent = ClaudeAgent()
