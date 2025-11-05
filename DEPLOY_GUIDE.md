# 快速部署指南

## 📋 项目部署方案总结

根据你的项目特点（Flask + MySQL + Graphviz），我为你整理了以下**便宜又好用**的部署方案：

---

## 🏆 最推荐方案（按预算）

### 💰 预算：¥0-50/月

**方案：Railway免费套餐**
- ✅ 完全免费（有$5免费额度）
- ✅ 支持Docker一键部署
- ✅ 自动HTTPS
- ✅ 数据库可以使用PlanetScale免费版或Railway的MySQL
- ⚠️ 免费额度有限，适合小项目

**快速部署步骤**：
1. 访问 https://railway.app
2. 用GitHub登录
3. 连接你的代码仓库
4. 添加MySQL数据库服务
5. 配置环境变量
6. 一键部署

---

### 💰 预算：¥24-50/月

**方案：腾讯云轻量应用服务器**
- ✅ 国内访问速度快
- ✅ 支持宝塔面板（你已有配置）
- ✅ 新用户优惠大
- ✅ 2核4G配置足够使用

**快速部署步骤**：
```bash
# 1. 购买服务器（选择Ubuntu 22.04）
# 2. 安装宝塔面板
wget -O install.sh http://download.bt.cn/install/install-ubuntu_6.0.sh && sudo bash install.sh

# 3. 在宝塔面板中：
#    - 安装Python项目管理器、MySQL、Nginx
#    - 上传项目文件
#    - 配置Python项目（使用你的gunicorn_config.py）
#    - 配置Nginx反向代理（使用nginx_config.conf）
```

---

### 💰 预算：¥42-168/月

**方案：Vultr VPS（全球访问）**
- ✅ 全球多个节点可选
- ✅ 性能稳定
- ✅ 支持Docker部署
- ✅ 适合全球用户访问

**快速部署步骤**：
```bash
# 使用Docker Compose一键部署
git clone <your-repo>
cd sql
docker-compose up -d
```

---

## 📁 项目文件说明

我已经为你创建了以下部署相关文件：

1. **部署方案对比.md** - 详细的方案对比和成本分析
2. **quick_deploy.sh** - Linux/Mac快速部署脚本
3. **quick_deploy.bat** - Windows快速部署脚本
4. **railway.json** - Railway平台配置文件
5. **render.yaml** - Render平台配置文件

---

## 🚀 立即开始部署

### 方式一：使用Docker（最简单）

```bash
# 1. 确保已安装Docker和Docker Compose
# 2. 克隆项目
git clone <your-repo>
cd sql

# 3. 配置环境变量（编辑docker-compose.yml或使用.env文件）
# 4. 启动服务
docker-compose up -d

# 5. 访问 http://localhost:5001
```

### 方式二：使用Railway（最省钱）

1. 访问 https://railway.app
2. 用GitHub账号登录
3. 点击 "New Project" → "Deploy from GitHub repo"
4. 选择项目仓库
5. 添加MySQL数据库服务
6. 配置环境变量：
   - `DEEPSEEK_API_KEY` - 你的DeepSeek API密钥
   - `SECRET_KEY` - 随机生成（Railway会自动生成）
   - `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` - 从数据库服务获取
7. 点击 "Deploy" 开始部署

### 方式三：使用宝塔面板（国内推荐）

1. 购买腾讯云轻量应用服务器（2核4G，¥50/月）
2. 安装宝塔面板
3. 在宝塔面板中安装Python项目管理器、MySQL、Nginx
4. 上传项目文件
5. 配置Python项目（使用项目中的`gunicorn_config.py`）
6. 配置Nginx反向代理（使用项目中的`nginx_config.conf`）
7. 配置SSL证书（Let's Encrypt免费证书）

---

## ⚙️ 环境变量配置

无论使用哪种部署方式，都需要配置以下环境变量：

```bash
# Flask配置
FLASK_ENV=production
SECRET_KEY=your-secret-key-here  # 生产环境请使用随机字符串

# 数据库配置
DB_HOST=localhost  # 或数据库服务地址
DB_USER=root
DB_PASSWORD=your-password
DB_NAME=user_system

# DeepSeek API
DEEPSEEK_API_KEY=your-deepseek-api-key
DEEPSEEK_API_URL=https://api.deepseek.com/v1/chat/completions
```

---

## 📊 成本对比表

| 方案 | 月成本 | 适合场景 | 推荐度 |
|------|--------|----------|--------|
| Railway免费版 | ¥0 | 小项目、测试 | ⭐⭐⭐⭐⭐ |
| 腾讯云轻量服务器 | ¥24-50 | 国内用户 | ⭐⭐⭐⭐⭐ |
| Vultr VPS | ¥42-168 | 全球访问 | ⭐⭐⭐⭐ |
| Render免费版 | ¥0-49 | 简单项目 | ⭐⭐⭐⭐ |

---

## 🔧 常见问题

### Q: 选择哪个方案最好？
**A**: 
- 如果主要用户在国内 → 选择**腾讯云轻量服务器**（¥50/月）
- 如果想免费试用 → 选择**Railway**（免费额度）
- 如果需要全球访问 → 选择**Vultr**（$12/月）

### Q: 数据库怎么办？
**A**: 
- 宝塔面板：直接在服务器上安装MySQL
- Railway/Render：使用平台提供的MySQL服务
- Docker：使用docker-compose.yml中的MySQL容器

### Q: 需要备案吗？
**A**: 
- 国内服务器：需要备案才能使用域名访问
- 海外服务器：无需备案

### Q: 如何配置SSL证书？
**A**: 
- 宝塔面板：在网站管理中申请Let's Encrypt免费证书
- Railway/Render：自动配置HTTPS
- Docker：需要手动配置Nginx SSL

---

## 📞 需要帮助？

如果部署过程中遇到问题：

1. 查看详细文档：`部署方案对比.md`
2. 检查配置文件：
   - `gunicorn_config.py` - Gunicorn配置
   - `nginx_config.conf` - Nginx配置
   - `docker-compose.yml` - Docker配置
3. 查看日志文件排查问题

---

## 🎯 推荐行动步骤

1. **第一步**：如果预算有限，先试用Railway免费版
2. **第二步**：如果Railway不够用，考虑腾讯云轻量服务器（¥50/月）
3. **第三步**：如果需要全球访问，选择Vultr VPS

祝你部署顺利！🎉

