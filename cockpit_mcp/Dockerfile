FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    COCKPIT_DATA_BASE_URL=https://vitzz86.github.io \
    COCKPIT_REMOTE_CACHE_SECONDS=30

WORKDIR /app

COPY cockpit_mcp/requirements.txt /app/cockpit_mcp/requirements.txt
RUN pip install --no-cache-dir -r /app/cockpit_mcp/requirements.txt \
    && useradd --create-home --uid 10001 cockpit

COPY cockpit_mcp /app/cockpit_mcp
COPY data.json scores.json charts.json /app/

USER cockpit
EXPOSE 8790

CMD ["python", "-m", "uvicorn", "cockpit_mcp.http_app:app", "--host", "0.0.0.0", "--port", "8790", "--proxy-headers"]
