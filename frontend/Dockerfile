FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/templates/default.conf.template

# Defaults so the container starts even when env vars aren't provided
# (e.g. plain `docker run` or docker-compose without overrides).
# BACKEND_URL default matches the docker-compose service name.
ENV PORT=10000 \
    BACKEND_URL=http://sentinel-backend:8000

EXPOSE 10000
CMD ["nginx", "-g", "daemon off;"]
