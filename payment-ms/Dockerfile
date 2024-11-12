FROM python:3.11

WORKDIR /app

COPY ./app /app

RUN pip install fastapi uvicorn faust-streaming

CMD ["sh", "-c", "faust -A main:faustApp worker -l info & uvicorn main:app --host 0.0.0.0 --port 8002 --reload"]
