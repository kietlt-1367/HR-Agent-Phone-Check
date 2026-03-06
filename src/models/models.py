from dataclasses import dataclass, field
from datetime import datetime

from models.data_storage import InterviewDataStorage, InterviewSession


@dataclass
class SessionUserData:
    """Custom user data for agent session."""

    storage: InterviewDataStorage
    interview_session: InterviewSession


@dataclass
class CandidateScoring:
    """Standardized scoring rubric for candidates."""

    communication_score: float  # 1-10
    experience_fit_score: float  # 1-10
    salary_alignment_score: float  # 1-10
    overall_score: float  # Average of above three
    communication_feedback: str
    experience_fit_feedback: str
    salary_alignment_feedback: str


@dataclass
class InterviewSummary:
    """AI-generated interview summary and evaluation."""

    strengths: list[str]  # Key strengths identified
    concerns: list[str]  # Concerns or red flags
    recommendation: str  # proceed / maybe / pass
    summary_text: str  # Free-form summary


@dataclass
class InterviewAnalytics:
    """Analytics and timing data for interview."""

    total_duration_seconds: float
    task_durations: dict = field(
        default_factory=dict
    )  # {"personal": 120, "experience": 180, ...}
    start_time: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    end_time: str = ""
    tasks_completed: list[str] = field(default_factory=list)
