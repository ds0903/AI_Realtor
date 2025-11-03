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
    
    def get_system_prompt(self, welcome_messages, questions, objections, reactions):
        """
        Генерує системний промпт для Claude агента
        
        Args:
            welcome_messages: список привітальних повідомлень
            questions: список питань (6 шт)
            objections: список відповідей на заперечення
            reactions: список реакцій на відповіді
        
        Returns:
            str: системний промпт
        """
        # Форматуємо списки для промпта
        welcome_str = '\n'.join(f'- {msg}' for msg in welcome_messages)
        questions_str = '\n'.join(f'{i+1}. {q}' for i, q in enumerate(questions))
        objections_str = ', '.join(objections[:3])
        reactions_str = ', '.join(reactions[:3])
        
        # Отримуємо шаблон промпта з YAML
        template = self.prompts['system']['main_prompt']
        
        # Заповнюємо шаблон
        return template.format(
            welcome_messages=welcome_str,
            questions=questions_str,
            objections=objections_str,
            reactions=reactions_str
        )
    
    def get_context_prompt(self, conversation_history, filters, questions_asked):
        """
        Генерує контекст для AI на основі історії розмови
        
        Args:
            conversation_history: історія повідомлень
            filters: зібрані фільтри
            questions_asked: задані питання
        
        Returns:
            str: контекст для промпта
        """
        template = self.prompts['context']['template']
        
        return template.format(
            conversation_history=json.dumps(conversation_history[-10:], ensure_ascii=False, indent=2),
            filters=json.dumps(filters, ensure_ascii=False),
            questions_asked=questions_asked
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
def get_system_prompt(welcome_messages, questions, objections, reactions):
    """Отримує системний промпт"""
    return prompts_loader.get_system_prompt(welcome_messages, questions, objections, reactions)

def get_context_prompt(conversation_history, filters, questions_asked):
    """Отримує контекст промпт"""
    return prompts_loader.get_context_prompt(conversation_history, filters, questions_asked)

def get_contact_request_message():
    """Отримує повідомлення запиту контакту"""
    return prompts_loader.get_contact_request_message()

def get_success_message(api_success=True):
    """Отримує повідомлення успіху"""
    return prompts_loader.get_success_message(api_success)
