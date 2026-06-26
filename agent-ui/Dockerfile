FROM node:20-alpine AS builder
WORKDIR /app
COPY agent-ui/package*.json ./
RUN npm ci
COPY agent-ui/ .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY agent-ui/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
