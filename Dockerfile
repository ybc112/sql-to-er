# 使用Python 3.9官方镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    graphviz \
    graphviz-dev \
    gcc \
    g++ \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 复制requirements文件
COPY sql_to_er/requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 创建必要的目录
RUN mkdir -p logs uploads sql_to_er/web_app/output/tmp

# 设置环境变量
ENV FLASK_ENV=production
ENV PYTHONPATH=/app:/app/sql_to_er:/app/sql_to_er/web_app

# 暴露端口
EXPOSE 5001

# 启动命令
CMD ["gunicorn", "-c", "gunicorn_config.py", "wsgi:application"]