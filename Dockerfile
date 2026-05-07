FROM node:22-bookworm AS frontend-build

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend ./
RUN npm run build
RUN npm prune --omit=dev


FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV NODE_ENV=production

RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    nodejs \
    npm \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 user
WORKDIR /home/user/app

COPY --chown=user:user requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY --chown=user:user . .

COPY --from=frontend-build --chown=user:user /app/frontend/.next ./frontend/.next
COPY --from=frontend-build --chown=user:user /app/frontend/public ./frontend/public
COPY --from=frontend-build --chown=user:user /app/frontend/package*.json ./frontend/
COPY --from=frontend-build --chown=user:user /app/frontend/node_modules ./frontend/node_modules

COPY docker/nginx.conf /etc/nginx/nginx.conf
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 7860

CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
