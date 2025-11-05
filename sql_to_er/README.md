# SQL to ER Diagram Converter

将SQL CREATE TABLE语句转换为实体关系图（ER图）的工具。

## 特性

- 解析SQL CREATE TABLE语句
- 自动识别主键和外键关系
- 生成标准ER图：
  - 实体（Entity）：矩形框表示
  - 属性（Attribute）：椭圆形表示
  - 关系（Relationship）：菱形表示
  - 主键属性用红色标注

## 安装

1. 克隆项目：
```bash
cd sql_to_er
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

## 使用方法

### 命令行使用

```bash
# 从SQL文件生成ER图
python main.py examples/company_db.sql

# 指定输出文件名
python main.py examples/ecommerce_db.sql -o ecommerce_diagram

# 从标准输入读取SQL
echo "CREATE TABLE test (id INT PRIMARY KEY, name VARCHAR(50));" | python main.py -

# 生成图片但不自动打开
python main.py examples/school_db.sql --no-view
```

### 作为Python模块使用

```python
from src import parse_sql, build_er_model, render_er_diagram

# SQL语句
sql = """
CREATE TABLE Department (
    dept_id INT PRIMARY KEY,
    name VARCHAR(50)
);

CREATE TABLE Employee (
    emp_id INT PRIMARY KEY,
    name VARCHAR(100),
    dept_id INT,
    FOREIGN KEY (dept_id) REFERENCES Department(dept_id)
);
"""

# 解析SQL
tables = parse_sql(sql)

# 构建ER模型
entities, relationships = build_er_model(tables)

# 渲染ER图
render_er_diagram(entities, relationships, "my_diagram")
```

## 示例

项目包含了几个示例SQL文件：

- `examples/company_db.sql` - 公司员工管理系统
- `examples/ecommerce_db.sql` - 电子商务系统
- `examples/school_db.sql` - 学校管理系统

运行示例：
```bash
python main.py examples/company_db.sql
```

## 项目结构

```
sql_to_er/
├── src/
│   ├── __init__.py
│   ├── sql_parser.py      # SQL解析模块
│   ├── er_model.py        # ER模型定义
│   └── visualization.py   # 图形渲染模块
├── examples/              # 示例SQL文件
├── output/               # 输出目录
├── main.py              # 主程序
└── requirements.txt     # 依赖列表
```

## 技术栈

- **sqlglot** - SQL解析器
- **graphviz** - 图形渲染
- **Python 3.8+**

## 注意事项

- 目前支持基本的CREATE TABLE语句
- 支持PRIMARY KEY和FOREIGN KEY约束
- 输出格式为PNG图片
- 需要系统安装Graphviz软件