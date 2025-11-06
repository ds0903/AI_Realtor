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
    
    async def get_token(self):
        """Отримання access token"""
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
            else:
                logger.error(f"❌ Помилка отримання токену: {response.text}")
    
    async def send_message(self, phone: str, text: str):
        """Відправка повідомлення через SendPulse"""
        if not self.token:
            await self.get_token()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_url}/whatsapp/contacts/sendByPhones",
                headers={"Authorization": f"Bearer {self.token}"},
                json={
                    "phones": [phone],
                    "message": text
                }
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Повідомлення відправлено на {phone}")
                return True
            else:
                logger.error(f"❌ Помилка відправки: {response.text}")
                return False

sendpulse_client = SendPulseClient()
