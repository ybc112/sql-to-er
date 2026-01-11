"""
系统配置管理模块
用于管理和获取系统配置信息
"""

import pymysql
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class SystemConfig:
    """系统配置管理类"""
    
    def __init__(self):
        self._config_cache = {}
        self._cache_valid = False
    
    def get_db_connection(self):
        """获取数据库连接"""
        return pymysql.connect(
            host='localhost',
            user='root',
            password='123456',
            database='user_system',
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
    
    def _load_config(self):
        """从数据库加载配置"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT config_key, config_value FROM system_config")
            configs = cursor.fetchall()
            
            self._config_cache = {}
            for config in configs:
                self._config_cache[config['config_key']] = config['config_value']
            
            self._cache_valid = True
            conn.close()
            
        except Exception as e:
            logger.error(f"加载系统配置失败: {e}")
            self._cache_valid = False
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        if not self._cache_valid:
            self._load_config()
        
        return self._config_cache.get(key, default)
    
    def get_price(self, service_type: str) -> float:
        """获取服务价格"""
        price_key = f"{service_type}_price"
        price_str = self.get_config(price_key, "0.00")
        
        try:
            return float(price_str)
        except (ValueError, TypeError):
            logger.warning(f"无效的价格配置: {price_key} = {price_str}")
            return 0.00
    
    def get_all_prices(self) -> Dict[str, float]:
        """获取所有服务价格"""
        if not self._cache_valid:
            self._load_config()
        
        prices = {}
        for key, value in self._config_cache.items():
            if key.endswith('_price'):
                service_type = key.replace('_price', '')
                try:
                    prices[service_type] = float(value)
                except (ValueError, TypeError):
                    prices[service_type] = 0.00
        
        return prices
    
    def set_config(self, key: str, value: str, description: str = None):
        """设置配置值"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO system_config (config_key, config_value, description)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                config_value = VALUES(config_value),
                description = COALESCE(VALUES(description), description),
                updated_at = CURRENT_TIMESTAMP
            """, (key, value, description))
            
            conn.commit()
            conn.close()
            
            # 更新缓存
            self._config_cache[key] = value
            
        except Exception as e:
            logger.error(f"设置配置失败: {e}")
            raise
    
    def refresh_cache(self):
        """刷新配置缓存"""
        self._cache_valid = False
        self._load_config()
    
    def get_ai_config(self) -> Dict[str, str]:
        """获取AI相关配置"""
        if not self._cache_valid:
            self._load_config()
        
        ai_config = {}
        for key, value in self._config_cache.items():
            if key.startswith('ai_') or 'model' in key.lower():
                ai_config[key] = value
        
        return ai_config
    
    def is_maintenance_mode(self) -> bool:
        """检查是否为维护模式"""
        mode = self.get_config('maintenance_mode', '0')
        return mode == '1'
    
    def get_site_info(self) -> Dict[str, str]:
        """获取网站信息"""
        return {
            'site_name': self.get_config('site_name', 'SQL转ER图工具'),
            'site_url': self.get_config('site_url', ''),
            'admin_email': self.get_config('admin_email', ''),
        }

# 全局配置实例
system_config = SystemConfig()

def get_service_price(service_type: str) -> float:
    """获取服务价格的便捷函数"""
    return system_config.get_price(service_type)

def get_config_value(key: str, default: Any = None) -> Any:
    """获取配置值的便捷函数"""
    return system_config.get_config(key, default)

def is_maintenance_mode() -> bool:
    """检查维护模式的便捷函数"""
    return system_config.is_maintenance_mode()

# 服务类型常量
class ServiceTypes:
    """服务类型常量"""
    PAPER_GENERATION = 'paper_generation'
    DEFENSE_QUESTIONS = 'defense_questions'
    SQL_TO_ER = 'sql_to_er'
    ER_OPTIMIZATION = 'er_optimization'
    DATABASE_DESIGN = 'database_design'
    FLOWCHART_GENERATION = 'flowchart_generation'

# 默认价格配置
DEFAULT_PRICES = {
    ServiceTypes.PAPER_GENERATION: 3.00,
    ServiceTypes.DEFENSE_QUESTIONS: 2.00,
    ServiceTypes.SQL_TO_ER: 1.50,
    ServiceTypes.ER_OPTIMIZATION: 1.00,
    ServiceTypes.DATABASE_DESIGN: 2.50,
    ServiceTypes.FLOWCHART_GENERATION: 1.00,
}

def init_default_config():
    """初始化默认配置"""
    try:
        conn = system_config.get_db_connection()
        cursor = conn.cursor()
        
        # 检查是否已有配置
        cursor.execute("SELECT COUNT(*) as count FROM system_config")
        count = cursor.fetchone()['count']
        
        if count == 0:
            # 插入默认配置
            default_configs = [
                ('paper_generation_price', '3.00', '论文生成服务价格（元）'),
                ('defense_questions_price', '2.00', '答辩问题生成价格（元）'),
                ('sql_to_er_price', '1.50', 'SQL转ER图价格（元）'),
                ('er_optimization_price', '1.00', 'ER图优化价格（元）'),
                ('database_design_price', '2.50', '数据库设计价格（元）'),
                ('flowchart_generation_price', '1.00', '流程图生成价格（元）'),
                ('ai_model_name', 'deepseek-chat', '使用的AI模型'),
                ('site_name', 'SQL转ER图工具', '网站名称'),
                ('maintenance_mode', '0', '维护模式（0关闭，1开启）'),
                ('admin_email', 'admin@example.com', '管理员邮箱'),
                ('site_url', 'http://localhost:5000', '网站URL'),
            ]
            
            for key, value, desc in default_configs:
                cursor.execute("""
                    INSERT INTO system_config (config_key, config_value, description)
                    VALUES (%s, %s, %s)
                """, (key, value, desc))
            
            conn.commit()
            logger.info("默认系统配置初始化完成")
        
        conn.close()
        
    except Exception as e:
        logger.error(f"初始化默认配置失败: {e}")

if __name__ == "__main__":
    # 测试配置管理
    init_default_config()
    
    # 测试获取配置
    print("论文生成价格:", get_service_price(ServiceTypes.PAPER_GENERATION))
    print("所有价格:", system_config.get_all_prices())
    print("AI配置:", system_config.get_ai_config())
    print("网站信息:", system_config.get_site_info())
    print("维护模式:", is_maintenance_mode())
