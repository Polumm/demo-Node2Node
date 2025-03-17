FROM python:3.9

WORKDIR /app
COPY app.py .

RUN pip install fastapi uvicorn[standard]

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
