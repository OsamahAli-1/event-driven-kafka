from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import faust
import uuid
import logging

app = FastAPI()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("payment-ms")

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

faustApp = faust.App('payment_app', broker='kafka://kafka:9092')
payment_topic = faustApp.topic('payment_events', value_type=PaymentEvent)
inventory_topic = faustApp.topic('inventory_events', value_type=InventoryEvent)

# Run the Faust worker in the background when FastAPI starts
@app.on_event("startup")
async def start_faust_worker():
    await faustApp.start()

cards = [{
    "card_number": 1
}]

@faustApp.agent(inventory_topic)
async def process_order(orders):
    async for order in orders:
        logger.info(order)
        if order.event_type == 'InventoryChecked':
            card_number = order.order['payment_info'].get("card_number")
            if cards[0]["card_number"] == card_number:
                payment_response = {"status": "authrized"}
                event_data = PaymentEvent(
                    event_type='PaymentAuthorized',
                    correlation_id=order.correlation_id,
                    order=order.order,
                    payment_response=payment_response
                )
                await payment_topic.send(value=event_data)
                logger.info(f"payment authorized for order correlation id: {order.correlation_id}")
            else:
                event_data = PaymentEvent(
                    event_type='PaymentDeclined',
                    correlation_id=order.correlation_id,
                    order=order.order,
                    payment_response={"message:Payment declined"}
                )
                await payment_topic.send(value=event_data)


