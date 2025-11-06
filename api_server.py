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
        
        # Витягуємо дані з вебхука
        message_data = data.get("data", {})
        phone = message_data.get("phone")
        text = message_data.get("text")
        contact_id = message_data.get("contact_id")
        
        if not phone or not text:
            return JSONResponse({"status": "error", "message": "Missing data"}, status_code=400)
        
        # Використовуємо phone як user_id (або contact_id)
        user_id = int(contact_id) if contact_id else hash(phone)
        
        # Обробляємо повідомлення
        if text.strip().lower() in ["/start", "start", "старт"]:
            response = await MessageHandler.process_start_command(user_id, phone)
        else:
            response = await MessageHandler.process_text_message(user_id, text, phone)
        
        # Відправляємо відповідь через SendPulse
        bot_text = response.get("response", "")
        if bot_text:
            await sendpulse_client.send_message(phone, bot_text)
        
        # Обробка actions
        action = response.get("action")
        if action == "show_more":
            # TODO: відправка квартир
            pass
        elif action == "schedule_viewing":
            # TODO: запис на перегляд
            pass
        elif action == "call_manager":
            # TODO: виклик менеджера
            pass
        
        return JSONResponse({"status": "ok"})
        
    except Exception as e:
        logger.error(f"❌ Помилка обробки вебхука: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@app.get("/health")
async def health():
    """Перевірка здоров'я сервера"""
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
