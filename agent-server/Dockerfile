FROM python:3.12-slim

WORKDIR /app

# Install SDK with agent extras
COPY ai-server-sdk/ /tmp/ai-server-sdk/
RUN pip install "/tmp/ai-server-sdk[agent]" --no-cache-dir

# Install server deps
COPY agent-server/requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir

COPY agent-server/ .

EXPOSE 8088
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8088"]
