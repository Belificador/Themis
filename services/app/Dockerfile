FROM node:20-slim AS frontend
WORKDIR /src/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend ./
RUN npm run build

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY services/app/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY libs/egm_common /app/libs/egm_common
COPY services/app /app/services/app
COPY --from=frontend /src/frontend/dist /app/frontend/dist
ENV PYTHONPATH=/app/libs \
    FRONTEND_DIST=/app/frontend/dist

WORKDIR /app/services/app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
