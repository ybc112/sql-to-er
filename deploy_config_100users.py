"""
部署配置文件 - 每天100用户优化版
针对小规模访问量的生产环境配置
"""
import os

class Config100Users:
    """每天100用户的优化配置"""
    
    # Flask基础配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-production-secret-key-change-this'
    DEBUG = False
    TESTING = False
    
    # 数据库配置 - 小规模优化
    DB_CONFIG = {
        'host': 'localhost',
        'user': 'root',
        'password': '123456',  # 请改为实际密码
        'database': 'user_system',
        'charset': 'utf8mb4',
        # 连接池优化 - 小规模访问
        'pool_size': 5,        # 连接池大小
        'max_overflow': 10,    # 最大溢出连接
        'pool_timeout': 30,    # 连接超时
        'pool_recycle': 3600   # 连接回收时间
    }
    
    # 服务器配置
    HOST = '0.0.0.0'
    PORT = 5001
    
    # 日志配置 - 减少IO
    LOG_LEVEL = 'WARNING'  # 只记录警告和错误
    LOG_FILE = '/www/wwwroot/ybcybcybc.xyz/sql4/logs/app.log'
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB轮转
    LOG_BACKUP_COUNT = 3  # 保留3个备份
    
    # 文件上传配置 - 小规模优化
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8MB，降低内存占用
    UPLOAD_FOLDER = '/www/wwwroot/ybcybcybc.xyz/sql4/uploads'
    
    # 缓存配置
    CACHE_TYPE = 'simple'  # 使用简单内存缓存
    CACHE_DEFAULT_TIMEOUT = 300  # 5分钟缓存
    
    # API配置
    DEEPSEEK_API_KEY = "你的DeepSeek API密钥"
    DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
    API_TIMEOUT = 30  # API超时时间
    
    # 性能配置
    SQLALCHEMY_POOL_SIZE = 5  # 数据库连接池
    SQLALCHEMY_POOL_TIMEOUT = 20
    SQLALCHEMY_POOL_RECYCLE = 3600
    SQLALCHEMY_MAX_OVERFLOW = 10
    
    # 限流配置
    RATELIMIT_STORAGE_URL = "memory://"  # 使用内存存储限流信息
    RATELIMIT_DEFAULT = "100 per hour"   # 每小时100个请求
    
    # ER图生成配置
    ER_DIAGRAM_CONFIG = {
        'max_tables': 20,      # 最大表数量
        'max_columns': 50,     # 单表最大列数
        'timeout': 60,         # 渲染超时时间
        'cache_enabled': True, # 启用结果缓存
        'cache_ttl': 3600     # 缓存1小时
    }
    
    # 静态文件配置
    STATIC_FOLDER = 'sql_to_er/web_app/static'
    STATIC_URL_PATH = '/static'
    
    # 会话配置
    SESSION_COOKIE_SECURE = False  # HTTP环境设为False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 3600  # 1小时会话

class Config:
    """配置选择器"""
    
    @staticmethod
    def get_config():
        """返回100用户优化配置"""
        return Config100Users()

# MySQL优化建议（在my.cnf中配置）
MYSQL_CONFIG_SUGGESTIONS = """
# MySQL配置建议（2GB内存服务器）
[mysqld]
# 内存配置
innodb_buffer_pool_size = 512M      # 缓冲池大小
key_buffer_size = 64M               # MyISAM键缓冲
query_cache_size = 32M              # 查询缓存
tmp_table_size = 32M                # 临时表大小
max_heap_table_size = 32M           # 内存表大小

# 连接配置
max_connections = 50                # 最大连接数
max_connect_errors = 10             # 最大连接错误
connect_timeout = 10                # 连接超时

# 性能配置
slow_query_log = 1                  # 启用慢查询日志
long_query_time = 2                 # 慢查询阈值2秒
"""