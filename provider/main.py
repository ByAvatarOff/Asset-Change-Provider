from fastapi import FastAPI

from provider.api.utils import router




app = FastAPI(title="Crypto News Broadcaster", version="1.0.0")
app.include_router(router)


#
# @app.on_event("startup")
# async def startup_event():
#     await telegram_manager.initialize()
#     await rabbitmq_consumer.connect()
#
#     # Запуск потребителя в фоновом режиме
#     asyncio.create_task(rabbitmq_consumer.start_consuming())
#
#
# @app.on_event("shutdown")
# async def shutdown_event():
#     await rabbitmq_consumer.close()



if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)