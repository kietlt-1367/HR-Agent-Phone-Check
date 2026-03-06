import logging
from typing import Optional

from models.data_storage import InterviewDataStorage, InterviewSession
from models.models import SessionUserData
from livekit.agents import AgentSession

logger = logging.getLogger(__name__)


def get_storage_from_session(session: AgentSession[SessionUserData]) -> Optional[InterviewDataStorage]:
    """Get storage instance from agent session userdata."""
    return session.userdata.storage


def get_interview_session(session: AgentSession[SessionUserData]) -> Optional[InterviewSession]:
    """Get interview session from agent session userdata."""
    return session.userdata.interview_session


def save_to_storage(
    session: AgentSession[SessionUserData],
    field_name: str,
    data: dict
) -> None:
    """
    Save data to interview session storage.
    
    Args:
        session: Agent session containing userdata
        field_name: Name of the field to update (e.g., 'personal_info')
        data: Dictionary of data to save
    """
    storage = get_storage_from_session(session)
    interview_session = get_interview_session(session)
    
    if storage and interview_session:
        setattr(interview_session, field_name, data)
        storage.update_session(interview_session)
        logger.debug(f"Saved {field_name} to session {interview_session.session_id}")
    else:
        logger.warning(f"Could not save {field_name}: storage or session not found")
