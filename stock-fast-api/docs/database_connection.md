# 数据库连接规范文档 (Database Connection Specification)

## 1. 数据库基本信息
* **类型**: PostgreSQL
* **主机 (Host)**: `127.0.0.1`
* **端口 (Port)**: `5432`
* **数据库名称 (Database)**: `stock_cache_system`

## 2. 访问凭据 (Credentials)
> **注意**：此文档包含敏感信息，请勿上传至公开仓库。

* **管理员用户名 (User)**: `postgres`
* **管理员密码 (Password)**: `H7k9P2mX5wR1` (2026-04-16 重置)

## 3. 开发规范

### 3.1 环境变量管理 (推荐)
在生产或长期开发环境中，**严禁**将密码硬编码在代码中。建议在项目根目录创建 `.env` 文件：

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=stock_cache_system
DB_USER=postgres
DB_PASS=H7k9P2mX5wR1
```

### 3.2 Python 连接示例 (使用 psycopg2)
```python
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS")
    )
```

### 3.3 权限说明
* **ETL 账号**: 目前统一使用 `postgres` 管理员账号。
* **后续规划**: 建议为 ETL 流程创建一个受限的 `stock_etl` 用户，仅授予 `SELECT`, `INSERT`, `UPDATE` 权限，以符合最小权限原则。
