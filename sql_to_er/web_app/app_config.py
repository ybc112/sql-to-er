# -*- coding: utf-8 -*-
"""
配置管理模块 - 从环境变量加载敏感配置
"""
import os
from dotenv import load_dotenv

# 加载 .env 文件（如果存在）
load_dotenv()


class Config:
    """基础配置类"""

    # Flask 配置
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

    # 数据库配置
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_NAME = os.getenv('DB_NAME', 'user_system')
    DB_CHARSET = os.getenv('DB_CHARSET', 'utf8mb4')

    @classmethod
    def get_db_config(cls):
        """获取数据库配置字典"""
        return {
            'host': cls.DB_HOST,
            'user': cls.DB_USER,
            'password': cls.DB_PASSWORD,
            'database': cls.DB_NAME,
            'charset': cls.DB_CHARSET
        }

    # 邮件配置
    SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.qq.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', '465'))
    EMAIL_USER = os.getenv('EMAIL_USER', '')
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', '')

    @classmethod
    def get_email_config(cls):
        """获取邮件配置字典"""
        return {
            'smtp_host': cls.SMTP_HOST,
            'smtp_port': cls.SMTP_PORT,
            'email_user': cls.EMAIL_USER,
            'email_password': cls.EMAIL_PASSWORD
        }

    # DeepSeek API 配置
    DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
    DEEPSEEK_API_URL = os.getenv('DEEPSEEK_API_URL', 'https://api.deepseek.com/v1/chat/completions')

    # 虎皮椒支付配置
    HUPI_APPID = os.getenv('HUPI_APPID', '')
    HUPI_APPSECRET = os.getenv('HUPI_APPSECRET', '')

    @classmethod
    def get_hupi_config(cls):
        """获取虎皮椒支付配置"""
        return {
            'appid': cls.HUPI_APPID,
            'appsecret': cls.HUPI_APPSECRET
        }


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False

    # 生产环境必须设置这些变量
    @classmethod
    def validate(cls):
        """验证生产环境必需的配置"""
        required = [
            ('SECRET_KEY', cls.SECRET_KEY, 'dev-secret-key-change-in-production'),
            ('DB_PASSWORD', cls.DB_PASSWORD, ''),
            ('DEEPSEEK_API_KEY', cls.DEEPSEEK_API_KEY, ''),
        ]

        missing = []
        for name, value, default in required:
            if not value or value == default:
                missing.append(name)

        if missing:
            raise ValueError(f"生产环境缺少必需的配置: {', '.join(missing)}")


class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    DB_NAME = os.getenv('TEST_DB_NAME', 'user_system_test')


# 根据环境变量选择配置
def get_config():
    """根据 FLASK_ENV 环境变量获取对应的配置类"""
    env = os.getenv('FLASK_ENV', 'development')

    config_map = {
        'development': DevelopmentConfig,
        'production': ProductionConfig,
        'testing': TestingConfig
    }

    return config_map.get(env, DevelopmentConfig)


# 便捷访问
config = get_config()
