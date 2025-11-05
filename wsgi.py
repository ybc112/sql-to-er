"""
WSGI入口文件
用于Gunicorn和宝塔面板部署
"""
import sys
import os

# 添加项目路径到Python路径
project_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_path)
sys.path.insert(0, os.path.join(project_path, 'sql_to_er'))
sys.path.insert(0, os.path.join(project_path, 'sql_to_er', 'web_app'))

# 设置环境变量
os.environ['FLASK_ENV'] = 'production'

# 导入Flask应用
from sql_to_er.web_app.app import app
from deploy_config import Config

# 应用生产配置
config = Config.get_config()

# 更新应用配置
app.config.update({
    'SECRET_KEY': config.SECRET_KEY,
    'DEBUG': config.DEBUG,
    'MAX_CONTENT_LENGTH': config.MAX_CONTENT_LENGTH
})

# 创建必要的目录
os.makedirs(os.path.dirname(config.LOG_FILE), exist_ok=True)
os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)

if __name__ == "__main__":
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
else:
    # 这是WSGI服务器调用的应用对象
    application = app
