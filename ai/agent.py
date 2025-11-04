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
        jokes = sheets_service.get_jokes()
        district_synonyms = sheets_service.get_district_synonyms()
        
        return get_system_prompt(welcome, questions, objections, reactions, jokes, district_synonyms)

    async def _get_conversation_from_db(self, user_id):
        """Отримує конверсацію з БД"""
        async with async_session() as session:
            result = await session.execute(
                select(Conversation).where(Conversation.user_id == user_id)
            )
            return result.scalar_one_or_none()
    
    def _analyze_filters(self, filters):
        """
        Аналізує фільтри і визначає які питання вже покриті
        1 = ім'я
        2 = тип (квартира/будинок)
        3 = район
        4 = кімнатність
        5 = ремонт
        6 = бюджет
        """
        covered = []
        
        # Перевіряємо кожен фільтр і записуємо як покрите питання
        if filters.get("name"):
            covered.append(1)
        
        if filters.get("type"):
            covered.append(2)
        
        if filters.get("district"):
            covered.append(3)
        
        if filters.get("rooms"):
            covered.append(4)
        
        if filters.get("state") or filters.get("renovation"):
            covered.append(5)
        
        if filters.get("budget") or filters.get("price_min") or filters.get("price_max"):
            covered.append(6)
        
        return sorted(covered)
    
    def _normalize_district(self, district_name, synonyms):
        """Нормалізує назву району з використанням синонімів"""
        if not district_name or not synonyms:
            return district_name
        
        # Перевіряємо чи є синонім
        district_lower = district_name.lower().strip()
        if district_lower in synonyms:
            return synonyms[district_lower]
        
        return district_name
    
    async def process_message(self, user_id, user_message):
        """Обробляє повідомлення користувача через Claude AI"""
        conversation_record = await self._get_conversation_from_db(user_id)
        
        # Отримуємо синоніми районів
        district_synonyms = sheets_service.get_district_synonyms()
        
        if not conversation_record:
            messages_history = []
            filters = {}
            questions_asked = []
        else:
            messages_history = conversation_record.messages or []
            filters = conversation_record.filters or {}
            # Аналізуємо які питання вже покриті на основі філтрів
            questions_asked = self._analyze_filters(filters)
        
        # Отримуємо phone_number з бази
        phone_number = conversation_record.phone_number if conversation_record else None
        
        context = get_context_prompt(
            messages_history[-10:],
            filters,
            questions_asked,
            phone_number
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
            
            # Оновлюємо фільтри
            if result.get("filters"):
                for key, value in result["filters"].items():
                    if value is not None:
                        # Нормалізуємо назву району
                        if key == "district":
                            value = self._normalize_district(value, district_synonyms)
                        filters[key] = value
            
            # Аналізуємо нові фільтри і оновлюємо questions_asked
            questions_asked = self._analyze_filters(filters)
            
            # Також додаємо з відповіді AI якщо є
            ai_questions = result.get("questions_asked", [])
            if ai_questions:
                questions_asked = sorted(list(set(questions_asked + ai_questions)))
            
            # Перевіряємо чи є контакт в контексті
            has_phone = conversation_record and conversation_record.phone_number
            
            ready_for_contact = len(questions_asked) >= 5 or result.get("ready_for_contact", False)
            
            return {
                "response": result.get("response", "Вибачте, сталася помилка."),
                "filters": filters,
                "questions_asked": questions_asked,
                "ready_for_contact": ready_for_contact and not has_phone,
                "action": result.get("action"),
                "viewing_variants": result.get("viewing_variants", [])
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
