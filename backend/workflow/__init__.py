"""
Workflow module for skill orchestration.

This module provides:
- File I/O for workflow definitions and execution records
- Workflow execution engine
- Orchestration agent for natural language interaction
- Data models for workflows, nodes, and edges
- Skill invoker for executing skills via OpenClaw Gateway
"""

from .models import (
    Workflow,
    WorkflowNode,
    WorkflowEdge,
    InputParam,
    Execution,
    NodeExecution
)

from .io import (
    WorkflowIO,
    ExecutionIO,
    OutputIO
)

from .engine import (
    WorkflowEngine,
    MockSkillInvoker
)

from .agent import OrchestrationAgent

from .skill_invoker import (
    SkillInvoker,
    create_skill_invoker
)

__all__ = [
    # Models
    'Workflow',
    'WorkflowNode',
    'WorkflowEdge',
    'InputParam',
    'Execution',
    'NodeExecution',

    # I/O
    'WorkflowIO',
    'ExecutionIO',
    'OutputIO',

    # Engine
    'WorkflowEngine',
    'MockSkillInvoker',

    # Agent
    'OrchestrationAgent',

    # Skill Invoker
    'SkillInvoker',
    'create_skill_invoker',
]