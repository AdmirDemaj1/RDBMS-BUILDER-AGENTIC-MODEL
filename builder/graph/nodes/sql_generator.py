# graph/nodes/sql_generator.py
from typing import List
from ..state import GraphState
from ...utils.state_manager import StateManager
from ...utils.task_manager import start_task, complete_task, fail_task


class SQLDialectGenerator:
    def __init__(self, dialect: str):
        self.dialect = dialect.lower()
    
    def get_type_mapping(self) -> dict:
        mappings = {
            "mysql": {
                "UUID": "CHAR(36)", "SERIAL": "BIGINT AUTO_INCREMENT",
                "BIGSERIAL": "BIGINT AUTO_INCREMENT",
                "TIMESTAMP": "DATETIME", "TIMESTAMPTZ": "DATETIME",
                "BOOLEAN": "TINYINT(1)", "JSONB": "JSON", "JSON": "JSON",
                "TEXT": "TEXT", "INTEGER": "INT", "BIGINT": "BIGINT"
            },
            "sqlite": {
                "UUID": "TEXT", "SERIAL": "INTEGER", "BIGSERIAL": "INTEGER",
                "TIMESTAMP": "TEXT", "TIMESTAMPTZ": "TEXT",
                "BOOLEAN": "INTEGER", "DECIMAL": "REAL", "VARCHAR": "TEXT",
                "JSONB": "TEXT", "JSON": "TEXT", "INTEGER": "INTEGER"
            },
            "postgresql": {
                "UUID": "UUID", "SERIAL": "SERIAL", "BIGSERIAL": "BIGSERIAL",
                "TIMESTAMP": "TIMESTAMP", "TIMESTAMPTZ": "TIMESTAMPTZ",
                "BOOLEAN": "BOOLEAN", "JSONB": "JSONB", "JSON": "JSON",
                "TEXT": "TEXT", "INTEGER": "INTEGER", "BIGINT": "BIGINT"
            }
        }
        return mappings.get(self.dialect, mappings["postgresql"])
    
    def convert_type(self, data_type: str) -> str:
        mapping = self.get_type_mapping()
        base = data_type.split("(")[0].upper()
        params = "(" + data_type.split("(")[1] if "(" in data_type else ""
        converted = mapping.get(base, data_type)
        if self.dialect == "sqlite" and base in ["VARCHAR", "DECIMAL"]:
            return converted
        return converted + params if params else converted
    
    def generate_column(self, col: dict) -> str:
        parts = [col["name"], self.convert_type(col["data_type"])]
        
        if col.get("primary_key"):
            if self.dialect == "sqlite" and "INTEGER" in col["data_type"].upper():
                parts.append("PRIMARY KEY AUTOINCREMENT")
            else:
                parts.append("PRIMARY KEY")
        
        if not col.get("nullable", True) and not col.get("primary_key"):
            parts.append("NOT NULL")
        if col.get("unique") and not col.get("primary_key"):
            parts.append("UNIQUE")
        if col.get("default"):
            parts.append(f"DEFAULT {col['default']}")
        if col.get("check_constraint"):
            parts.append(f"CHECK ({col['check_constraint']})")
        
        return " ".join(parts)
    
    def generate_fk_constraint(self, table_name: str, col: dict) -> str:
        ref = col["references"]
        on_delete = ref.get("on_delete", "RESTRICT")
        on_update = ref.get("on_update", "CASCADE")
        
        fk = f"    CONSTRAINT fk_{table_name}_{col['name']} "
        fk += f"FOREIGN KEY ({col['name']}) REFERENCES {ref['table']}({ref['column']})"
        fk += f" ON DELETE {on_delete} ON UPDATE {on_update}"
        return fk
    
    def generate_index(self, table_name: str, idx: dict) -> str:
        unique = "UNIQUE " if idx.get("unique") else ""
        columns = ", ".join(idx["columns"])
        idx_name = idx.get("name", f"idx_{table_name}_{'_'.join(idx['columns'])}")
        
        if self.dialect == "postgresql" and idx.get("type", "btree") != "btree":
            return f"CREATE {unique}INDEX {idx_name} ON {table_name} USING {idx['type']} ({columns});"
        return f"CREATE {unique}INDEX {idx_name} ON {table_name} ({columns});"
    
    def generate_table(self, table: dict) -> str:
        lines = []
        
        # Table comment
        if table.get("description"):
            lines.append(f"-- {table['description']}")
        
        # Security notice for PII
        pii_cols = [c["name"] for c in table["columns"] if c.get("is_pii")]
        if pii_cols:
            lines.append(f"-- ⚠️  PII columns: {', '.join(pii_cols)} - Consider encryption")
        
        lines.append(f"CREATE TABLE {table['name']} (")
        
        col_defs = [f"    {self.generate_column(c)}" for c in table["columns"]]
        
        # Foreign key constraints
        for col in table["columns"]:
            if col.get("references"):
                col_defs.append(self.generate_fk_constraint(table["name"], col))
        
        # Table-level constraints
        for constraint in table.get("constraints", []):
            col_defs.append(f"    CONSTRAINT chk_{table['name']}_{len(col_defs)} CHECK ({constraint})")
        
        lines.append(",\n".join(col_defs))
        lines.append(");")
        
        return "\n".join(lines)
    
    def generate_updated_at_trigger(self, table_name: str) -> str:
        if self.dialect == "postgresql":
            return f"""
-- Auto-update updated_at trigger for {table_name}
CREATE TRIGGER trg_{table_name}_updated_at
    BEFORE UPDATE ON {table_name}
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();"""
        elif self.dialect == "mysql":
            return f"""
-- Auto-update updated_at trigger for {table_name}
CREATE TRIGGER trg_{table_name}_updated_at
    BEFORE UPDATE ON {table_name}
    FOR EACH ROW
    SET NEW.updated_at = NOW();"""
        return ""
    
    def generate_rls_policy(self, table_name: str) -> str:
        if self.dialect != "postgresql":
            return ""
        return f"""
-- Row Level Security for {table_name}
ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;
-- Example policy (customize based on your auth):
-- CREATE POLICY {table_name}_tenant_isolation ON {table_name}
--     USING (tenant_id = current_setting('app.current_tenant')::uuid);"""
    
    def generate_ddl(self, tables: List[dict]) -> str:
        dialect_name = {"postgresql": "PostgreSQL", "mysql": "MySQL", "sqlite": "SQLite"}
        
        parts = [
            "-- ============================================================",
            f"-- RDBMS Schema - Production Ready",
            f"-- Dialect: {dialect_name.get(self.dialect, self.dialect)}",
            f"-- Generated with optimization, security, and best practices",
            "-- ============================================================",
            ""
        ]
        
        # Dialect-specific setup
        if self.dialect == "mysql":
            parts.append("SET FOREIGN_KEY_CHECKS = 0;")
            parts.append("SET sql_mode = 'STRICT_TRANS_TABLES,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO';")
            parts.append("")
        elif self.dialect == "sqlite":
            parts.append("PRAGMA foreign_keys = ON;")
            parts.append("PRAGMA journal_mode = WAL;")
            parts.append("")
        elif self.dialect == "postgresql":
            parts.append("-- Enable required extensions")
            parts.append('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
            parts.append('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')
            parts.append("")
            parts.append("-- Function for auto-updating updated_at")
            parts.append("""CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';""")
            parts.append("")
        
        # Section: Tables
        parts.append("-- ============================================================")
        parts.append("-- TABLES")
        parts.append("-- ============================================================")
        parts.append("")
        
        for table in tables:
            parts.append(self.generate_table(table))
            parts.append("")
        
        # Section: Indexes
        parts.append("-- ============================================================")
        parts.append("-- INDEXES (Critical for query performance)")
        parts.append("-- ============================================================")
        parts.append("")
        
        for table in tables:
            indexes = table.get("indexes", [])
            if indexes:
                parts.append(f"-- Indexes for {table['name']}")
                for idx in indexes:
                    parts.append(self.generate_index(table["name"], idx))
                parts.append("")
        
        # Section: Triggers
        if self.dialect in ["postgresql", "mysql"]:
            parts.append("-- ============================================================")
            parts.append("-- TRIGGERS (Auto-update timestamps)")
            parts.append("-- ============================================================")
            for table in tables:
                has_updated_at = any(c["name"] == "updated_at" for c in table["columns"])
                if has_updated_at:
                    parts.append(self.generate_updated_at_trigger(table["name"]))
            parts.append("")
        
        # Section: Row Level Security
        rls_tables = [t for t in tables if t.get("row_level_security")]
        if rls_tables and self.dialect == "postgresql":
            parts.append("-- ============================================================")
            parts.append("-- ROW LEVEL SECURITY (Multi-tenant isolation)")
            parts.append("-- ============================================================")
            for table in rls_tables:
                parts.append(self.generate_rls_policy(table["name"]))
            parts.append("")
        
        # Cleanup
        if self.dialect == "mysql":
            parts.append("SET FOREIGN_KEY_CHECKS = 1;")
        
        return "\n".join(parts)


def sql_generator(state: GraphState) -> GraphState:
    start_task(state, "generate_sql")
    
    working = state["working"]
    dialect = working.get("sql_dialect", "postgresql")
    tables = working["tables"]
    
    try:
        generator = SQLDialectGenerator(dialect)
        ddl = generator.generate_ddl(tables)
        
        state["archive"]["ddl_script"] = ddl
        state["working"]["current_step"] = "sql_generation_complete"
        
        complete_task(state, "generate_sql", f"{dialect.upper()} DDL - {len(tables)} tables")
        
    except Exception as e:
        fail_task(state, "generate_sql", str(e))
        # Re-raise to let LangGraph checkpoint at previous node for proper resume
        raise
    
    return state