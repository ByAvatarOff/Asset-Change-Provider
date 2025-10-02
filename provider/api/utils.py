from fastapi import APIRouter, HTTPException

router = APIRouter()



@router.post("/broadcast/config", response_model=dict)
async def add_broadcast_config(config: BroadcastConfig):
    """Добавляет конфигурацию для трансляции"""
    try:
        telegram_manager.add_broadcast_config(config)
        return {
            "status": "success",
            "message": f"Broadcast config added for chat: {config.chat_name}"
        }
    except Exception as e:
        logger.error(f"Error adding broadcast config: {e}")
        raise HTTPException(status_code=500, detail="Failed to add broadcast config")


@router.get("/broadcast/configs", response_model=dict[str, BroadcastConfig])
async def get_broadcast_configs():
    """Получает все конфигурации трансляции"""
    return telegram_manager.broadcast_configs


@router.delete("/broadcast/config/{chat_id}", response_model=dict)
async def remove_broadcast_config(chat_id: str):
    """Удаляет конфигурацию трансляции"""
    try:
        telegram_manager.remove_broadcast_config(chat_id)
        return {
            "status": "success",
            "message": f"Broadcast config removed for chat: {chat_id}"
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail="Chat configuration not found")


@router.put("/broadcast/config/{chat_id}/toggle", response_model=dict)
async def toggle_broadcast_config(chat_id: str):
    """Включает/выключает конфигурацию трансляции"""
    if chat_id not in telegram_manager.broadcast_configs:
        raise HTTPException(status_code=404, detail="Chat configuration not found")

    config = telegram_manager.broadcast_configs[chat_id]
    config.active = not config.active

    return {
        "status": "success",
        "chat_id": chat_id,
        "active": config.active
    }


@router.post("/broadcast/test-message", response_model=dict)
async def send_test_message(chat_id: str, message: str):
    """Отправляет тестовое сообщение в чат"""
    try:
        await telegram_manager.bot.send_message(
            chat_id=chat_id,
            text=f"🧪 Test message: {message}",
            parse_mode='HTML'
        )
        return {
            "status": "success",
            "message": "Test message sent successfully"
        }
    except Exception as e:
        logger.error(f"Failed to send test message: {e}")
        raise HTTPException(status_code=500, detail="Failed to send test message")