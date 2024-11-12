import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import faust
import uuid
import logging

app = FastAPI()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("order-ms")

class Order(BaseModel):
    user_info: dict
    inventory_info: dict
    payment_info: dict
    order_bill_info: dict

class OrderEvent(faust.Record):
    event_type: str
    correlation_id: str
    order: dict


class InventoryEvent(faust.Record):
    event_type: str
    correlation_id: str
    order: dict
    inventory_response: dict


class PaymentEvent(faust.Record):
    event_type: str
    correlation_id: str
    order: dict
    payment_response: dict

faustApp = faust.App('order_app', broker='kafka://kafka:9092')
order_topic = faustApp.topic('order_events', value_type=OrderEvent)
inventory_topic = faustApp.topic('inventory_events', value_type=InventoryEvent)
payment_topic = faustApp.topic('payment_events', value_type=PaymentEvent)

# Run the Faust worker in the background when FastAPI starts
@app.on_event("startup")
async def start_faust_worker():
    await faustApp.start()
    

created_orders = []
failed_orders = []


@app.post("/create_order")
async def create_order(order: Order):
    correlation_id = str(uuid.uuid4())
    event_data = OrderEvent(
        event_type='OrderPlaced',
        correlation_id=correlation_id,
        order=order.model_dump()
    )
    try:
        sent = await order_topic.send(value=event_data)
        await sent
        logger.info(f"order placed, corrleation id:{event_data.correlation_id} status: {sent}")
    except Exception:
        logger.info(f"kafka producer failed")
    return {"message": "Order placed", "correlation_id": correlation_id}


@faustApp.agent(inventory_topic)
async def process_inventory_topic(orders):
    async for order in orders:
        if order.event_type == 'UnavailableStock':
            failed_orders.append({
                "correlation_id": order.correlation_id,
                "reason": "Out of stock",
                "order_data": order.order
            })
            logger.info(f"failed order: {order}")
            
@faustApp.agent(payment_topic)
async def process_payment_topic(orders):
    async for order in orders:
        if order.event_type == 'PaymentAuthorized':
            created_orders.append({
                "correlation_id": order.correlation_id,
                "payment_response": order.payment_response,
                "order_data": order.order
            })
            logger.info(f"created order: {order}")
        elif order.event_type == 'PaymentDeclined':
            failed_orders.append({
                "correlation_id": order.correlation_id,
                "payment_response": order.payment_response,
                "order_data": order.order
            })
            logger.info(f"failed order: {order}")


