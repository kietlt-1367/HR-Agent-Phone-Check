import inspect

from workflow.loader import DynamicTask, build_runtime_task_instructions
from workflow.models import TaskConfig, TaskField


def test_dynamic_tool_exposes_yaml_fields_in_signature() -> None:
    task_config = TaskConfig(
        id="sample",
        name="Sample",
        description="Collect sample data",
        instructions="Collect sample data",
        on_enter_prompt="Start",
        tool_name="record_sample",
        tool_description="Record sample",
        fields=[
            TaskField(
                name="full_name",
                type="string",
                required=True,
                description="Candidate name",
            ),
            TaskField(
                name="years_of_experience",
                type="integer",
                required=False,
                description="Years",
                default=0,
            ),
        ],
    )

    task = DynamicTask(task_config)
    tool = task.record_sample
    signature = inspect.signature(tool)

    assert list(signature.parameters.keys()) == [
        "full_name",
        "years_of_experience",
    ]
    assert all(
        parameter.kind == inspect.Parameter.KEYWORD_ONLY
        for parameter in signature.parameters.values()
    )
    assert signature.parameters["full_name"].default is inspect.Parameter.empty
    assert signature.parameters["years_of_experience"].default == 0

    tool_names = [tool.info.name for tool in task.tools if hasattr(tool, "info")]
    assert "record_sample" in tool_names


def test_runtime_instructions_enforce_tool_call_protocol() -> None:
    task_config = TaskConfig(
        id="personal",
        name="Personal",
        description="Collect personal info",
        instructions="Thu thập thông tin cá nhân.",
        on_enter_prompt="Hỏi thông tin",
        tool_name="record_personal_info",
        tool_description="Record personal info",
        fields=[
            TaskField(
                name="full_name",
                type="string",
                required=True,
                description="Candidate name",
            ),
            TaskField(
                name="applied_position",
                type="string",
                required=True,
                description="Applied position",
            ),
        ],
    )

    instructions = build_runtime_task_instructions(task_config)

    assert "record_personal_info" in instructions
    assert "PHẢI gọi tool" in instructions
    assert "không tiếp tục xác nhận lặp lại" in instructions
    assert "vui lòng chờ hệ thống chuyển bước" in instructions
