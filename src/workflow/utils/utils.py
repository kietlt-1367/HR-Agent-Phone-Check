import logging

from livekit.agents import AgentSession

from models.data_storage import InterviewDataStorage, InterviewSession
from models.models import SessionUserData

logger = logging.getLogger(__name__)


def get_storage_from_session(
    session: AgentSession[SessionUserData],
) -> InterviewDataStorage | None:
    """Get storage instance from agent session userdata."""
    return session.userdata.storage


def get_interview_session(
    session: AgentSession[SessionUserData],
) -> InterviewSession | None:
    """Get interview session from agent session userdata."""
    return session.userdata.interview_session


def save_to_storage(
    session: AgentSession[SessionUserData],
    task_id: str,
    data: dict,
    task_name: str = "",
    task_description: str = "",
    tool_name: str = "",
) -> None:
    """
    Save data to interview session storage.

    Args:
        session: Agent session containing userdata
        task_id: Workflow task identifier from YAML
        data: Dictionary of data to save
        task_name: Human-readable task name
        task_description: Task description
        tool_name: Function tool name used by this task
    """
    storage = get_storage_from_session(session)
    interview_session = get_interview_session(session)

    if storage and interview_session:
        interview_session.task_data[task_id] = data

        interview_session.task_metadata[task_id] = {
            "name": task_name,
            "description": task_description,
            "tool_name": tool_name,
        }

        if task_id not in interview_session.task_order:
            interview_session.task_order.append(task_id)

        storage.update_session(interview_session)
        logger.debug(f"Saved task '{task_id}' to session {interview_session.session_id}")
    else:
        logger.warning(f"Could not save task '{task_id}': storage or session not found")
