import pytest
from dotenv import find_dotenv, load_dotenv
from livekit.agents import AgentSession, inference, llm

from settings import get_settings
from workflow import create_task_from_config, load_workflow_from_yaml

# Load environment variables from .env.local
load_dotenv(find_dotenv(".env.local"), override=True)


def _llm() -> llm.LLM:
    return inference.LLM(model="openai/gpt-4.1-mini")


@pytest.mark.asyncio
async def test_dynamic_first_task_greeting() -> None:
    """Test that first dynamic YAML task greets and asks required info."""
    settings = get_settings()
    workflow_schema = load_workflow_from_yaml(settings.workflow.workflow_path)
    first_task_config = workflow_schema.tasks[0]

    async with (
        _llm() as llm,
        AgentSession(llm=llm) as session,
    ):
        task = create_task_from_config(first_task_config)
        await session.start(task)

        result = await session.run(user_input="Xin chào")

        await (
            result.expect.next_event()
            .is_message(role="assistant")
            .judge(
                llm,
                intent="""
                Starts the configured first workflow step in a professional and friendly tone,
                and asks for the required information of that step as defined in YAML.
                """,
            )
        )

        result.expect.no_more_events()
