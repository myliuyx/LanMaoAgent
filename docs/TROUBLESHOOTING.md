# 故障排查指南 / Troubleshooting Guide

本文档汇集常见问题及解决方案。

---

## 1. 后端启动问题

### 1.1 后端无法启动

**症状**：服务无法启动，容器或进程立即退出。

**排查步骤**：

```bash
# 查看日志
docker logs stock-api

# 检查环境变量
echo $DB_HOST
echo $DB_PORT
echo $DB_USER
echo $DB_PASSWORD
```

**常见原因**：

| 原因 | 解决方案 |
|------|---------|
| 环境变量未设置 | 在 `.env` 文件中配置所有必填变量 |
| 数据库连接失败 | 检查 DB_HOST 是否可达，数据库是否启动 |
| 端口 8000 被占用 | 修改 `docker-compose.yml` 中的端口映射 |

**验证命令**：

```bash
# 测试数据库连接
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT 1"

# 测试 API 健康检查
curl http://localhost:8000/
```

---

### 1.2 数据库连接被拒绝

**症状**：日志显示 `connection refused` 或 `could not connect to server`。

**排查**：

1. 确认 PostgreSQL 已启动：`pg_isready -h $DB_HOST -p $DB_PORT`
2. 确认数据库存在：`psql -h $DB_HOST -U $DB_USER -l | grep stock_db`
3. 确认用户权限：`psql -h $DB_HOST -U $DB_USER -d stock_db -c "SELECT 1"`

---

## 2. 前端问题

### 2.1 前端返回 502 Bad Gateway

**症状**：访问前端时所有 API 请求返回 502。

**排查步骤**：

```bash
# 1. 检查后端是否正常运行
docker logs stock-api

# 2. 检查后端容器网络
docker exec stock-frontend ping stock-api

# 3. 查看 Nginx 错误日志
docker exec stock-frontend cat /var/log/nginx/error.log
```

**常见原因**：

| 原因 | 解决方案 |
|------|---------|
| 后端未启动 | 启动后端服务 |
| 容器网络不通 | 检查 `docker-compose.yml` 中的 `depends_on` 和网络配置 |
| Nginx 配置错误 | 检查 `nginx.conf` 中的 `proxy_pass` 地址 |

**Nginx 代理检查**：

```nginx
location /api/ {
    proxy_pass http://stock-api:8000/api/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

---

### 2.2 前端页面空白

**排查**：

1. 检查浏览器控制台错误
2. 检查 Nginx 是否正确提供静态文件：`docker exec stock-frontend ls -la /usr/share/nginx/html/`
3. 检查 `index.html` 是否存在

---

## 3. 数据库问题

### 3.1 数据库迁移失败

**症状**：表创建失败或部分表不存在。

**排查**：

```bash
# 连接数据库
psql -h $DB_HOST -U $DB_USER -d $DB_NAME

# 查看所有表
\dt

# 执行迁移脚本（如需要重新运行）
\i docs/09_postgresql_ddl.sql
```

**验证脚本执行结果**：

```sql
-- 检查表数量
SELECT count(*) FROM information_schema.tables
WHERE table_schema = 'public';

-- 预期：16 张表
```

---

### 3.2 数据不同步

**症状**：数据库中有数据但查询结果为空，或数据日期不是最新。

**排查**：

1. 确认当前是否为交易日（工作日 9:30-15:00）
2. 检查 ETL 任务是否正常运行：`GET /api/v1/jobs?status=RUNNING`
3. 检查数据覆盖情况：`GET /api/v1/coverage`
4. 手动触发同步任务

---

## 4. ETL 任务问题

### 4.1 任务执行失败

**排查步骤**：

```bash
# 1. 查看任务状态
GET /api/v1/jobs?status=FAILED

# 2. 查看任务详情
GET /api/v1/jobs/{job_id}

# 3. 查看任务日志
GET /api/v1/jobs/{job_id}/logs?offset=0&limit=100
```

**常见错误及解决方案**：

| 错误类型 | 可能原因 | 解决方案 |
|---------|---------|---------|
| 数据源连接失败 | baostock API 不可用 | 检查网络连接，等待恢复 |
| 断点续传失败 | 检查点数据损坏 | 使用 `force_restart=true` 重新执行 |
| 写入冲突 | 并发写入同一表 | 任务本身有锁机制，如持续出现请联系开发者 |

---

### 4.2 任务长时间运行

**排查**：

1. 检查任务开始时间是否合理
2. 查看日志确认是否有进展
3. 检查数据量是否异常大

---

### 4.3 断点续传不生效

**原因**：检查点表 `etl_checkpoint` 数据损坏或被清除。

**解决方案**：

```bash
# 强制从头开始
POST /api/v1/jobs/sync-daily?trade_date=2026-04-30&force_restart=true
```

---

## 5. 认证问题

### 5.1 登录失败

**排查**：

1. 确认用户名密码正确
2. 检查 JWT_SECRET_KEY 是否配置
3. 查看后端日志是否有认证相关错误

**测试认证**：

```bash
# 获取 token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your_password"}'

# 使用 token 访问受保护接口
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/dashboard/summary
```

---

### 5.2 Token 过期

**症状**：API 返回 401 Unauthorized。

**解决方案**：重新登录获取新 token。

---

## 6. 数据质量问题

### 6.1 数据缺失

**排查**：

```bash
# 查看数据覆盖情况
GET /api/v1/coverage

# 检查特定股票的数据范围
GET /api/v1/stocks/coverage?symbol=600519.SH
```

**补数据方法**：使用回补功能 `POST /api/v1/backfill/run`

---

### 6.2 数据错误

如果发现数据明显错误（如价格异常、涨跌幅超限）：

1. 检查数据源是否正常
2. 任务是否正常完成无报错
3. 反馈给开发团队排查

---

## 7. 常见错误码

| 错误码 | 说明 | 可能原因 |
|--------|------|---------|
| `code: 1001` | 未授权 | 未登录或 token 过期 |
| `code: 1002` | 参数错误 | 请求参数格式或值不正确 |
| `code: 1003` | 资源不存在 | 查询的数据不存在 |
| `code: 2001` | 任务不存在 | ETL 任务 ID 不存在 |
| `code: 2002` | 任务执行中 | 任务正在运行无法重复触发 |
| `code: 2003` | 任务失败 | ETL 任务执行失败，详见 error_message |
| `code: 3001` | 数据库错误 | 数据库操作失败 |

---

## 8. 日志文件位置

| 组件 | 日志位置 | 说明 |
|------|---------|------|
| 后端服务 | `/app/logs/` 或容器日志 | ETL 任务执行日志 |
| Nginx | `/var/log/nginx/error.log` | 前端代理错误日志 |
| 数据库 | PostgreSQL 配置指定目录 | 数据库操作日志 |

---

## 9. 相关文档

- [快速入门指南](QUICK_START.md)
- [部署指南](DEPLOYMENT.md)
- [用户使用指南](USER_GUIDE.md)
- [定时任务使用文档](../stock-fast-api/docs/定时任务使用文档.md)
- [API 接口文档](../stock-fast-api/docs/REGISTRY.md)