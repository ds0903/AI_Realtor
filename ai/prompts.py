"""
Модуль для роботи з промптами з YAML файлу
"""
import yaml
import os
import json

class PromptsLoader:
    """Клас для завантаження промптів з YAML файлу"""
    
    def __init__(self, prompts_file='ai/prompts.yml'):
        """
        Ініціалізація завантажувача промптів
        
        Args:
            prompts_file: шлях до YAML файлу з промптами
        """
        self.prompts_file = prompts_file
        self.prompts = self._load_prompts()
    
    def _load_prompts(self):
        """Завантажує промпти з YAML файлу"""
        try:
            with open(self.prompts_file, 'r', encoding='utf-8') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            raise FileNotFoundError(f"Файл промптів не знайдено: {self.prompts_file}")
        except yaml.YAMLError as e:
            raise ValueError(f"Помилка парсингу YAML файлу: {e}")
    
    def get_system_prompt(self, welcome_messages, questions, objections, reactions, jokes=None, district_synonyms=None):
        """
        Генерує системний промпт для Claude агента
        
        Args:
            welcome_messages: список привітальних повідомлень
            questions: список питань (6 шт)
            objections: список відповідей на заперечення
            reactions: список реакцій на відповіді
            jokes: список жартів
            district_synonyms: словник синонімів районів
        
        Returns:
            str: системний промпт
        """
        # Форматуємо списки для промпта
        # Беремо ТІЛЬКИ перше привітання (українське)
        welcome_str = welcome_messages[0] if welcome_messages else "Вітаю вас!"
        questions_str = '\n'.join(f'{i+1}. {q}' for i, q in enumerate(questions))
        objections_str = ', '.join(objections[:3])
        reactions_str = ', '.join(reactions[:3])
        
        # Форматуємо жарти
        jokes = jokes or []
        jokes_str = '\n'.join(f'- {joke}' for joke in jokes) if jokes else "Немає жартів"
        
        # Форматуємо синоніми районів
        district_synonyms = district_synonyms or {}
        if district_synonyms:
            synonyms_str = '\n'.join(f'- "{syn}" = {official}' for syn, official in district_synonyms.items())
        else:
            synonyms_str = "Немає синонімів"
        
        # Отримуємо шаблон промпта з YAML
        template = self.prompts['system']['main_prompt']
        
        # Заповнюємо шаблон
        return template.format(
            welcome_messages=welcome_str,
            questions=questions_str,
            objections=objections_str,
            reactions=reactions_str,
            jokes=jokes_str,
            district_synonyms=synonyms_str
        )
    
    def get_context_prompt(self, conversation_history, filters, questions_asked, phone_number=None):
        """
        Генерує контекст для AI на основі історії розмови
        
        Args:
            conversation_history: історія повідомлень
            filters: зібрані фільтри
            questions_asked: задані питання
            phone_number: номер телефону
        
        Returns:
            str: контекст для промпта
        """
        template = self.prompts['context']['template']
        
        return template.format(
            conversation_history=json.dumps(conversation_history[-10:], ensure_ascii=False, indent=2),
            filters=json.dumps(filters, ensure_ascii=False),
            questions_asked=questions_asked,
            phone_number=phone_number if phone_number else "None"
        )
    
    def get_contact_request_message(self):
        """Повертає повідомлення запиту контакту"""
        return self.prompts['contact_request']['message']
    
    def get_success_message(self, api_success=True):
        """
        Повертає повідомлення після отримання контакту
        
        Args:
            api_success: чи успішний запит до API
        
        Returns:
            str: повідомлення успіху
        """
        if api_success:
            return self.prompts['success_message']['api_success']
        return self.prompts['success_message']['api_error']

# Глобальний екземпляр завантажувача
prompts_loader = PromptsLoader()

# Функції для зворотної сумісності
def get_system_prompt(welcome_messages, questions, objections, reactions, jokes=None, district_synonyms=None):
    """Отримує системний промпт"""
    return prompts_loader.get_system_prompt(welcome_messages, questions, objections, reactions, jokes, district_synonyms)

def get_context_prompt(conversation_history, filters, questions_asked, phone_number=None):
    """Отримує контекст промпт"""
    return prompts_loader.get_context_prompt(conversation_history, filters, questions_asked, phone_number)

def get_contact_request_message():
    """Отримує повідомлення запиту контакту"""
    return prompts_loader.get_contact_request_message()

def get_success_message(api_success=True):
    """Отримує повідомлення успіху"""
    return prompts_loader.get_success_message(api_success)
