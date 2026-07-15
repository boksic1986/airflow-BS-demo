ARG NGINX_IMAGE=nginx:1.30.3-alpine3.23
FROM node:20-alpine AS deps
WORKDIR /app
ARG VITE_DISPLAY_TIME_ZONE=Asia/Shanghai
ENV VITE_DISPLAY_TIME_ZONE=$VITE_DISPLAY_TIME_ZONE
COPY package*.json ./
RUN npm install

FROM deps AS test
COPY . .
RUN npm test -- --run

FROM deps AS build
COPY . .
RUN npm run build

FROM ${NGINX_IMAGE}
ARG NGINX_CONF=nginx.bs-nipt.conf
COPY ${NGINX_CONF} /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
EXPOSE 8080
