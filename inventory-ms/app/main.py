import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import faust
import uuid
import logging

app = FastAPI()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("inventory-ms")

class OrderEvent(faust.Record):
    event_type: str
    correlation_id: str
    order: dict

class InventoryEvent(faust.Record):
    event_type: str
    correlation_id: str
    order: dict
    inventory_response: dict

faustApp = faust.App('inventory_app', broker='kafka://kafka:9092')
order_topic = faustApp.topic('order_events', value_type=OrderEvent)
inventory_topic = faustApp.topic('inventory_events', value_type=InventoryEvent)

inventory = [{
    "item_id": 1
}]

# Run the Faust worker in the background when FastAPI starts
@app.on_event("startup")
async def start_faust_worker():
    await faustApp.start()


@faustApp.agent(order_topic)
async def process_order(orders):
    async for order in orders:
        logger.info(order.event_type)
        if order.event_type == 'OrderPlaced':
            item_id = order.order['inventory_info'].get("item_id")
            if inventory[0].get("item_id") == item_id:
                inventory_response = {"status": "available"}
                event_data = InventoryEvent(
                    event_type='InventoryChecked',
                    correlation_id=order.correlation_id,
                    order=order.order,
                    inventory_response=inventory_response
                )
                await inventory_topic.send(value=event_data)
                logger.info(f"Inventory checked for order correlation id:  {order.correlation_id}")
            else:
                event_data = InventoryEvent(
                    event_type='UnavailableStock',
                    correlation_id=order.correlation_id,
                    order=order.order,
                    inventory_response={"message":"Out of stock"}
                )
                await inventory_topic.send(value=event_data)


