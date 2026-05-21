# ========== Stage 1: Build ==========
FROM node:20-slim AS builder

WORKDIR /app

# 安装依赖（利用 Docker 缓存层）
COPY package.json package-lock.json* ./
RUN npm ci

# 复制源代码
COPY . .

# 构建生产版本
# VITE_API_BASE_URL 在 .env.production 中已设为 /api/v1
RUN npm run build

# ========== Stage 2: Serve with Nginx ==========
FROM nginx:alpine

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制 Nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
