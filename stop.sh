#!/bin/bash
# 停止Python项目脚本

echo "正在停止Gunicorn进程..."

# 查找并停止gunicorn进程
pids=$(pgrep -f "gunicorn.*wsgi:application")

if [ -n "$pids" ]; then
    echo "找到运行中的进程: $pids"
    pkill -f "gunicorn.*wsgi:application"
    sleep 2
    
    # 检查是否成功停止
    if pgrep -f "gunicorn.*wsgi:application" > /dev/null; then
        echo "❌ 进程仍在运行，使用强制停止..."
        pkill -9 -f "gunicorn.*wsgi:application"
    else
        echo "✅ Gunicorn进程已成功停止！"
    fi
else
    echo "ℹ️  没有发现运行中的Gunicorn进程"
fi