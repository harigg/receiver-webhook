FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared lib
COPY ../shared/lib /app/shared/lib

# Copy agents
COPY ../agents /app/agents

# Copy webhook receiver
COPY . /app/webhook-receiver

WORKDIR /app/webhook-receiver

EXPOSE 8080

CMD ["python", "main.py"]
