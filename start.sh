#!/bin/bash
# 宝塔面板Python项目启动脚本

# 设置项目路径
PROJECT_PATH="/www/wwwroot/ybcybcybc.xyz/sql4"
cd $PROJECT_PATH

# 设置环境变量
export FLASK_ENV=production
export PYTHONPATH=$PROJECT_PATH:$PROJECT_PATH/sql_to_er:$PROJECT_PATH/sql_to_er/web_app

# 创建必要的目录
mkdir -p logs
mkdir -p uploads
mkdir -p sql_to_er/web_app/output/tmp

# 检查是否已有进程在运行
if pgrep -f "gunicorn.*wsgi:application" > /dev/null; then
    echo "Gunicorn进程已在运行，正在停止..."
    pkill -f "gunicorn.*wsgi:application"
    sleep 2
fi

# 后台启动Gunicorn
echo "启动Gunicorn服务..."
nohup gunicorn -c gunicorn_config.py wsgi:application > logs/gunicorn.log 2>&1 &

# 等待启动
sleep 3

# 检查启动状态
if pgrep -f "gunicorn.*wsgi:application" > /dev/null; then
    echo "✅ Gunicorn启动成功！"
    echo "📊 进程信息："
    ps aux | grep "gunicorn.*wsgi:application" | grep -v grep
    echo "🌐 访问地址："
    echo "   - http://127.0.0.1:5001"
    echo "   - http://8.148.104.41:5001"
else
    echo "❌ Gunicorn启动失败！"
    echo "查看日志："
    tail -n 20 logs/gunicorn.log
fi
