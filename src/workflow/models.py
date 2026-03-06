"""
Workflow configuration models for dynamic task loading.

These models define the YAML schema for workflow configuration.
"""

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field


class FieldValidation(BaseModel):
    """Validation rules for a field."""

    min_length: int | None = None
    max_length: int | None = None
    min: int | None = None
    max: int | None = None
    pattern: str | None = None
    error_message: str | None = None


class TaskField(BaseModel):
    """Definition of a data field to collect in a task."""

    name: str = Field(..., description="Field name (Python identifier)")
    type: str = Field(
        ..., description="Field type: string, integer, float, boolean, list[string]"
    )
    required: bool = Field(default=True, description="Is this field required?")
    description: str = Field(default="", description="Human-readable description")
    validation: FieldValidation | None = Field(
        default=None, description="Validation rules"
    )
    default: Any = Field(default=None, description="Default value if not required")


class TaskConfig(BaseModel):
    """Configuration for a single task in the workflow."""

    id: str = Field(..., description="Unique task identifier")
    name: str = Field(..., description="Human-readable task name")
    description: str = Field(..., description="Brief task description")
    instructions: str = Field(
        ..., description="LLM instructions for this task (Vietnamese)"
    )
    on_enter_prompt: str = Field(
        ..., description="Initial prompt when entering this task"
    )
    tool_name: str = Field(..., description="Name of the function tool")
    tool_description: str = Field(..., description="Description of the function tool")
    fields: list[TaskField] = Field(..., description="Data fields to collect")

    # Optional special behaviors
    generate_summary: bool = Field(
        default=False, description="Generate summary after this task?"
    )
    send_webhook: bool = Field(
        default=False, description="Send webhook after this task?"
    )


class WorkflowConfig(BaseModel):
    """Top-level workflow configuration."""

    name: str = Field(..., description="Workflow name")
    description: str = Field(..., description="Workflow description")
    timeout_seconds: int = Field(
        default=1800, description="Workflow timeout in seconds"
    )
    language: str = Field(default="vi", description="Conversation language")


class WorkflowSchema(BaseModel):
    """Complete workflow schema loaded from YAML."""

    workflow: WorkflowConfig
    tasks: list[TaskConfig]


@dataclass
class DynamicTaskResult:
    """Result of a dynamic task execution."""

    task_id: str
    data: dict[str, Any] = field(default_factory=dict)
