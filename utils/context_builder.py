# utils/context_builder.py
from graph.state import GraphState


class ContextBuilder:
    """Builds minimal context for LLM calls to reduce tokens."""
    
    @staticmethod
    def for_entity_extraction(state: GraphState) -> str:
        """Just requirements - minimal context."""
        req = state["working"]["user_requirements"]
        # Truncate if very long
        if len(req) > 2000:
            req = req[:2000] + "..."
        return req
    
    @staticmethod
    def for_relationship_analysis(state: GraphState) -> str:
        """Requirements + entity names only."""
        working = state["working"]
        
        req = working["user_requirements"]
        if len(req) > 1500:
            req = req[:1500] + "..."
        
        entities = "\n".join([
            f"- {e['name']}: {e['description'][:80]}"
            for e in working["entities"][:15]
        ])
        
        return f"Requirements:\n{req}\n\nEntities:\n{entities}"
    
    @staticmethod
    def for_schema_design(state: GraphState) -> str:
        """Compact entities + relationships."""
        working = state["working"]
        
        entities = "\n".join([
            f"- {e['name']}: {', '.join(e['attributes'][:8])}"
            for e in working["entities"][:15]
        ])
        
        relationships = "\n".join([
            f"- {r['from_entity']} --[{r['type']}]--> {r['to_entity']}"
            for r in working["relationships"][:20]
        ])
        
        return f"Entities:\n{entities}\n\nRelationships:\n{relationships}"
    
    @staticmethod
    def for_critic(state: GraphState) -> str:
        """Compact table structure + previous evaluation for comparison."""
        working = state["working"]
        archive = state["archive"]
        
        tables = []
        for t in working["tables"][:15]:
            cols = [c["name"] for c in t["columns"][:10]]
            fks = sum(1 for c in t["columns"] if c.get("references"))
            idxs = len(t.get("indexes", []))
            tables.append(f"- {t['name']} ({len(t['columns'])} cols, {fks} FKs, {idxs} indexes): {', '.join(cols[:8])}")
        
        context = f"Tables:\n" + "\n".join(tables)
        
        # Add previous evaluation context if this is a refinement iteration
        critic_reports = archive.get("critic_reports", [])
        if critic_reports:
            prev_score = critic_reports[-1].get("overall_score", 0)
            prev_critical = len([f for f in critic_reports[-1].get("feedback_items", []) 
                               if f.get("severity") == "critical"])
            
            context += f"\n\n## Previous Evaluation (for comparison):\n"
            context += f"- Previous Score: {prev_score}/10\n"
            context += f"- Previous Critical Issues: {prev_critical}\n"
            
            # Show schema versions to help compare
            schema_versions = archive.get("schema_versions", [])
            if len(schema_versions) >= 2:
                context += f"- This is refinement iteration {len(critic_reports)}\n"
                context += f"- Refinement claimed to apply fixes - verify they were actually implemented\n"
        
        return context
    
    @staticmethod
    def for_refiner(state: GraphState) -> str:
        """Current schema + pending feedback only."""
        working = state["working"]
        archive = state["archive"]
        
        tables = "\n".join([
            f"- {t['name']}: {', '.join([c['name'] for c in t['columns'][:8]])}"
            for t in working["tables"][:15]
        ])
        
        feedback = []
        if archive["critic_reports"]:
            latest = archive["critic_reports"][-1]
            for f in latest.get("feedback_items", []):
                if not f.get("applied") and f["severity"] in ["critical", "warning"]:
                    feedback.append(f"- [{f['severity']}] {f['issue'][:80]}")
        
        return f"Schema:\n{tables}\n\nFeedback:\n" + "\n".join(feedback[:8])
    
    @staticmethod
    def for_nestjs_architecture(state: GraphState) -> str:
        """Build context for NestJS architecture generation."""
        working = state["working"]
        
        tables_info = []
        for table in working["tables"]:
            cols = []
            for col in table["columns"]:
                col_info = f"{col['name']} ({col['data_type']})"
                if col.get("primary_key"):
                    col_info += " PK"
                if col.get("references"):
                    ref = col["references"]
                    col_info += f" FK→{ref['table']}.{ref['column']}"
                cols.append(col_info)
            
            indexes = [f"idx:{','.join(idx['columns'])}" for idx in table.get("indexes", [])]
            
            table_str = f"Table: {table['name']}\n"
            table_str += f"  Description: {table.get('description', 'N/A')}\n"
            table_str += f"  Columns: {', '.join(cols)}\n"
            if indexes:
                table_str += f"  Indexes: {', '.join(indexes)}"
            
            tables_info.append(table_str)
        
        relationships_info = []
        for rel in working.get("relationships", []):
            relationships_info.append(
                f"- {rel['from_entity']} --[{rel['type']}]--> {rel['to_entity']}: {rel.get('description', '')}"
            )
        
        context = "## Tables\n\n"
        context += "\n\n".join(tables_info)
        
        if relationships_info:
            context += "\n\n## Relationships\n\n"
            context += "\n".join(relationships_info)
        
        return context