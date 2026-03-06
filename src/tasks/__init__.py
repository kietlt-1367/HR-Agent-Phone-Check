from __future__ import annotations

from .additional_info import AdditionalInfoTask
from .closing import ClosingTask
from .fit_assessment import FitAssessmentTask
from .personal_info import PersonalInfoTask
from .work_experience import WorkExperienceTask

__all__ = [
    "PersonalInfoTask",
    "WorkExperienceTask",
    "FitAssessmentTask",
    "AdditionalInfoTask",
    "ClosingTask",
]
