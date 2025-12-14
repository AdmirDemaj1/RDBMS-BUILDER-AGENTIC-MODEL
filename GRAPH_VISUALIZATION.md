# RDBMS Builder - Graph Visualization

This document contains Mermaid diagrams for visualizing the RDBMS Builder LangGraph workflows.

## Main Graph (Initial Execution)

```mermaid
graph TD
    START([START]) --> plan[Plan]
    plan --> clarify[Clarify]
    
    clarify -->|needs_clarification| END1([END - Wait for User Input])
    clarify -->|proceed| extract[Extract Entities]
    
    extract --> analyze[Analyze Relationships]
    analyze --> design[Design Schema]
    design --> verify_initial[Verify Initial Schema]
    verify_initial --> validate[Validate Schema]
    
    validate -->|enable_critic = false| parallel_trigger1[Parallel Trigger]
    validate -->|enable_critic = true| critic[Critic Review]
    
    critic -->|requires_revision = false| parallel_trigger2[Parallel Trigger]
    critic -->|requires_revision = true| refine[Refine Schema]
    
    refine --> verify_refine[Verify Refinements]
    
    verify_refine -->|revision_count < max| critic
    verify_refine -->|revision_count >= max| parallel_trigger3[Parallel Trigger]
    
    parallel_trigger1 --> sql[Generate SQL]
    parallel_trigger1 --> erd[Generate ERD]
    parallel_trigger1 --> nestjs[Generate NestJS]
    
    parallel_trigger2 --> sql
    parallel_trigger2 --> erd
    parallel_trigger2 --> nestjs
    
    parallel_trigger3 --> sql
    parallel_trigger3 --> erd
    parallel_trigger3 --> nestjs
    
    sql --> aggregator[Aggregator]
    erd --> aggregator
    nestjs --> aggregator
    
    aggregator --> END2([END - Complete])
    
    style START fill:#90EE90
    style END1 fill:#FFB6C1
    style END2 fill:#90EE90
    style parallel_trigger1 fill:#FFE4B5
    style parallel_trigger2 fill:#FFE4B5
    style parallel_trigger3 fill:#FFE4B5
    style sql fill:#87CEEB
    style erd fill:#87CEEB
    style nestjs fill:#87CEEB
    style aggregator fill:#DDA0DD
    style critic fill:#FFD700
    style refine fill:#FFD700
```

## Continuation Graph (After User Clarification)

```mermaid
graph TD
    START([START - Resume]) --> extract[Extract Entities]
    
    extract --> analyze[Analyze Relationships]
    analyze --> design[Design Schema]
    design --> verify_initial[Verify Initial Schema]
    verify_initial --> validate[Validate Schema]
    
    validate -->|enable_critic = false| parallel_trigger1[Parallel Trigger]
    validate -->|enable_critic = true| critic[Critic Review]
    
    critic -->|requires_revision = false| parallel_trigger2[Parallel Trigger]
    critic -->|requires_revision = true| refine[Refine Schema]
    
    refine --> verify_refine[Verify Refinements]
    
    verify_refine -->|revision_count < max| critic
    verify_refine -->|revision_count >= max| parallel_trigger3[Parallel Trigger]
    
    parallel_trigger1 --> sql[Generate SQL]
    parallel_trigger1 --> erd[Generate ERD]
    parallel_trigger1 --> nestjs[Generate NestJS]
    
    parallel_trigger2 --> sql
    parallel_trigger2 --> erd
    parallel_trigger2 --> nestjs
    
    parallel_trigger3 --> sql
    parallel_trigger3 --> erd
    parallel_trigger3 --> nestjs
    
    sql --> aggregator[Aggregator]
    erd --> aggregator
    nestjs --> aggregator
    
    aggregator --> END([END - Complete])
    
    style START fill:#90EE90
    style END fill:#90EE90
    style parallel_trigger1 fill:#FFE4B5
    style parallel_trigger2 fill:#FFE4B5
    style parallel_trigger3 fill:#FFE4B5
    style sql fill:#87CEEB
    style erd fill:#87CEEB
    style nestjs fill:#87CEEB
    style aggregator fill:#DDA0DD
    style critic fill:#FFD700
    style refine fill:#FFD700
```

## Simplified Overview (All Paths Combined)

```mermaid
graph LR
    START([START]) --> A[Planning & Clarification]
    A -->|User Input Needed| WAIT([Wait])
    A -->|Ready| B[Schema Design Pipeline]
    WAIT --> B
    
    B --> C{Critic Enabled?}
    C -->|No| D[Parallel Generation]
    C -->|Yes| E[Critic Review Loop]
    
    E -->|Needs Refinement| F[Refine & Verify]
    F --> E
    E -->|Approved| D
    
    D --> G[Generate SQL]
    D --> H[Generate ERD]
    D --> I[Generate NestJS]
    
    G --> J[Aggregator]
    H --> J
    I --> J
    
    J --> END([END])
    
    style START fill:#90EE90
    style END fill:#90EE90
    style WAIT fill:#FFB6C1
    style D fill:#FFE4B5
    style E fill:#FFD700
    style F fill:#FFD700
    style G fill:#87CEEB
    style H fill:#87CEEB
    style I fill:#87CEEB
    style J fill:#DDA0DD
```

## Node Details

### Planning Phase
- **plan**: Creates execution plan and task breakdown
- **clarify**: Identifies missing information and generates clarifying questions

### Schema Design Phase
- **extract_entities**: Identifies domain entities from requirements
- **analyze_relationships**: Determines relationships between entities
- **design_schema**: Creates initial database schema design
- **verify_initial_schema**: Validates the initial schema design

### Quality Assurance Phase
- **validate_schema**: Runs validation checks on schema
- **critic**: Reviews schema quality and provides feedback
- **refine_schema**: Improves schema based on critic feedback
- **verify_refinements**: Validates refined schema changes

### Generation Phase (Parallel Execution)
- **parallel_trigger**: Synchronization point for parallel execution
- **generate_sql**: Creates DDL scripts
- **generate_erd**: Creates Entity-Relationship Diagram (Mermaid format)
- **generate_nestjs**: Generates NestJS backend architecture

### Completion Phase
- **aggregator**: Collects all parallel generation outputs

## Conditional Logic

### should_clarify
- **needs_clarification**: User input required → END
- **proceed**: Continue to entity extraction

### should_run_critic
- **run_critic**: Critic enabled → Run critic review
- **generate_outputs**: Critic disabled → Skip to generation

### should_refine
- **refine**: Requires revision AND revision_count ≤ max_revisions
- **generate_outputs**: No refinement needed OR max revisions reached

### should_re_critique
- **re_critique**: revision_count < max_revisions → Run critic again
- **generate_outputs**: Max revisions reached → Proceed to generation

## Color Legend

- 🟢 **Green**: Start/End nodes
- 🔵 **Blue**: Generation nodes (parallel execution)
- 🟡 **Yellow**: Critic/refinement nodes
- 🟣 **Purple**: Aggregator/synchronization
- 🟠 **Orange**: Parallel trigger
- 🔴 **Pink**: Wait/pause state

## Usage Notes

1. The main graph handles initial execution and may pause for user clarification
2. The continuation graph resumes after user provides answers
3. Critic loop can run up to `max_critic_revisions` times (default: 2)
4. SQL, ERD, and NestJS generation run in parallel for performance
5. Checkpointing saves state at each node for resumability

## Integration with Excalidraw

To use in Excalidraw:
1. Copy any of the Mermaid code blocks above
2. In Excalidraw: Insert → Mermaid
3. Paste the code
4. The diagram will render automatically
5. You can then customize styling and layout in Excalidraw

