"""
宝塔面板部署配置文件
用于生产环境的Flask应用配置
"""
import os

class ProductionConfig:
    """生产环境配置"""
    
    # Flask基础配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-production-secret-key-change-this'
    DEBUG = False
    TESTING = False
    
    # 数据库配置 - 根据你的宝塔MySQL配置修改
    DB_CONFIG = {
        'host': 'localhost',          # MySQL服务器地址
        'user': 'root',   # 你的MySQL用户名
        'password': '123456', # 请改为您的实际MySQL密码
        'database': 'user_system',    # 数据库名
        'charset': 'utf8mb4'
    }
    
    # 服务器配置
    HOST = '0.0.0.0'  # 监听所有接口
    PORT = 5001       # 端口号，可以根据需要修改
    
    # 日志配置
    LOG_LEVEL = 'INFO'
    LOG_FILE = '/www/wwwroot/ybcybcybc.xyz/sql4/logs/app.log'  # 替换为实际路径
    
    # 文件上传配置
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    UPLOAD_FOLDER = '/www/wwwroot/ybcybcybc.xyz/sql4/uploads'  # 替换为实际路径
    
    # API配置
    DEEPSEEK_API_KEY = "你的DeepSeek API密钥"  # 替换为实际API密钥
    DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

class Config:
    """配置类选择器"""
    
    @staticmethod
    def get_config():
        """根据环境变量选择配置"""
        env = os.environ.get('FLASK_ENV', 'production')
        if env == 'production':
            return ProductionConfig()
        else:
            return ProductionConfig()  # 默认使用生产配置