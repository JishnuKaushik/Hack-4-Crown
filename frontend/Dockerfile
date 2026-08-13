# UNVERIFIED: not build-tested (no Docker available in the dev environment
# this was written in). Review/test before relying on it for a real deploy.
#   docker build -t civiclens-frontend .   (run from frontend/)
FROM node:20-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# VITE_* vars are baked into the bundle at build time, not read at runtime —
# pass them as build args if they differ from .env.example's defaults.
ARG VITE_API_BASE_URL=http://localhost:8000/api/v1
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
