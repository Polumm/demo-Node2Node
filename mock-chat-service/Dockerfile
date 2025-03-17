FROM python:3.9

WORKDIR /app
COPY app.py .

# websockets 9+ or 10+ is typically fine. 13.1 is stable.
RUN pip install fastapi uvicorn[standard] requests websockets==13.1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8002"]
