import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class InterviewSession:
    """Represents a complete HR interview session with metadata."""

    session_id: str = field(default_factory=lambda: str(uuid4()))
    room_name: Optional[str] = None
    participant_id: Optional[str] = None
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None

    personal_info: Optional[Dict[str, Any]] = None
    work_experience: Optional[Dict[str, Any]] = None
    fit_assessment: Optional[Dict[str, Any]] = None
    additional_info: Optional[Dict[str, Any]] = None
    closing_notes: Optional[Dict[str, Any]] = None
    
    # New fields for analysis
    interview_summary: Optional[Dict[str, Any]] = None
    candidate_scoring: Optional[Dict[str, Any]] = None
    analytics: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in asdict(self).items() if v is not None}


class InterviewDataStorage:
    """
    Thread-safe storage for interview session data.
    
    Features:
    - JSON format (safe for special characters)
    - Session isolation (one file per session)
    - Timestamps and session IDs
    - Configurable storage directory
    - Atomic writes
    """

    def __init__(self, storage_dir: Optional[str] = None):
        """
        Initialize storage.
        
        Args:
            storage_dir: Directory for storing session files. 
                        Defaults to ./interview_data/
        """
        if storage_dir is None:
            storage_dir = "./interview_data"

        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Interview data storage initialized at: {self.storage_dir.absolute()}")

    def create_session(
        self,
        room_name: Optional[str] = None,
        participant_id: Optional[str] = None
    ) -> InterviewSession:
        """Create a new interview session with unique ID."""
        session = InterviewSession(
            room_name=room_name,
            participant_id=participant_id
        )

        # Save initial session file
        self._save_session(session)

        logger.info(f"Created new interview session: {session.session_id}")
        return session

    def update_session(self, session: InterviewSession) -> None:
        """Update existing session data."""
        self._save_session(session)
        logger.debug(f"Updated session: {session.session_id}")

    def complete_session(self, session: InterviewSession) -> None:
        """Mark session as completed with timestamp."""
        session.completed_at = datetime.utcnow().isoformat()
        self._save_session(session)
        logger.info(f"Completed session: {session.session_id}")

    def _save_session(self, session: InterviewSession) -> None:
        """
        Save session data to JSON file atomically.
        
        Uses atomic write pattern: write to temp file, then rename.
        This prevents corruption from concurrent access or crashes.
        """
        file_path = self._get_session_path(session.session_id)
        temp_path = file_path.with_suffix('.tmp')

        try:
            # Write to temp file first
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(session.to_dict(), f, ensure_ascii=False, indent=2)

            # Atomic rename
            temp_path.replace(file_path)

        except Exception as e:
            logger.error(f"Failed to save session {session.session_id}: {e}")
            # Clean up temp file if it exists
            if temp_path.exists():
                temp_path.unlink()
            raise

    def load_session(self, session_id: str) -> Optional[InterviewSession]:
        """Load session from file."""
        file_path = self._get_session_path(session_id)

        if not file_path.exists():
            logger.warning(f"Session file not found: {session_id}")
            return None

        try:
            with open(file_path, encoding='utf-8') as f:
                data = json.load(f)

            return InterviewSession(**data)

        except Exception as e:
            logger.error(f"Failed to load session {session_id}: {e}")
            return None

    def _get_session_path(self, session_id: str) -> Path:
        """Get file path for session."""
        return self.storage_dir / f"session_{session_id}.json"

    def list_sessions(
        self,
        completed_only: bool = False,
        limit: Optional[int] = None
    ) -> List[InterviewSession]:
        """
        List all sessions, sorted by creation time (newest first).
        
        Args:
            completed_only: If True, only return completed sessions
            limit: Maximum number of sessions to return
        """
        sessions = []

        for file_path in sorted(
            self.storage_dir.glob("session_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        ):
            try:
                with open(file_path, encoding='utf-8') as f:
                    data = json.load(f)

                session = InterviewSession(**data)

                if completed_only and session.completed_at is None:
                    continue

                sessions.append(session)

                if limit and len(sessions) >= limit:
                    break

            except Exception as e:
                logger.warning(f"Failed to load session from {file_path}: {e}")

        return sessions

    def get_storage_stats(self) -> Dict[str, Any]:
        """Get statistics about stored sessions."""
        all_files = list(self.storage_dir.glob("session_*.json"))

        total_size = sum(f.stat().st_size for f in all_files)

        sessions = self.list_sessions()
        completed = sum(1 for s in sessions if s.completed_at is not None)

        return {
            "storage_dir": str(self.storage_dir.absolute()),
            "total_sessions": len(sessions),
            "completed_sessions": completed,
            "in_progress_sessions": len(sessions) - completed,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / 1024 / 1024, 2)
        }
