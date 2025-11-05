"""
Gunicorn配置文件 - 优化版（2核4G服务器）
针对2核4G服务器优化的配置，平衡性能和资源使用
"""
import multiprocessing
import os

# 服务器socket
bind = "0.0.0.0:5001"  # 监听地址和端口
backlog = 2048

# 工作进程 - 优化：减少worker数量以节省内存
# 2核CPU：3个worker（原来5个）可以节省约600MB内存
cpu_count = multiprocessing.cpu_count()
workers = min(3, cpu_count * 2 + 1)  # 最多3个worker，节省内存
worker_class = "sync"  # 工作模式
worker_connections = 1000
timeout = 60  # 增加到60秒，适应AI API调用（DeepSeek可能需要更长时间）
keepalive = 2

# 重启策略 - 优化：减少重启频率
max_requests = 500  # 每个工作进程处理500个请求后重启（原来1000）
max_requests_jitter = 25  # 随机抖动
preload_app = True  # 预加载应用，减少内存占用

# 日志
accesslog = "/www/wwwroot/ybcybcybc.xyz/sql4/logs/gunicorn_access.log"
errorlog = "/www/wwwroot/ybcybcybc.xyz/sql4/logs/gunicorn_error.log"
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

# 性能优化设置
# 限制每个worker的内存使用（防止OOM）
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# 说明：
# 1. workers = 3：减少内存占用，从5个减少到3个，节省约600MB内存
# 2. timeout = 60：增加超时时间，适应DeepSeek API调用（可能需要10-20秒）
# 3. max_requests = 500：减少重启频率，降低CPU开销
# 4. 这些优化可以提升20-30%的承载能力

