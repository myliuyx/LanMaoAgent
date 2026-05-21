# 快速入门指南 / Quick Start Guide

[English](#english) | [中文](#中文)

---

## English

### Prerequisites

- Docker and Docker Compose installed
- OR Python 3.10+ and Node.js 18+ for manual setup
- PostgreSQL 15+ (if not using Docker)

### Option 1: Docker Compose (Recommended)

#### Step 1: Clone the Repository

```bash
git clone https://github.com/myliuyx/stock_project.git
cd stock_project
```

#### Step 2: Configure Backend

```bash
cd stock-fast-api
cp .env.example .env
```

Edit `.env` with your settings:

```bash
# Required
DB_HOST=your_postgres_host
DB_NAME=stock_db
DB_USER=stock_user
DB_PASSWORD=your_secure_password
JWT_SECRET_KEY=your_secret_key_at_least_32_characters

# Optional
DB_PORT=5432
CORS_ORIGINS=http://localhost:5173
```

#### Step 3: Initialize Database

```bash
# Connect to PostgreSQL and create database
psql -h <host> -U <user> -c "CREATE DATABASE stock_db;"

# Run DDL to create tables
psql -h <host> -U <user> -d stock_db -f docs/09_postgresql_ddl.sql
```

#### Step 4: Start Backend

```bash
docker-compose up -d
# Backend API available at http://localhost:8000
# API docs at http://localhost:8000/docs
```

#### Step 5: Build and Start Frontend

```bash
cd ../stock-front_ui

# Build Docker image
docker build -t stock-frontend .

# Run frontend
docker run -d -p 5173:80 --name stock-frontend stock-frontend

# Frontend available at http://localhost:5173
```

### Option 2: Manual Setup

#### Backend

```bash
cd stock-fast-api

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your database and JWT settings

# Initialize database
psql -h <host> -U <user> -d <dbname> -f docs/09_postgresql_ddl.sql

# Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend

```bash
cd stock-front_ui

npm install

npm run dev
# Visit http://localhost:5173
```

### First Login

1. Open http://localhost:5173
2. Login with default credentials (if configured):
   - Username: `admin`
   - Password: `admin123`
3. After login, you will be redirected to the Dashboard

### Verify Installation

```bash
# Test backend API
curl http://localhost:8000/api/v1/system/meta

# Expected response: {"code": 0, "message": "success", "data": {...}}
```

---

## 中文

### 环境要求

- 已安装 Docker 和 Docker Compose
- 或手动安装 Python 3.10+ 和 Node.js 18+
- PostgreSQL 15+（如不使用 Docker）

### 方式一：Docker Compose（推荐）

#### 步骤 1: 克隆代码

```bash
git clone https://github.com/myliuyx/stock_project.git
cd stock_project
```

#### 步骤 2: 配置后端

```bash
cd stock-fast-api
cp .env.example .env
```

编辑 `.env` 文件：

```bash
# 必填
DB_HOST=你的PostgreSQL主机
DB_NAME=stock_db
DB_USER=stock_user
DB_PASSWORD=你的安全密码
JWT_SECRET_KEY=你的密钥至少32字符

# 可选
DB_PORT=5432
CORS_ORIGINS=http://localhost:5173
```

#### 步骤 3: 初始化数据库

```bash
# 连接 PostgreSQL 并创建数据库
psql -h <主机> -U <用户> -c "CREATE DATABASE stock_db;"

# 执行 DDL 创建表
psql -h <主机> -U <用户> -d stock_db -f docs/09_postgresql_ddl.sql
```

#### 步骤 4: 启动后端

```bash
docker-compose up -d
# 后端 API 地址: http://localhost:8000
# API 文档: http://localhost:8000/docs
```

#### 步骤 5: 构建并启动前端

```bash
cd ../stock-front_ui

# 构建 Docker 镜像
docker build -t stock-frontend .

# 运行前端
docker run -d -p 5173:80 --name stock-frontend stock-frontend

# 前端地址: http://localhost:5173
```

### 方式二：手动部署

#### 后端

```bash
cd stock-fast-api

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入数据库和 JWT 配置

# 初始化数据库
psql -h <主机> -U <用户> -d <数据库名> -f docs/09_postgresql_ddl.sql

# 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 前端

```bash
cd stock-front_ui

npm install

npm run dev
# 访问 http://localhost:5173
```

### 首次登录

1. 打开 http://localhost:5173
2. 使用默认账号登录（如已配置）：
   - 用户名：`admin`
   - 密码：`admin123`
3. 登录后自动跳转到控制台

### 验证安装

```bash
# 测试后端 API
curl http://localhost:8000/api/v1/system/meta

# 预期响应: {"code": 0, "message": "success", "data": {...}}
```

### 下一步

- 查看 [用户使用指南](USER_GUIDE.md) 了解各功能使用方法
- 查看 [API 接口文档](../stock-fast-api/docs/REGISTRY.md) 了解 API 详情