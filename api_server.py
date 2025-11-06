"""
FastAPI сервер для обробки вебхуків SendPulse
"""
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from database import init_db
from message_handler import MessageHandler
from adapters.sendpulse import sendpulse_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Realtor API")

@app.on_event("startup")
async def startup():
    """Ініціалізація при старті"""
    await init_db()
    logger.info("✅ База даних ініціалізована")

@app.post("/webhook/sendpulse")
async def sendpulse_webhook(request: Request):
    """Обробка вебхука від SendPulse"""
    try:
        data = await request.json()
        logger.info(f"📥 SendPulse webhook: {data}")
        
        # SendPulse надсилає дані в різних форматах, обробляємо обидва
        # Формат 1: вкладений в "data"
        if "data" in data:
            message_data = data.get("data", {})
        else:
            # Формат 2: прямо в root
            message_data = data
        
        # Витягуємо інформацію
        contact = message_data.get("contact", {})
        message = message_data.get("message", {})
        
        # Отримуємо phone/contact_id
        phone = contact.get("phone") or contact.get("id")
        contact_id = contact.get("id")
        name = contact.get("name", "")
        
        # Отримуємо текст повідомлення
        text = message.get("text") or message_data.get("text") or data.get("text")
        
        logger.info(f"📱 Phone: {phone}, Contact: {contact_id}, Text: {text}")
        
        if not text:
            logger.error("❌ Немає тексту в повідомленні")
            return JSONResponse({"status": "error", "message": "No text"}, status_code=400)
        
        # Використовуємо contact_id як user_id
        user_id = int(contact_id) if contact_id and str(contact_id).isdigit() else hash(phone or "unknown")
        
        # Обробляємо повідомлення
        if text.strip().lower() in ["/start", "start", "старт", "привіт", "hi", "hello"]:
            response = await MessageHandler.process_start_command(user_id, name or phone)
        else:
            response = await MessageHandler.process_text_message(user_id, text, name or phone)
        
        bot_text = response.get("response", "")
        
        logger.info(f"🤖 AI відповідь: {bot_text[:200]}")
        
        # Відправляємо через SendPulse API
        if bot_text and phone:
            success = await sendpulse_client.send_message(phone, bot_text)
            if success:
                logger.info(f"✅ Повідомлення відправлено на {phone}")
            else:
                logger.error(f"❌ Не вдалося відправити на {phone}")
        
        return JSONResponse({"status": "ok"})
        
    except Exception as e:
        logger.error(f"❌ Помилка вебхука: {e}", exc_info=True)
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@app.post("/start")
async def start_api(request: Request):
    """Обробка API запиту від SendPulse (для блоку 'Запит API')"""
    try:
        data = await request.json()
        logger.info(f"📥 SendPulse API запит: {data}")
        
        command = data.get("command")
        user_id = data.get("user_id")
        user_name = data.get("user_name")
        
        if not user_id:
            return JSONResponse({"response": "Помилка: немає user_id"}, status_code=400)
        
        # Конвертуємо user_id в int
        try:
            user_id = int(user_id) if isinstance(user_id, str) else user_id
        except:
            user_id = hash(str(user_id))
        
        # Обробка команди
        if command == "start" or command == "/start":
            ai_response = await MessageHandler.process_start_command(user_id, user_name)
        else:
            text = data.get("text", command)
            ai_response = await MessageHandler.process_text_message(user_id, text, user_name)
        
        bot_text = ai_response.get("response", "Помилка обробки")
        
        logger.info(f"🤖 AI відповідь: {bot_text[:100]}")
        
        # Повертаємо ТІЛЬКИ response як просту строку в JSON
        return {"response": bot_text}
        
    except Exception as e:
        logger.error(f"❌ Помилка API: {e}")
        return {"response": f"Помилка: {str(e)}"}

@app.get("/health")
async def health():
    """Перевірка здоров'я сервера"""
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
