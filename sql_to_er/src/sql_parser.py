"""
Enhanced SQL parser with ALTER TABLE support
"""
import re
from typing import Dict, Any, Tuple, List


def parse_sql(sql: str) -> Tuple[Dict[str, Any], str]:
    """
    解析 SQL，支持 CREATE TABLE 和 ALTER TABLE ADD FOREIGN KEY
    """
    try:
        # 标准化引号
        sql = sql.replace(''', "'").replace(''', "'")
        sql = sql.replace('"', '"').replace('"', '"')
        
        # 移除注释但保留 COMMENT 内容
        lines = []
        for line in sql.split('\n'):
            # 如果行中有 COMMENT 关键字，保留整行
            if 'COMMENT' in line.upper():
                lines.append(line)
            else:
                # 移除 -- 注释
                lines.append(re.sub(r'--.*$', '', line))
        sql = '\n'.join(lines)
        
        # 移除块注释
        sql = re.sub(r'/\*(?!.*COMMENT).*?\*/', '', sql, flags=re.DOTALL)
        
        # 移除 CREATE DATABASE 和 USE 语句
        sql = re.sub(r'CREATE\s+DATABASE[^;]*;', '', sql, flags=re.IGNORECASE)
        sql = re.sub(r'USE\s+[^;]*;', '', sql, flags=re.IGNORECASE)
        
        tables = {}
        
        # 第一步：解析所有 CREATE TABLE 语句
        # 手动查找CREATE TABLE语句，正确处理括号匹配
        sql_upper = sql.upper()
        pos = 0
        
        while True:
            # 查找下一个CREATE TABLE
            create_pos = sql_upper.find('CREATE TABLE', pos)
            if create_pos == -1:
                create_pos = sql_upper.find('CREATE  TABLE', pos)  # 处理多个空格
            if create_pos == -1:
                break
            
            # 找到表名
            name_match = re.search(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`"]?(\w+)[`"]?\s*\(', 
                                 sql[create_pos:], re.IGNORECASE)
            if not name_match:
                pos = create_pos + 1
                continue
            
            table_name = name_match.group(1)
            
            # 找到开始括号的位置
            start_paren = create_pos + name_match.end() - 1
            
            # 匹配括号以找到结束位置
            paren_count = 1
            i = start_paren + 1
            in_quote = False
            quote_char = None
            
            while i < len(sql) and paren_count > 0:
                char = sql[i]
                
                # 处理引号
                if char in ("'", '"') and (i == 0 or sql[i-1] != '\\'):
                    if not in_quote:
                        in_quote = True
                        quote_char = char
                    elif char == quote_char:
                        in_quote = False
                        quote_char = None
                
                # 不在引号内时计算括号
                if not in_quote:
                    if char == '(':
                        paren_count += 1
                    elif char == ')':
                        paren_count -= 1
                
                i += 1
            
            if paren_count == 0:
                # 找到了完整的CREATE TABLE语句
                table_content = sql[start_paren + 1:i - 1]
                full_statement = sql[create_pos:i]
                
                # 查找到语句结束的分号
                semi_pos = sql.find(';', i)
                if semi_pos != -1:
                    full_statement = sql[create_pos:semi_pos + 1]
                
                # 提取表注释
                table_comment = ''
                comment_match = re.search(r"COMMENT\s*=?\s*['\"]([^'\"]*)['\"]\s*(?:;|$)", 
                                        full_statement[i-create_pos:], re.IGNORECASE)
                if comment_match:
                    table_comment = comment_match.group(1)
                
                # 解析列和约束
                columns = []
                primary_keys = []
                foreign_keys = []
                
                # 智能分割
                parts = smart_split(table_content)
                
                for part in parts:
                    part = part.strip()
                    if not part:
                        continue
                    
                    upper_part = part.upper()
                    
                    # 处理约束
                    constraint_line = False
                    # 仅当该行以 PRIMARY/FOREIGN/UNIQUE/KEY/INDEX 或带 CONSTRAINT 开头时，视为约束行
                    if re.match(r'^\s*(CONSTRAINT\s+[`"]?\w+[`"]?\s+)?PRIMARY\s+KEY', upper_part):
                        constraint_line = True
                        pk_match = re.search(r'PRIMARY\s+KEY\s*\(([^)]+)\)', part, re.IGNORECASE)
                        if pk_match:
                            pk_cols = [col.strip().strip('`"') for col in pk_match.group(1).split(',')]
                            primary_keys.extend(pk_cols)
                    elif re.match(r'^\s*(CONSTRAINT\s+[`"]?\w+[`"]?\s+)?FOREIGN\s+KEY', upper_part):
                        constraint_line = True
                        fk_match = re.search(
                            r'FOREIGN\s+KEY\s*\(([^)]+)\)\s*REFERENCES\s+[`"]?(\w+)[`"]?\s*\(([^)]+)\)',
                            part, re.IGNORECASE
                        )
                        if fk_match:
                            add_foreign_key(foreign_keys, fk_match, part)
                    elif re.match(r'^\s*(CONSTRAINT\s+[`"]?\w+[`"]?\s+)?UNIQUE(\s+KEY)?', upper_part):
                        constraint_line = True
                    elif re.match(r'^\s*(KEY|INDEX)\s+', upper_part):
                        constraint_line = True

                    if constraint_line:
                        # 对于纯约束行，处理完后跳过列解析
                        continue

                    # 处理列定义
                    col_match = re.match(r'^[`"]?(\w+)[`"]?\s+(\w+(?:\([^)]+\))?)', part, re.IGNORECASE)
                    if col_match:
                        col_name = col_match.group(1)
                        col_type = col_match.group(2).upper()

                        # 提取列属性
                        col_info = extract_column_info(part, col_name, col_type)
                        columns.append(col_info)

                        if col_info['pk']:
                            primary_keys.append(col_name)
                
                # 确保主键标记正确
                for col in columns:
                    if col['name'] in primary_keys:
                        col['pk'] = True
                
                tables[table_name] = {
                    'columns': columns,
                    'primary_keys': list(set(primary_keys)),
                    'foreign_keys': foreign_keys,
                    'comment': table_comment
                }
            
            pos = create_pos + len(table_name) + 10  # 继续查找下一个表
        
        # 第二步：解析所有 ALTER TABLE 语句中的外键
        alter_pattern = r'ALTER\s+TABLE\s+[`"]?(\w+)[`"]?\s+(.*?)(?:;|$)'
        
        for match in re.finditer(alter_pattern, sql, re.IGNORECASE | re.DOTALL):
            table_name = match.group(1)
            alter_content = match.group(2)
            
            if table_name not in tables:
                continue
            
            # 查找 ADD CONSTRAINT 或 ADD FOREIGN KEY
            fk_patterns = [
                r'ADD\s+CONSTRAINT\s+[`"]?\w+[`"]?\s+FOREIGN\s+KEY\s*\(([^)]+)\)\s*REFERENCES\s+[`"]?(\w+)[`"]?\s*\(([^)]+)\)',
                r'ADD\s+FOREIGN\s+KEY\s*\(([^)]+)\)\s*REFERENCES\s+[`"]?(\w+)[`"]?\s*\(([^)]+)\)'
            ]
            
            for pattern in fk_patterns:
                for fk_match in re.finditer(pattern, alter_content, re.IGNORECASE):
                    add_foreign_key(tables[table_name]['foreign_keys'], fk_match, alter_content)
        
        if not tables:
            return {}, "No CREATE TABLE statements found in the SQL."
        
        return tables, ""
        
    except Exception as e:
        # 提供更详细的错误信息
        import traceback
        error_detail = {
            'message': str(e),
            'type': type(e).__name__,
            'traceback': traceback.format_exc()
        }
        
        # 尝试提取错误位置
        error_msg = f"解析错误: {str(e)}"
        if hasattr(e, 'line_number'):
            error_msg += f" (行号: {e.line_number})"
        
        return {}, error_msg


