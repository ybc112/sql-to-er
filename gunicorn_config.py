"""
Gunicorn配置文件
用于宝塔面板Python项目部署
"""
import multiprocessing
import os

# 服务器socket
bind = "0.0.0.0:5001"  # 监听地址和端口
backlog = 2048

# 工作进程
workers = multiprocessing.cpu_count() * 2 + 1  # 推荐的工作进程数
worker_class = "sync"  # 工作模式
worker_connections = 1000
timeout = 30
keepalive = 2

# 重启
max_requests = 1000  # 每个工作进程处理请求的最大数量
max_requests_jitter = 50  # 随机抖动
preload_app = True  # 预加载应用

# 日志
accesslog = "/www/wwwroot/ybcybcybc.xyz/sql4/logs/gunicorn_access.log"  # 访问日志
errorlog = "/www/wwwroot/ybcybcybc.xyz/sql4/logs/gunicorn_error.log"   # 错误日志
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# 进程命名
proc_name = "sql_to_er_app"

# 用户和组（如果需要）
# user = "www"
# group = "www"

# 其他设置
daemon = False  # 不要设为True，宝塔会管理进程
pidfile = "/www/wwwroot/ybcybcybc.xyz/sql4/logs/gunicorn.pid"
tmp_upload_dir = None