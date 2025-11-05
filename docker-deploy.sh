#!/bin/bash
# Docker部署脚本

echo "🐳 开始Docker部署..."

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ Docker未安装，请先安装Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose未安装，请先安装Docker Compose"
    exit 1
fi

# 创建必要的目录
mkdir -p logs uploads ssl

# 停止现有容器
echo "🛑 停止现有容器..."
docker-compose down

# 构建并启动服务
echo "🚀 构建并启动服务..."
docker-compose up -d --build

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 10

# 检查服务状态
echo "📊 检查服务状态..."
docker-compose ps

# 检查应用健康状态
echo "🏥 检查应用健康状态..."
if curl -f http://localhost/health > /dev/null 2>&1; then
    echo "✅ 应用部署成功！"
    echo "🌐 访问地址："
    echo "   - http://localhost"
    echo "   - http://你的服务器IP"
else
    echo "❌ 应用启动失败，查看日志："
    docker-compose logs web
fi

echo "📝 常用命令："
echo "   查看日志: docker-compose logs -f"
echo "   重启服务: docker-compose restart"
echo "   停止服务: docker-compose down"
echo "   进入容器: docker-compose exec web bash"