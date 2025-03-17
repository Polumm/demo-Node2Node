FROM python:3.9

WORKDIR /app
COPY app.py .

# Copy test files
COPY tests /app/tests

# websockets 9+ or 10+ is typically fine. 13.1 is stable.
RUN pip install fastapi uvicorn[standard] requests websockets==13.1 pytest httpx requests

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8002"]
