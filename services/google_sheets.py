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
        
        # Кеш для даних з Google Sheets
        self._cache = {
            'welcome': None,
            'questions': None,
            'objections': None,
            'reactions': None,
            'jokes': None,
            'silence': None,
            'districts': None,
            'synonyms': None
        }
        self._cache_loaded = False
    
    def _load_all_data(self):
        """Завантажує всі дані один раз"""
        if self._cache_loaded:
            return
        
        print("📄 Завантаження даних з Google Sheets...")
        
        self._cache['welcome'] = self._get_messages_from_column("Welcome")
        self._cache['questions'] = self._get_messages_from_column("Questions")
        self._cache['objections'] = self._get_messages_from_column("Objections")
        self._cache['reactions'] = self._get_messages_from_column("Reactions")
        self._cache['jokes'] = self._load_jokes()
        self._cache['silence'] = self._load_silence_responses()
        self._cache['districts'] = self._get_messages_from_column("Districts")
        self._cache['synonyms'] = self._load_district_synonyms()
        
        self._cache_loaded = True
        print("✅ Дані завантажено!")
    
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
        self._load_all_data()
        return self._cache['welcome']
    
    def get_questions(self):
        """Отримує питання з колонки B аркуша Questions"""
        self._load_all_data()
        return self._cache['questions']
    
    def get_objections(self):
        """Отримує заперечення з колонки B аркуша Objections"""
        self._load_all_data()
        return self._cache['objections']
    
    def get_reactions(self):
        """Отримує реакції з колонки B аркуша Reactions"""
        self._load_all_data()
        return self._cache['reactions']
    
    def get_districts(self):
        """Отримує список районів з колонки B аркуша Districts"""
        self._load_all_data()
        return self._cache['districts'] or []
    
    def _load_jokes(self):
        """Завантажує жарти з колонки B аркуша з назвою, що містить 'react' або 'joke'"""
        try:
            # Спробуємо різні варіанти назв
            for name in ["Reactions", "reactions", "Jokes", "jokes"]:
                try:
                    worksheet = self.sheet.worksheet(name)
                    # Отримуємо всі записи
                    all_values = worksheet.get_all_values()
                    
                    jokes = []
                    for row in all_values[1:]:  # Пропускаємо заголовок
                        if len(row) >= 2:  # Перевіряємо що є обидві колонки
                            trigger = row[0].strip().lower() if row[0] else ""
                            response = row[1].strip() if row[1] else ""
                            
                            # Шукаємо записи з тригером "joke" або "жарт"
                            if trigger in ["joke", "жарт"] and response:
                                jokes.append(response)
                    
                    if jokes:
                        return jokes
                except:
                    continue
            
            return []
        except Exception as e:
            print(f"Error loading jokes: {e}")
            return []
    
    def get_jokes(self):
        """Отримує жарти з кешу"""
        self._load_all_data()
        return self._cache['jokes'] or []
    
    def _load_silence_responses(self):
        """Завантажує відповіді на тригер silence з Google Sheets"""
        try:
            for name in ["Reactions", "reactions"]:
                try:
                    worksheet = self.sheet.worksheet(name)
                    all_values = worksheet.get_all_values()
                    
                    silence_responses = []
                    for row in all_values[1:]:
                        if len(row) >= 2:
                            trigger = row[0].strip().lower() if row[0] else ""
                            response = row[1].strip() if row[1] else ""
                            
                            if trigger == "silence" and response:
                                silence_responses.append(response)
                    
                    if silence_responses:
                        return silence_responses
                except:
                    continue
            
            return []
        except Exception as e:
            print(f"Error loading silence responses: {e}")
            return []
    
    def get_silence_responses(self):
        """Отримує відповіді на silence з кешу"""
        self._load_all_data()
        return self._cache['silence'] or []
    
    def _load_district_synonyms(self):
        """Завантажує синоніми районів з аркуша (колонка A = synonym, колонка B = official_name)"""
        try:
            for name in ["Districts", "districts", "synonym", "Synonym"]:
                try:
                    worksheet = self.sheet.worksheet(name)
                    all_values = worksheet.get_all_values()
                    
                    synonyms = {}
                    for row in all_values[1:]:
                        if len(row) >= 2:
                            synonym = row[0].strip() if row[0] else ""
                            official_name = row[1].strip() if row[1] else ""
                            
                            if synonym and official_name:
                                synonyms[synonym.lower()] = official_name
                    
                    if synonyms:
                        return synonyms
                except:
                    continue
            
            return {}
        except Exception as e:
            print(f"Error loading district synonyms: {e}")
            return {}
    
    def get_district_synonyms(self):
        """Отримує синоніми районів з кешу"""
        self._load_all_data()
        return self._cache['synonyms'] or {}
    
    def add_viewing_request(self, user_data):
        """
        Додає запис на перегляд в Google Sheets
        
        Args:
            user_data: dict з даними користувача
                - name: ім'я
                - phone: телефон
                - filters: фільтри пошуку
                - apartment_info: інформація про обрану квартиру (опціонально)
        """
        from datetime import datetime
        
        try:
            # Щукаємо аркуш Viewings, якщо немає - створюємо
            try:
                worksheet = self.sheet.worksheet("Viewings")
            except:
                # Створюємо новий аркуш
                worksheet = self.sheet.add_worksheet(title="Viewings", rows="1000", cols="20")
                # Додаємо заголовки
                worksheet.append_row([
                    "Дата/Час", "Ім'я", "Телефон", 
                    "Тип", "Район", "Кімнат", "Бюджет", "Ремонт",
                    "Обрана квартира"
                ])
            
            # Формуємо дані для запису
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            name = user_data.get('name', 'Не вказано')
            phone = user_data.get('phone', 'Не вказано')
            
            filters = user_data.get('filters', {})
            property_type = filters.get('type', '')
            district = filters.get('district', '')
            rooms = filters.get('rooms', '')
            budget = filters.get('budget', '')
            state = filters.get('state', '')
            
            apartment_info = user_data.get('apartment_info', '')
            
            # Додаємо рядок
            row = [
                now, name, phone,
                property_type, district, rooms, budget, state,
                apartment_info
            ]
            
            worksheet.append_row(row)
            print(f"✅ Додано запис на перегляд для {name} ({phone})")
            return True
            
        except Exception as e:
            print(f"❌ Error adding viewing request: {e}")
            return False

sheets_service = GoogleSheetsService()
