# Frontend: build the React app, then serve it with nginx.
# nginx also proxies /api to the backend, so the browser talks to one origin.
FROM node:22-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY . .
RUN npm run build


FROM nginx:1.27-alpine

# Rendered into /etc/nginx/conf.d/default.conf by the image's envsubst step.
ENV API_UPSTREAM=http://backend:8000

COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
  CMD wget -qO- http://127.0.0.1/ > /dev/null || exit 1
