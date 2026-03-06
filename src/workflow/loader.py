"""
Dynamic workflow loader and generic task implementation.

This module allows loading workflow configurations from YAML
and generating AgentTask instances dynamically.
"""

import inspect
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml
from livekit.agents import AgentTask, function_tool

from infra import prepare_interview_payload, send_interview_webhook
from models.data_storage import InterviewDataStorage, InterviewSession
from settings import get_settings
from summary_generator import generate_summary_and_scoring
from workflow.models import DynamicTaskResult, TaskConfig, WorkflowSchema
from workflow.utils import (
    get_interview_session,
    get_storage_from_session,
    save_to_storage,
)

logger = logging.getLogger(__name__)


def build_runtime_task_instructions(task_config: TaskConfig) -> str:
    """Build strict runtime instructions to improve task completion reliability."""
    required_fields = [field.name for field in task_config.fields if field.required]
    optional_fields = [field.name for field in task_config.fields if not field.required]

    required_text = ", ".join(required_fields) if required_fields else "(không có)"
    optional_text = ", ".join(optional_fields) if optional_fields else "(không có)"

    protocol = f"""

QUY TẮC BẮT BUỘC THỰC THI TASK:
- Trường bắt buộc: {required_text}
- Trường không bắt buộc: {optional_text}
- Ngay khi đã có đủ trường bắt buộc, PHẢI gọi tool `{task_config.tool_name}` đúng 1 lần với dữ liệu đã thu thập.
- Sau khi gọi tool, dừng bước hiện tại và chờ hệ thống chuyển task; không tiếp tục xác nhận lặp lại.
- Không nói các câu kiểu "vui lòng chờ hệ thống chuyển bước" nhiều lần.
- Nếu thiếu trường bắt buộc, chỉ hỏi đúng phần còn thiếu.
""".strip()

    return f"{task_config.instructions.strip()}\n\n{protocol}"


def load_workflow_from_yaml(yaml_path: str | Path) -> WorkflowSchema:
    """
    Load workflow configuration from YAML file.

    Args:
        yaml_path: Path to the YAML workflow configuration file (relative or absolute)

    Returns:
        WorkflowSchema: Validated workflow configuration

    Raises:
        FileNotFoundError: If YAML file doesn't exist
        ValueError: If YAML structure is invalid
    """
    yaml_path = Path(yaml_path)

    # Resolve relative paths from project root
    if not yaml_path.is_absolute():
        project_root = Path(__file__).parent.parent.parent
        yaml_path = project_root / yaml_path

    if not yaml_path.exists():
        raise FileNotFoundError(f"Workflow YAML not found: {yaml_path}")

    with open(yaml_path, encoding="utf-8") as f:
        raw_data = yaml.safe_load(f)

    try:
        schema = WorkflowSchema(**raw_data)
        logger.info(
            f"Loaded workflow: {schema.workflow.name} with {len(schema.tasks)} tasks"
        )
        return schema
    except Exception as e:
        raise ValueError(f"Invalid workflow YAML structure: {e}") from e


def validate_field_value(
    field_name: str, value: Any, field_config: Any
) -> tuple[bool, str | None]:
    """
    Validate a field value against its configuration.

    Args:
        field_name: Name of the field
        value: Value to validate
        field_config: TaskField configuration

    Returns:
        Tuple of (is_valid, error_message)
    """
    if field_config.required and (value is None or value == ""):
        return False, f"{field_name} là bắt buộc"

    if value is None:
        return True, None

    validation = field_config.validation
    if not validation:
        return True, None

    # String validations
    if field_config.type == "string" and isinstance(value, str):
        if validation.min_length and len(value) < validation.min_length:
            return (
                False,
                validation.error_message
                or f"{field_name} phải có ít nhất {validation.min_length} ký tự",
            )
        if validation.max_length and len(value) > validation.max_length:
            return (
                False,
                validation.error_message
                or f"{field_name} không được vượt quá {validation.max_length} ký tự",
            )

    # Integer validations
    if field_config.type == "integer" and isinstance(value, int):
        if validation.min is not None and value < validation.min:
            return (
                False,
                validation.error_message
                or f"{field_name} phải lớn hơn hoặc bằng {validation.min}",
            )
        if validation.max is not None and value > validation.max:
            return (
                False,
                validation.error_message
                or f"{field_name} phải nhỏ hơn hoặc bằng {validation.max}",
            )

    return True, None


