# syntax=docker/dockerfile:1.7

FROM node:20-alpine AS build
WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend .

# Build arguments for version tracking
ARG VITE_API_URL=https://localhost:8000
ARG VITE_GIT_COMMIT=unknown
ARG VITE_GIT_BRANCH=unknown
ARG VITE_BUILD_TIME=unknown
ARG VITE_APP_VERSION=1.0.0

# Set as environment variables for Vite build
ENV VITE_API_URL=$VITE_API_URL \
    VITE_GIT_COMMIT=$VITE_GIT_COMMIT \
    VITE_GIT_BRANCH=$VITE_GIT_BRANCH \
    VITE_BUILD_TIME=$VITE_BUILD_TIME \
    VITE_APP_VERSION=$VITE_APP_VERSION

RUN npm run build

FROM nginx:1.27-alpine AS runtime
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/frontend/dist /usr/share/nginx/html
COPY docker/frontend-runtime-config.sh /docker-entrypoint.d/40-runtime-config.sh
RUN chmod +x /docker-entrypoint.d/40-runtime-config.sh

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