def smart_split(content: str) -> List[str]:
    """智能分割 SQL 内容，考虑括号嵌套"""
    parts = []
    current = ''
    depth = 0
    in_quote = False
    quote_char = None
    
    i = 0
    while i < len(content):
        char = content[i]
        
        # 处理引号
        if char in ("'", '"') and (i == 0 or content[i-1] != '\\'):
            if not in_quote:
                in_quote = True
                quote_char = char
            elif char == quote_char:
                in_quote = False
                quote_char = None
        
        # 不在引号内时处理括号和逗号
        if not in_quote:
            if char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
            elif char == ',' and depth == 0:
                parts.append(current.strip())
                current = ''
                i += 1
                continue
        
        current += char
        i += 1
    
    if current.strip():
        parts.append(current.strip())
    
    return parts


def extract_column_info(part: str, col_name: str, col_type: str) -> Dict[str, Any]:
    """提取列信息"""
    upper_part = part.upper()
    
    # 提取注释
    comment = None
    comment_match = re.search(r"COMMENT\s+['\"]([^'\"]*)['\"]", part, re.IGNORECASE)
    if comment_match:
        comment = comment_match.group(1)
    
    return {
        'name': col_name,
        'type': col_type,
        'pk': 'PRIMARY KEY' in upper_part,
        'nullable': 'NOT NULL' not in upper_part,
        'default': extract_default(part),
        'comment': comment,
        'auto_increment': 'AUTO_INCREMENT' in upper_part
    }


def extract_default(part: str) -> Any:
    """提取默认值"""
    default_match = re.search(r'DEFAULT\s+([^\s,]+)', part, re.IGNORECASE)
    if default_match:
        value = default_match.group(1).strip("'\"")
        return value if value.upper() != 'NULL' else None
    return None


def add_foreign_key(foreign_keys: List[Dict], fk_match, content: str) -> None:
    """添加外键信息"""
    local_cols = [col.strip().strip('`"') for col in fk_match.group(1).split(',')]
    ref_table = fk_match.group(2)
    ref_cols = [col.strip().strip('`"') for col in fk_match.group(3).split(',')]
    
    # 获取约束名和注释
    constraint_name = ''
    constraint_match = re.search(r'CONSTRAINT\s+[`"]?(\w+)[`"]?', content[:fk_match.start()], re.IGNORECASE)
    if constraint_match:
        constraint_name = constraint_match.group(1)
    
    # 获取注释
    comment = constraint_name
    comment_match = re.search(r"COMMENT\s+['\"]([^'\"]*)['\"]", content[fk_match.start():], re.IGNORECASE)
    if comment_match:
        comment = comment_match.group(1)
    
    for i, local_col in enumerate(local_cols):
        foreign_keys.append({
            'column': local_col,
            'ref': {
                'table': ref_table,
                'column': ref_cols[i] if i < len(ref_cols) else local_col
            },
            'comment': comment
        })