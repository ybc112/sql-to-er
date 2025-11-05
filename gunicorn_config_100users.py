"""
Gunicorn配置文件 - 每天100用户优化版
针对每天100人访问量的服务器配置优化
适用于2核2GB或2核4GB服务器
"""
import multiprocessing
import os

# 服务器socket
bind = "0.0.0.0:5001"
backlog = 512  # 降低backlog，节省内存

# 工作进程配置 - 针对100人/天优化
# 平均并发2-5人，峰值10-15人
workers = 2  # 2个worker足够处理峰值并发
worker_class = "sync"  # sync模式最稳定，适合CPU密集型任务
worker_connections = 500  # 降低连接数
timeout = 90  # 增加超时时间，适应复杂ER图渲染
keepalive = 2

# 重启策略 - 防止内存泄漏
max_requests = 300  # 每300个请求重启worker
max_requests_jitter = 50  # 随机抖动
preload_app = True  # 预加载应用，共享内存

# 日志配置
accesslog = "/www/wwwroot/ybcybcybc.xyz/sql4/logs/gunicorn_access.log"
errorlog = "/www/wwwroot/ybcybcybc.xyz/sql4/logs/gunicorn_error.log"
loglevel = "warning"  # 降低日志级别，减少IO
access_log_format = '%(h)s "%(r)s" %(s)s %(b)s %(D)s'  # 简化日志格式

# 进程管理
proc_name = "sql_to_er_100users"
daemon = False
pidfile = "/www/wwwroot/ybcybcybc.xyz/sql4/logs/gunicorn.pid"

# 性能限制 - 防止资源耗尽
limit_request_line = 2048  # 限制请求行长度
limit_request_fields = 50  # 限制请求头数量
limit_request_field_size = 4096  # 限制请求头大小

# 内存优化
worker_tmp_dir = "/dev/shm"  # 使用内存文件系统（如果可用）

# 说明：
# - 2个worker可以处理约4-8个并发请求
# - 每个worker约占用80-150MB内存
# - 总内存占用约200-400MB（不含MySQL）
# - 适合2GB内存服务器，4GB内存更佳