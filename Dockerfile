# copyright by berlonak
# telegram: @Kilax123
# Only the web application is included. Never bake private Telegram exports into the image.
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY pyproject.toml README.md LICENSE NOTICE ./
COPY tgarchive ./tgarchive
RUN pip install --no-cache-dir . && useradd --system --uid 10001 --home /nonexistent --shell /usr/sbin/nologin archive
USER 10001:10001
EXPOSE 8000
CMD ["uvicorn", "tgarchive.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-proxy-headers"]
