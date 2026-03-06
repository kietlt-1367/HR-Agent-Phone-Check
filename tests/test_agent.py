import pytest
from dotenv import find_dotenv, load_dotenv
from livekit.agents import AgentSession, inference, llm

from tasks.personal_info import PersonalInfoTask

# Load environment variables from .env.local
load_dotenv(find_dotenv(".env.local"), override=True)


def _llm() -> llm.LLM:
    return inference.LLM(model="openai/gpt-4.1-mini")


@pytest.mark.asyncio
async def test_personal_info_greeting() -> None:
    """Test that PersonalInfoTask greets candidate and asks for name + position."""
    async with (
        _llm() as llm,
        AgentSession(llm=llm) as session,
    ):
        task = PersonalInfoTask()
        await session.start(task)

        result = await session.run(user_input="Xin chào")

        await (
            result.expect.next_event()
            .is_message(role="assistant")
            .judge(
                llm,
                intent="""
                Introduces itself as a professional and friendly HR virtual assistant,
                then asks the candidate for full name and applied position to begin
                the phone screening interview.
                """,
            )
        )

        result.expect.no_more_events()
