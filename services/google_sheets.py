"""
Сервіс для роботи з Google Sheets
"""
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import config

class GoogleSheetsService:
    """Клас для роботи з Google Sheets API"""
    
    def __init__(self):
        self.scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        self.creds = ServiceAccountCredentials.from_json_keyfile_name(
            config.GOOGLE_CREDENTIALS_FILE,
            self.scope
        )
        self.client = gspread.authorize(self.creds)
        self.sheet = self.client.open_by_key(config.GOOGLE_SHEET_ID)
    
    def _get_messages_from_column(self, worksheet_name, column=2):
        """
        Отримує повідомлення з колонки B (2) таблиці
        
        Args:
            worksheet_name: назва аркуша
            column: номер колонки (2 = B, де знаходяться тексти)
        
        Returns:
            list: список текстів повідомлень
        """
        try:
            worksheet = self.sheet.worksheet(worksheet_name)
        except:
            # Пробуємо з великої літери
            worksheet_name_capitalized = worksheet_name.capitalize()
            worksheet = self.sheet.worksheet(worksheet_name_capitalized)
        
        # Читаємо колонку B (2) де знаходяться тексти
        values = worksheet.col_values(column)
        
        # Пропускаємо заголовок (перший рядок) і порожні клітинки
        messages = []
        for i, value in enumerate(values):
            if i == 0:  # Пропускаємо заголовок
                continue
            if value and value.strip():  # Тільки непорожні
                messages.append(value.strip())
        
        return messages
        
    def get_welcome_messages(self):
        """Отримує привітальні повідомлення з колонки B аркуша Welcome"""
        return self._get_messages_from_column("Welcome")
    
    def get_questions(self):
        """Отримує питання з колонки B аркуша Questions"""
        return self._get_messages_from_column("Questions")
    
    def get_objections(self):
        """Отримує заперечення з колонки B аркуша Objections"""
        return self._get_messages_from_column("Objections")
    
    def get_reactions(self):
        """Отримує реакції з колонки B аркуша Reactions"""
        return self._get_messages_from_column("Reactions")
    
    def get_districts(self):
        """Отримує список районів з колонки B аркуша Districts"""
        try:
            return self._get_messages_from_column("Districts")
        except:
            return []

sheets_service = GoogleSheetsService()
