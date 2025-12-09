# graph/state.py
from typing import TypedDict, List, Optional
from enum import Enum


class Column(TypedDict):
    """Represents a database column"""
    name: str
    data_type: str
    nullable: bool
    primary_key: bool
    unique: bool
    default: Optional[str]
    references: Optional[dict]


class Table(TypedDict):
    """Represents a database table"""
    name: str
    description: str
    columns: List[Column]
    indexes: List[dict]


class Entity(TypedDict):
    """Raw entity extracted from user input"""
    name: str
    description: str
    attributes: List[str]


class Relationship(TypedDict):
    """Relationship between entities"""
    from_entity: str
    to_entity: str
    type: str
    description: str


class ClarifyingQuestion(TypedDict):
    """A question to ask the user"""
    question: str
    context: str  # Why we're asking
    options: Optional[List[str]]  # Suggested answers if applicable


class SQLDialect(str, Enum):
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"


class GraphState(TypedDict):
    """The state that flows through our graph."""
    # Input from user
    user_requirements: str
    user_answers: List[str]  # Answers to clarifying questions
    
    # Configuration
    sql_dialect: str  # postgresql, mysql, sqlite
    
    # Clarification
    clarifying_questions: List[ClarifyingQuestion]
    needs_clarification: bool
    
    # Extracted information
    entities: List[Entity]
    relationships: List[Relationship]
    
    # Generated schema
    tables: List[Table]
    
    # Validation
    validation_issues: List[str]
    iteration_count: int
    max_iterations: int
    
    # Output
    ddl_script: str
    erd_diagram: str  # Mermaid diagram
    
    # Control flow
    current_step: str
    is_complete: bool
    error: Optional[str]