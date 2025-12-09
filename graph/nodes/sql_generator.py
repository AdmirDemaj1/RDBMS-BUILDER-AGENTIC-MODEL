# graph/nodes/sql_generator.py
from typing import Dict, Any, List
from graph.state import GraphState


class SQLDialectGenerator:
    """Generates DDL for different SQL dialects."""
    
    def __init__(self, dialect: str):
        self.dialect = dialect.lower()
    
    def get_type_mapping(self) -> dict:
        """Map generic types to dialect-specific types."""
        if self.dialect == "mysql":
            return {
                "UUID": "CHAR(36)",
                "SERIAL": "INT AUTO_INCREMENT",
                "TIMESTAMP": "DATETIME",
                "TEXT": "TEXT",
                "BOOLEAN": "TINYINT(1)",
                "DECIMAL": "DECIMAL",
                "VARCHAR": "VARCHAR",
                "INTEGER": "INT",
                "BIGINT": "BIGINT",
                "DATE": "DATE",
                "JSONB": "JSON",
                "JSON": "JSON",
            }
        elif self.dialect == "sqlite":
            return {
                "UUID": "TEXT",
                "SERIAL": "INTEGER",
                "TIMESTAMP": "TEXT",
                "TEXT": "TEXT",
                "BOOLEAN": "INTEGER",
                "DECIMAL": "REAL",
                "VARCHAR": "TEXT",
                "INTEGER": "INTEGER",
                "BIGINT": "INTEGER",
                "DATE": "TEXT",
                "JSONB": "TEXT",
                "JSON": "TEXT",
            }
        else:  # postgresql (default)
            return {
                "UUID": "UUID",
                "SERIAL": "SERIAL",
                "TIMESTAMP": "TIMESTAMP",
                "TEXT": "TEXT",
                "BOOLEAN": "BOOLEAN",
                "DECIMAL": "DECIMAL",
                "VARCHAR": "VARCHAR",
                "INTEGER": "INTEGER",
                "BIGINT": "BIGINT",
                "DATE": "DATE",
                "JSONB": "JSONB",
                "JSON": "JSON",
            }
    
    def convert_type(self, data_type: str) -> str:
        """Convert a data type to the dialect-specific version."""
        mapping = self.get_type_mapping()
        
        # Handle types with parameters like VARCHAR(255) or DECIMAL(10,2)
        base_type = data_type.split("(")[0].upper()
        params = ""
        if "(" in data_type:
            params = "(" + data_type.split("(")[1]
        
        converted = mapping.get(base_type, data_type)
        
        # Don't add params if the type doesn't support them
        if self.dialect == "sqlite" and base_type in ["VARCHAR", "DECIMAL"]:
            return converted  # SQLite uses TEXT/REAL without params
        
        if params and converted not in ["TEXT", "REAL", "INTEGER"]:
            return converted + params
        return converted
    
    def get_default_id(self) -> str:
        """Get the default ID column definition."""
        if self.dialect == "mysql":
            return "id INT AUTO_INCREMENT PRIMARY KEY"
        elif self.dialect == "sqlite":
            return "id INTEGER PRIMARY KEY AUTOINCREMENT"
        else:
            return "id UUID PRIMARY KEY DEFAULT gen_random_uuid()"
    
    def get_timestamp_default(self) -> str:
        """Get the default timestamp value."""
        if self.dialect == "mysql":
            return "CURRENT_TIMESTAMP"
        elif self.dialect == "sqlite":
            return "CURRENT_TIMESTAMP"
        else:
            return "CURRENT_TIMESTAMP"
    
    def generate_column(self, col: dict) -> str:
        """Generate a single column definition."""
        parts = [col['name'], self.convert_type(col['data_type'])]
        
        if col.get('primary_key'):
            if self.dialect == "sqlite" and col['data_type'].upper() in ["INTEGER", "SERIAL"]:
                parts.append("PRIMARY KEY AUTOINCREMENT")
            elif self.dialect == "mysql" and col['data_type'].upper() == "SERIAL":
                parts.append("PRIMARY KEY")
            else:
                parts.append("PRIMARY KEY")
        
        if not col.get('nullable', True) and not col.get('primary_key'):
            parts.append("NOT NULL")
        
        if col.get('unique') and not col.get('primary_key'):
            parts.append("UNIQUE")
        
        if col.get('default') is not None:
            default_val = col['default']
            # Handle function defaults
            if default_val in ['CURRENT_TIMESTAMP', 'gen_random_uuid()', 'NOW()']:
                default_val = self.get_timestamp_default() if 'TIMESTAMP' in default_val or 'NOW' in default_val else default_val
                if self.dialect == "mysql" and default_val == "gen_random_uuid()":
                    default_val = "(UUID())"
                elif self.dialect == "sqlite" and default_val == "gen_random_uuid()":
                    default_val = "(lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6))))"
            parts.append(f"DEFAULT {default_val}")
        
        return " ".join(parts)
    
    def generate_foreign_key(self, table_name: str, col: dict) -> str:
        """Generate a foreign key constraint."""
        if not col.get('references'):
            return None
        
        ref = col['references']
        fk_name = f"fk_{table_name}_{col['name']}"
        
        if self.dialect == "sqlite":
            # SQLite handles FK differently - inline with column or separate
            return f"    FOREIGN KEY ({col['name']}) REFERENCES {ref['table']}({ref['column']})"
        else:
            return f"    CONSTRAINT {fk_name} FOREIGN KEY ({col['name']}) REFERENCES {ref['table']}({ref['column']})"
    
    def generate_index(self, table_name: str, idx: dict) -> str:
        """Generate an index statement."""
        idx_name = idx.get('name', f"idx_{table_name}_{'_'.join(idx['columns'])}")
        columns = ", ".join(idx['columns'])
        unique = "UNIQUE " if idx.get('unique') else ""
        return f"CREATE {unique}INDEX {idx_name} ON {table_name} ({columns});"
    
    def generate_table(self, table: dict) -> str:
        """Generate a complete table DDL."""
        lines = []
        
        # Header comment
        if table.get('description'):
            lines.append(f"-- {table['description']}")
        
        lines.append(f"CREATE TABLE {table['name']} (")
        
        column_definitions = []
        foreign_keys = []
        
        for col in table['columns']:
            col_def = "    " + self.generate_column(col)
            column_definitions.append(col_def)
            
            fk = self.generate_foreign_key(table['name'], col)
            if fk:
                foreign_keys.append(fk)
        
        all_definitions = column_definitions + foreign_keys
        lines.append(",\n".join(all_definitions))
        lines.append(");")
        
        # Add indexes
        for idx in table.get('indexes', []):
            lines.append(self.generate_index(table['name'], idx))
        
        lines.append("")  # Empty line after table
        
        return "\n".join(lines)
    
    def generate_header(self) -> str:
        """Generate the DDL header."""
        dialect_names = {
            "postgresql": "PostgreSQL",
            "mysql": "MySQL",
            "sqlite": "SQLite"
        }
        return f"""-- Generated RDBMS Schema
-- Dialect: {dialect_names.get(self.dialect, self.dialect)}
-- Generated by RDBMS Builder

"""
    
    def generate_ddl(self, tables: List[dict]) -> str:
        """Generate complete DDL for all tables."""
        parts = [self.generate_header()]
        
        # Add dialect-specific settings
        if self.dialect == "mysql":
            parts.append("SET FOREIGN_KEY_CHECKS = 0;\n")
        elif self.dialect == "sqlite":
            parts.append("PRAGMA foreign_keys = ON;\n")
        
        for table in tables:
            parts.append(self.generate_table(table))
        
        if self.dialect == "mysql":
            parts.append("\nSET FOREIGN_KEY_CHECKS = 1;")
        
        return "\n".join(parts)


def sql_generator(state: GraphState) -> Dict[str, Any]:
    """
    Node that generates DDL SQL from the validated schema.
    Supports multiple SQL dialects.
    """
    dialect = state.get('sql_dialect', 'postgresql')
    print(f"\n📝 Generating SQL DDL for {dialect.upper()}...")
    
    generator = SQLDialectGenerator(dialect)
    ddl_script = generator.generate_ddl(state['tables'])
    
    print(f"✅ SQL DDL generated successfully!")
    
    return {
        "ddl_script": ddl_script,
        "current_step": "sql_generation_complete"
    }