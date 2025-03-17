FROM python:3.9

WORKDIR /app
COPY app.py .

# Copy test files
COPY tests /app/tests

RUN pip install fastapi uvicorn[standard] pydantic pytest httpx requests

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8004"]
