# ===== 编译阶段 =====
FROM python:3.11-slim as builder

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
    PIP_MIRROR=https://pypi.tuna.tsinghua.edu.cn/simple

COPY requirements.txt .
# 使用国内镜像加速，多线程安装
RUN pip install --root-user-action=ignore -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# ===== 运行阶段 =====
FROM python:3.11-slim

# 安全：非 root 运行
RUN groupadd -r appgroup && useradd -r -g appgroup appuser
WORKDIR /app

# 只拷贝依赖产物，不含编译工具链
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY . .

RUN chown -R appuser:appgroup /app

# efinance 需要在 site-packages 下创建 data/ 目录，提前创建并授权
RUN mkdir -p /usr/local/lib/python3.11/site-packages/efinance/data && \
    chown -R appuser:appgroup /usr/local/lib/python3.11/site-packages/efinance/data

USER appuser
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]