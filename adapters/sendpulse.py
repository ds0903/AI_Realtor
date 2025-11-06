"""
SendPulse API клієнт
"""
import httpx
import logging
import config

logger = logging.getLogger(__name__)

class SendPulseClient:
    """Клієнт для роботи з SendPulse API"""
    
    def __init__(self):
        self.api_url = "https://api.sendpulse.com"
        self.client_id = config.SENDPULSE_CLIENT_ID
        self.client_secret = config.SENDPULSE_CLIENT_SECRET
        self.token = None
        self.bot_id = None
    
    async def get_token(self):
        """Отримання access token"""
        if not self.client_id or not self.client_secret:
            logger.error("❌ SENDPULSE_CLIENT_ID або SENDPULSE_CLIENT_SECRET не налаштовано!")
            return False
            
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_url}/oauth/access_token",
                json={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret
                }
            )
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                logger.info("✅ SendPulse token отримано")
                return True
            else:
                logger.error(f"❌ Помилка отримання токену: {response.text}")
                return False
    
    async def get_bot_id(self):
        """Отримання ID бота"""
        if not self.token:
            await self.get_token()
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/telegram/bots",
                headers={"Authorization": f"Bearer {self.token}"}
            )
            
            if response.status_code == 200:
                bots = response.json()
                if bots and len(bots) > 0:
                    self.bot_id = bots[0].get("id")
                    logger.info(f"✅ Bot ID: {self.bot_id}")
                    return True
            else:
                logger.error(f"❌ Помилка отримання bot ID: {response.text}")
                return False
    
    async def send_telegram_message(self, chat_id: str, text: str):
        """Відправка повідомлення через SendPulse Telegram"""
        if not self.token:
            await self.get_token()
        
        if not self.bot_id:
            await self.get_bot_id()
        
        if not self.bot_id:
            logger.error("❌ Не вдалося отримати bot_id")
            return False
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_url}/telegram/contacts/sendText",
                headers={"Authorization": f"Bearer {self.token}"},
                json={
                    "bot_id": self.bot_id,
                    "contact_id": chat_id,
                    "text": text
                }
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Повідомлення відправлено в chat {chat_id}")
                return True
            else:
                logger.error(f"❌ Помилка відправки: {response.text}")
                return False

sendpulse_client = SendPulseClient()
