# RDBMS Builder

An AI-powered tool for generating relational database schemas using LangGraph and Pydantic.

---

## 📚 Understanding Pydantic

### What is Pydantic?

Pydantic is a Python library that lets you define structured data using classes. It validates and parses data automatically, ensuring:

- ✅ Correct types
- ✅ Required fields
- ✅ Optional fields
- ✅ Defaults
- ✅ Nested objects
- ✅ Constraints

### Where is it used?

Pydantic is heavily used in:

- **FastAPI** — API request/response validation
- **LangChain / LangGraph** — Structured LLM outputs
- **Data validation pipelines** — ETL and data processing
- **Typed JSON-like structures** — Configuration management

### Automatic Type Conversion

Pydantic performs automatic type conversion. For example:

```python
"primary_key": "false"  →  primary_key: False
```

The string `"false"` is automatically converted to the boolean `False`.

---

## 🔧 How `with_structured_output()` Works

When using LangChain/LangGraph with Pydantic models, the `with_structured_output()` method enables structured JSON responses from LLMs.

### Step 1: Define Pydantic Models

```python
from pydantic import BaseModel, Field
from typing import List, Optional

class ColumnSchema(BaseModel):
    name: str = Field(description="Column name in snake_case")
    data_type: str = Field(description="PostgreSQL data type")
    nullable: bool = Field(default=True)
    primary_key: bool = Field(default=False)
    unique: bool = Field(default=False)
    default: Optional[str] = Field(default=None)
    references_table: Optional[str] = Field(default=None, description="Referenced table for FK")
    references_column: Optional[str] = Field(default=None, description="Referenced column for FK")


class TableSchema(BaseModel):
    name: str = Field(description="Table name in snake_case, plural")
    description: str = Field(description="Brief description")
    columns: List[ColumnSchema] = Field(description="List of columns")


class DatabaseSchema(BaseModel):
    tables: List[TableSchema] = Field(description="List of all tables")
```

### Step 2: Create Structured LLM

```python
structured_llm = llm.with_structured_output(DatabaseSchema)
```

This tells the LLM:
> "Do NOT give me text. Give me JSON **exactly** shaped like `DatabaseSchema`."

---

## ⚙️ Internal Process

Internally, LangChain/LangGraph performs 4 steps:

### 1️⃣ Read the Pydantic Model

LangChain inspects the model for:

- Fields
- Types
- Descriptions
- Nested models
- Optional/required fields

**Example conversion:**

```python
class TableSchema(BaseModel):
    name: str
    description: str
    columns: List[ColumnSchema]
```

Becomes this JSON schema:

```json
{
  "type": "object",
  "properties": {
    "name": {"type": "string"},
    "description": {"type": "string"},
    "columns": {
      "type": "array",
      "items": {
        "$ref": "#/definitions/ColumnSchema"
      }
    }
  },
  "required": ["name", "description", "columns"]
}
```

### 2️⃣ Create a Hidden System Prompt

LangChain adds a system message to the LLM:

```
You MUST respond only with valid JSON.
Your JSON MUST conform to the following schema:
<generated JSON schema>
```

### 3️⃣ Parse the LLM Response

After the LLM responds, the output is parsed:

| Result | Action |
|--------|--------|
| ✅ Valid JSON | Continue processing |
| ❌ Invalid JSON | Retry or raise error |

### 4️⃣ Validate with Pydantic

Finally, Pydantic validates and converts the JSON:

```python
parsed = DatabaseSchema.parse_obj(response_json)
```

Pydantic handles:

- ✅ Type checking
- ✅ Required field validation
- ✅ String → Boolean conversion
- ✅ Auto-casting values
- ✅ Helpful error messages


## 📚 How to design better schemas for LLMs

### Rule 1 — Never use ambiguous field names
❌ type
❌ value
❌ data
✔️ Always use descriptive names:
data_type
references_table
references_column

### Rule 2 — Keep nested structures shallow
LLMs understand:
DatabaseSchema → TableSchema → ColumnSchema
But deeper nesting becomes unstable.

### Rule 3 — Provide clear field descriptions
These:
name: str = Field(description="Column name in snake_case")
data_type: str = Field(description="PostgreSQL data type")
Tell the LLM how to behave.
If you remove these, the model will generate sloppy output.


### Rule 4 — Give default values where possible
Example:
nullable: bool = True
This prevents the model from forgetting fields.

### Rule 5 — Do NOT use Optional everywhere
Optional fields weaken validation.
Only use Optional when truly optional:
references_table: Optional[str] = None

















---

## ✨ Features

- 🤖 **AI-Powered Schema Generation** - Automatic database schema design from natural language
- 🔍 **Intelligent Critic System** - Built-in schema review and refinement
- 💾 **Long-Term Memory (NEW!)** - LangGraph checkpointing for persistent state across sessions
- 🚀 **NestJS Backend Generation** - Automatic API architecture and documentation
- 🧵 **Thread-Based Sessions** - Multi-session conversations with context preservation
- 📊 **ERD Generation** - Automatic entity-relationship diagrams
- 🗄️ **Multi-Dialect Support** - PostgreSQL, MySQL, SQLite

## 🚀 Getting Started

```bash
# Clone the repository
git clone <repository-url>
cd rdbms-builder

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .

# Set up environment (optional)
cp .env.example .env
# Edit .env with your API keys and configuration

# Run the application
python main.py
```

---

## 💾 Long-Term Memory (Checkpointing)

The RDBMS Builder now supports **LangGraph checkpointing** for long-term memory persistence!

### Key Benefits

- **Session Memory** - State persists across multiple runs
- **Error Recovery** - Automatic fault tolerance and resume capability
- **Multi-Session Workflows** - Build complex schemas over time
- **Time Travel** - Inspect and replay past executions

### Quick Start

```python
from main import run_builder
from utils.checkpoint_manager import CheckpointerType

# Run with checkpointing enabled
result = run_builder(
    requirements="Build a blog system...",
    enable_checkpointing=True,
    checkpoint_type=CheckpointerType.SQLITE,  # or POSTGRES
    thread_id="my-project-v1"
)

# Later, resume from the same thread
result = run_builder(
    requirements="Add comments feature...",
    thread_id="my-project-v1",  # Same thread ID!
    enable_checkpointing=True
)
```

### Supported Backends

- **SQLite** - File-based persistence (development)
- **PostgreSQL** - Database persistence (production)
- **Memory** - In-memory only (testing)

📖 **Full Documentation**: [CHECKPOINTING.md](CHECKPOINTING.md)

## 📁 Project Structure

```
rdbms-builder/
├── main.py                          # Entry point
├── CHECKPOINTING.md                 # Checkpointing documentation
├── graph/
│   ├── builder.py                   # LangGraph workflow builder
│   ├── state.py                     # State definitions
│   └── nodes/
│       ├── entity_extractor.py
│       ├── relationship_analyzer.py
│       ├── schema_designer.py
│       ├── sql_generator.py
│       └── validator.py
├── utils/
│   ├── llm.py                       # LLM configuration
│   ├── checkpoint_manager.py        # Checkpointing utilities
│   ├── state_manager.py             # State management
│   └── thread_manager.py            # Thread tracking
├── examples/
│   └── checkpointing_demo.py        # Checkpointing examples
└── data/
    └── checkpoints.db               # SQLite checkpoint storage
```
