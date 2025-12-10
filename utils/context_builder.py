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
        """Compact table structure only."""
        working = state["working"]
        
        tables = []
        for t in working["tables"][:15]:
            cols = [c["name"] for c in t["columns"][:10]]
            fks = sum(1 for c in t["columns"] if c.get("references"))
            tables.append(f"- {t['name']} ({len(t['columns'])} cols, {fks} FKs): {', '.join(cols[:8])}")
        
        prev = ""
        if working.get("critic_summary"):
            prev = f"\n\nPrevious: {working['critic_summary']['overall_score']}/10"
        
        return f"Tables:\n" + "\n".join(tables) + prev
    
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