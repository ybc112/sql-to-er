#!/usr/bin/env python3
"""
SQL to ER Diagram Converter - Main Program
Converts SQL CREATE TABLE statements to Entity-Relationship diagrams
"""
import argparse
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src import parse_sql, build_er_model, render_er_diagram


def sql_to_er(sql_content: str, output_name: str = "er_diagram", view: bool = True):
    """
    Convert SQL to ER diagram
    
    Args:
        sql_content: SQL string containing CREATE TABLE statements
        output_name: Output filename (without extension)
        view: Whether to open the diagram after rendering
    """
    print("🔍 Parsing SQL statements...")
    tables, error = parse_sql(sql_content)
    
    if not tables:
        print("❌ No CREATE TABLE statements found in the SQL")
        return None
    
    print(f"✅ Found {len(tables)} table(s):")
    for table_name in tables:
        print(f"   - {table_name}")
    
    print("\n🏗️  Building ER model...")
    entities, relationships = build_er_model(tables)
    
    print(f"   - {len(entities)} entities")
    print(f"   - {len(relationships)} relationships")
    
    print("\n🎨 Rendering ER diagram...")
    output_path = render_er_diagram(entities, relationships, output_name, view)
    
    print(f"\n✅ ER diagram saved to: {output_path}")
    return output_path


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Convert SQL CREATE TABLE statements to ER diagrams"
    )
    parser.add_argument(
        "input",
        help="SQL file path or '-' for stdin"
    )
    parser.add_argument(
        "-o", "--output",
        default="er_diagram",
        help="Output filename (without extension)"
    )
    parser.add_argument(
        "--no-view",
        action="store_true",
        help="Don't open the diagram after rendering"
    )
    
    args = parser.parse_args()
    
    # Read SQL content
    if args.input == "-":
        print("📝 Reading SQL from stdin (press Ctrl+D when done)...")
        sql_content = sys.stdin.read()
    else:
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"❌ Error: File not found: {args.input}")
            sys.exit(1)
        
        print(f"📝 Reading SQL from: {args.input}")
        sql_content = input_path.read_text()
    
    # Convert to ER diagram
    try:
        sql_to_er(sql_content, args.output, not args.no_view)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()