FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY icm ./icm

RUN pip install --no-cache-dir -e .

RUN mkdir -p data/logs data/sources data/tmp

COPY docker/backend-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "icm/business/api"]
