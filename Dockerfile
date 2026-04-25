FROM python:3.12-alpine
WORKDIR /app
RUN apk add --no-cache --virtual .build-deps gcc musl-dev linux-headers \
    && pip install --no-cache-dir mcp docker uvicorn \
    && apk del .build-deps \
    && rm -rf /root/.cache
COPY server.py .
EXPOSE 8000
ENV PYTHONUNBUFFERED=1
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
