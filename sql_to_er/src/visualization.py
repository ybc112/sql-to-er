"""
ER Diagram Visualization Module - Renders ER diagrams using Graphviz
"""
import graphviz
from typing import Dict, List, Optional
from .er_model import Entity, Relationship


class ERDiagramRenderer:
    """Renders ER diagrams using Graphviz"""
    
    def __init__(self, name: str = "ER_Diagram"):
        self.dot = graphviz.Digraph(name, format="png")
        self.dot.attr(rankdir="TB")  # Top to bottom layout
        self.dot.attr("node", fontname="Arial", fontsize="10")
        self.dot.attr("edge", arrowsize="0.7", penwidth="1.2")
        
    def render_entities(self, entities: Dict[str, Entity]):
        """Render entities and their attributes"""
        for entity_name, entity in entities.items():
            # Create subgraph for each entity to group it with its attributes
            with self.dot.subgraph(name=f"cluster_{entity_name}") as sub:
                sub.attr(label="", style="invis")  # Invisible cluster
                
                # Entity node (rectangle)
                sub.node(
                    entity_name, 
                    shape="box", 
                    style="filled", 
                    fillcolor="lightblue",
                    label=entity_name
                )
                
                # Attribute nodes (ellipses)
                for attr in entity.attributes:
                    attr_id = f"{entity_name}_{attr.name}"
                    display_name = attr.get_display_name()  # 使用注释优先的显示名称
                    
                    # Style for primary key attributes
                    if attr.is_pk:
                        sub.node(
                            attr_id,
                            label=f"{display_name}\\n[PK]",
                            shape="ellipse",
                            style="filled",
                            fillcolor="lightyellow",
                            fontcolor="red",
                            penwidth="2"
                        )
                    else:
                        sub.node(
                            attr_id,
                            label=display_name,
                            shape="ellipse",
                            style="filled",
                            fillcolor="white"
                        )
                    
                    # Connect entity to attribute
                    sub.edge(entity_name, attr_id, dir="none")
    
    def render_relationships(self, relationships: List[Relationship]):
        """Render relationships between entities"""
        for i, rel in enumerate(relationships):
            rel_node = f"rel_{i}"
            
            # Relationship node (diamond)
            # 使用关系注释或生成的名称作为标签
            rel_label = rel.get_display_name() if hasattr(rel, 'get_display_name') else rel.comment or f"{rel.from_entity}_{rel.to_entity}"
            
            self.dot.node(
                rel_node,
                shape="diamond",
                style="filled",
                fillcolor="lightgreen",
                label=rel_label,
                fontsize="9",
                width="0.8",
                height="0.6"
            )
            
            # Connect entities through relationship
            # From entity to relationship
            self.dot.edge(
                rel.from_entity,
                rel_node,
                dir="none",
                label=f"{rel.from_attribute}"
            )
            
            # From relationship to target entity
            self.dot.edge(
                rel_node,
                rel.to_entity,
                dir="none",
                label=f"→{rel.to_attribute}"
            )
    
    def save(self, filename: str = "er_diagram", view: bool = True):
        """Save the diagram to file"""
        output_path = f"output/{filename}"
        self.dot.render(output_path, view=view, cleanup=True)
        return f"{output_path}.png"


def render_er_diagram(entities: Dict[str, Entity], 
                     relationships: List[Relationship],
                     output_name: str = "er_diagram",
                     view: bool = True) -> str:
    """
    Convenience function to render an ER diagram
    
    Args:
        entities: Dictionary of entities
        relationships: List of relationships
        output_name: Output filename (without extension)
        view: Whether to open the diagram after rendering
        
    Returns:
        Path to the generated image file
    """
    renderer = ERDiagramRenderer(output_name)
    renderer.render_entities(entities)
    renderer.render_relationships(relationships)
    return renderer.save(output_name, view)