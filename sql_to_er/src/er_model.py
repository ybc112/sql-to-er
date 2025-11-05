"""
ER Model Classes - Represent entities, attributes, and relationships
"""
from typing import List, Optional, Dict, Any, Tuple


class Entity:
    """Represents an entity (table) in the ER diagram"""
    
    def __init__(self, name: str, comment: str = None):
        self.name = name
        self.attributes: List[Attribute] = []
        self.comment = comment

    def get_display_name(self) -> str:
        """Get the display name for this entity (comment if available, otherwise name)"""
        return self.comment if self.comment else self.name
    
    def add_attribute(self, attribute: 'Attribute'):
        """Add an attribute to this entity"""
        self.attributes.append(attribute)
    
    def __repr__(self):
        return f"Entity(name={self.name}, attributes={len(self.attributes)})"


class Attribute:
    """Represents an attribute (column) of an entity."""
    def __init__(self, name: str, data_type: str, is_pk: bool = False, is_fk: bool = False, 
                 comment: Optional[str] = None, nullable: bool = True, default: Optional[str] = None):
        self.name = name
        self.data_type = data_type
        self.is_pk = is_pk
        self.is_fk = is_fk
        self.comment = comment
        self.display_name = comment if comment else name
        self.nullable = nullable
        self.default = default

    def to_dict(self):
        """Converts the attribute to a dictionary."""
        return {
            "name": self.name,
            "type": self.data_type,
            "isPK": self.is_pk,
            "isFK": self.is_fk,
            "comment": self.comment,
            "displayName": self.display_name,
            "nullable": self.nullable,
            "default": self.default,
        }
    
    def get_display_name(self) -> str:
        """Get the display name for this attribute (comment if available, otherwise name)"""
        return self.display_name
    
    def __repr__(self):
        pk_str = " [PK]" if self.is_pk else ""
        comment_str = f" ({self.comment})" if self.comment else ""
        return f"Attribute(name={self.name}{pk_str}, type={self.data_type}{comment_str})"


class Relationship:
    """Represents a relationship between entities"""
    
    def __init__(self, from_entity: str, to_entity: str, 
                 from_attribute: str, to_attribute: str, 
                 name: Optional[str] = None, rel_type: str = '1:N', comment: str = None):
        self.from_entity = from_entity
        self.to_entity = to_entity
        self.from_attribute = from_attribute
        self.to_attribute = to_attribute
        self.name = name or f"{from_entity}_to_{to_entity}"
        self.rel_type = rel_type  # '1:1', '1:N', 'M:N'
        self.comment = comment
    
    def get_display_name(self) -> str:
        """Get the display name for this relationship (comment if available, otherwise name)"""
        return self.comment if self.comment else self.name
    
    def __repr__(self):
        return (f"Relationship({self.from_entity}.{self.from_attribute} -> "
                f"{self.to_entity}.{self.to_attribute}, type={self.rel_type})")


def build_er_model(tables: Dict[str, Any]) -> Tuple[Dict[str, Entity], List[Relationship]]:
    """
    Build ER model from parsed table metadata
    
    Args:
        tables: Dictionary of table metadata from SQL parser
        
    Returns:
        Tuple of (entities dictionary, relationships list)
    """
    entities = {}
    relationships = []
    
    # Create entities and attributes
    for table_name, table_data in tables.items():
        entity = Entity(table_name, comment=table_data.get("comment"))

        # 收集外键列名
        foreign_key_columns = set()
        for fk in table_data.get("foreign_keys", []):
            foreign_key_columns.add(fk["column"])

        # 判断是否为中间表（关联表）
        # 中间表的特征：有2个或更多外键，且大部分列都是外键或主键
        is_junction_table = len(table_data.get("foreign_keys", [])) >= 2

        # Add attributes: 始终显示所有字段，包括外键字段
        for col in table_data["columns"]:
            is_foreign_key = col["name"] in foreign_key_columns

            attr = Attribute(
                name=col["name"],
                data_type=col.get("type", "UNKNOWN"),
                is_pk=col.get("pk", False),
                is_fk=is_foreign_key,
                comment=col.get("comment"),
                nullable=col.get("nullable", True),
                default=col.get("default")
            )
            entity.add_attribute(attr)

        entities[table_name] = entity
    
    # Create relationships from foreign keys
    for table_name, table_data in tables.items():
        for fk in table_data["foreign_keys"]:
            # 判断关系类型
            rel_type = '1:N'  # 默认为一对多
            
            # 检查外键列是否也是主键（一对一关系）
            fk_column = fk["column"]
            is_fk_also_pk = any(col["name"] == fk_column and col["pk"] 
                                for col in table_data["columns"])
            
            # 检查外键列是否有UNIQUE约束
            is_fk_unique = any(col["name"] == fk_column and col.get("unique", False) 
                              for col in table_data["columns"])
            
            if is_fk_also_pk or is_fk_unique:
                rel_type = '1:1'
            
            # 检查是否是多对多关系（中间表通常有两个或更多外键，且这些外键组成复合主键）
            if len(table_data["foreign_keys"]) >= 2:
                # 计算主键数量
                pk_count = sum(1 for col in table_data["columns"] if col["pk"])
                fk_count = len(table_data["foreign_keys"])
                
                # 如果外键数量等于主键数量，且表只有外键列（或很少其他列），可能是中间表
                if fk_count >= 2 and pk_count >= 2:
                    rel_type = 'M:N'
            
            # Create a relationship for each foreign key
            rel = Relationship(
                from_entity=table_name,
                to_entity=fk["ref"]["table"],
                from_attribute=fk["column"],
                to_attribute=fk["ref"]["column"] or "id",
                rel_type=rel_type,
                comment=fk.get("comment") # Pass relationship comment
            )
            relationships.append(rel)
    
    return entities, relationships