class DynamicTask(AgentTask[DynamicTaskResult]):
    """
    Generic task implementation that executes based on YAML configuration.

    This task dynamically creates function tools based on field definitions
    and handles data collection according to the workflow configuration.
    """

    def __init__(self, task_config: TaskConfig):
        """
        Initialize a dynamic task from configuration.

        Args:
            task_config: TaskConfig from workflow YAML
        """
        self.task_config = task_config
        dynamic_tool = self._build_tool()
        setattr(self, self.task_config.tool_name, dynamic_tool)
        super().__init__(instructions=build_runtime_task_instructions(task_config))

    def _build_tool(self):
        """Build the function tool dynamically based on field configuration."""
        # Build the tool function with proper type annotations
        tool_name = self.task_config.tool_name
        tool_description = self.task_config.tool_description

        # Map YAML types to Python types
        type_mapping = {
            "string": str,
            "integer": int,
            "float": float,
            "boolean": bool,
            "list[string]": list[str],
        }

        # Build parameter annotations
        annotations = {}
        signature_parameters = []
        for field_config in self.task_config.fields:
            field_type = type_mapping.get(field_config.type, str)
            if not field_config.required:
                # Optional field with default
                annotations[field_config.name] = field_type | None
                signature_parameters.append(
                    inspect.Parameter(
                        field_config.name,
                        kind=inspect.Parameter.KEYWORD_ONLY,
                        default=field_config.default,
                        annotation=field_type | None,
                    )
                )
            else:
                annotations[field_config.name] = field_type
                signature_parameters.append(
                    inspect.Parameter(
                        field_config.name,
                        kind=inspect.Parameter.KEYWORD_ONLY,
                        annotation=field_type,
                    )
                )

        # Create the tool function with dynamic signature
        async def dynamic_tool(**kwargs):
            return await self._handle_tool_call(**kwargs)

        # Set function metadata
        dynamic_tool.__name__ = tool_name
        dynamic_tool.__doc__ = tool_description
        dynamic_tool.__annotations__ = annotations
        dynamic_tool.__signature__ = inspect.Signature(
            parameters=signature_parameters,
            return_annotation=type(None),
        )

        # Apply function_tool decorator
        return function_tool(dynamic_tool)

    async def _handle_tool_call(self, **kwargs) -> None:
        """
        Handle the dynamic tool call with validation.

        Args:
            **kwargs: Field values provided by the LLM
        """
        logger.info(f"Task '{self.task_config.id}' received data: {kwargs}")

        # Validate all fields
        errors = []
        validated_data = {}

        for field_config in self.task_config.fields:
            field_name = field_config.name
            value = kwargs.get(field_name)

            # Use default if not provided and not required
            if value is None and not field_config.required:
                value = field_config.default

            # Validate
            is_valid, error_msg = validate_field_value(field_name, value, field_config)
            if not is_valid:
                errors.append(error_msg)
            else:
                validated_data[field_name] = value

        # If there are validation errors, ask for correction
        if errors:
            error_text = " ".join(errors)
            await self.session.generate_reply(
                instructions=f"Xin lỗi, có lỗi: {error_text}. Vui lòng cung cấp lại thông tin."
            )
            return

        # Save dynamic task data directly by task_id
        save_to_storage(
            self.session,
            self.task_config.id,
            validated_data,
            task_name=self.task_config.name,
            task_description=self.task_config.description,
            tool_name=self.task_config.tool_name,
        )

        # Handle special closing task behavior
        if self.task_config.generate_summary or self.task_config.send_webhook:
            await self._handle_closing_task(validated_data)

        # Complete task with result
        result = DynamicTaskResult(
            task_id=self.task_config.id,
            data=validated_data,
        )
        self.complete(result)

        logger.info(f"Task '{self.task_config.id}' completed successfully")

    async def _handle_closing_task(self, validated_data: dict[str, Any]) -> None:
        """
        Handle special logic for closing task: summary generation and webhook.

        Args:
            validated_data: The validated closing task data
        """
        # Thank the candidate first
        await self.session.generate_reply(
            instructions="Cảm ơn bạn vì đã tham gia buổi phỏng vấn này. Kết quả sẽ được gửi cho bạn sau."
        )

        # Get session and storage
        storage: InterviewDataStorage = get_storage_from_session(self.session)
        session: InterviewSession = get_interview_session(self.session)

        if not storage or not session:
            logger.error("Storage or session not available for closing task")
            return

        # Generate summary and scoring if enabled
        if self.task_config.generate_summary:
            try:
                # Generate summary and scoring
                logger.info("Generating summary and scoring...")
                settings = get_settings()
                summary, scoring = await generate_summary_and_scoring(
                    gemini_api_key=settings.gemini_api_key,
                    gemini_model=settings.llm.gemini_model,
                    workflow_name=session.workflow_name,
                    workflow_description=session.workflow_description,
                    task_data=session.task_data,
                    task_metadata=session.task_metadata,
                    task_order=session.task_order,
                )

                # Store in session
                summary_dict = asdict(summary)
                scoring_dict = asdict(scoring)
                session.summary = summary_dict
                session.scoring = scoring_dict

                logger.info(
                    f"Summary generated - Recommendation: {summary.recommendation}"
                )
                logger.info(f"Scoring - Overall: {scoring.overall_score}/10")

            except Exception as e:
                logger.error(f"Error generating summary/scoring: {e}", exc_info=True)

        # Complete session
        storage.complete_session(session)

        # Send webhook if enabled
        if self.task_config.send_webhook:
            settings = get_settings()
            webhook_url = settings.hr_webhook_url  # Only from ENV
            if webhook_url:
                try:
                    logger.info(
                        f"Sending interview results to webhook: {webhook_url}"
                    )

                    # Prepare payload
                    payload = prepare_interview_payload(session.to_dict())

                    # Send webhook with retries
                    result = await send_interview_webhook(
                        webhook_url=webhook_url,
                        interview_data=payload,
                        timeout_seconds=settings.webhook.timeout_seconds,
                        retry_count=settings.webhook.retry_count,
                        retry_delay_seconds=settings.webhook.retry_delay_seconds,
                    )

                    if result.success:
                        logger.info(
                            f"Webhook sent successfully (status {result.status_code})"
                        )
                    else:
                        logger.error(f"Webhook failed: {result.error}")

                except Exception as e:
                    logger.error(f"Error sending webhook: {e}", exc_info=True)
            else:
                logger.debug("HR_WEBHOOK_URL not configured, skipping webhook send")

    async def on_enter(self):
        """Entry point when task starts."""
        await self.session.generate_reply(instructions=self.task_config.on_enter_prompt)


def create_task_from_config(task_config: TaskConfig) -> AgentTask:
    """
    Factory function to create a task instance from configuration.

    Args:
        task_config: TaskConfig from workflow YAML

    Returns:
        AgentTask instance
    """
    return DynamicTask(task_config)
