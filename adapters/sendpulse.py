"""
SendPulse через прямий Telegram Bot API
"""
import httpx
import logging
import config

logger = logging.getLogger(__name__)

class SendPulseClient:
    """Відправка через Telegram Bot API напряму"""
    
    def __init__(self):
        # Bot token з SendPulse (з логів бачу bot_id: 690c7c3d6624a67cdb05a513)
        # Це ds0903_bot з токеном: 8441270675:AAGfOb3bTu_brfhj5OBAViV8yxfxnyx14DA
        self.bot_token = "8441270675:AAGfOb3bTu_brfhj5OBAViV8yxfxnyx14DA"
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    async def send_telegram_message(self, chat_id: str, text: str):
        """Відправка через Telegram Bot API"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": text
                    }
                )
                
                if response.status_code == 200:
                    logger.info(f"✅ Повідомлення відправлено в chat {chat_id}")
                    return True
                else:
                    logger.error(f"❌ Помилка відправки: {response.text}")
                    return False
        except Exception as e:
            logger.error(f"❌ Exception: {e}")
            return False

sendpulse_client = SendPulseClient()
