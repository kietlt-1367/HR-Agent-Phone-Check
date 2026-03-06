"""Fit assessment task."""

import logging

from livekit.agents import AgentTask, function_tool
from models.models import FitAssessment
from tasks.utils import save_to_storage

logger = logging.getLogger(__name__)


class FitAssessmentTask(AgentTask[FitAssessment]):
    """Task to assess candidate's fit for the position."""
    
    def __init__(self):
        super().__init__(
            instructions="""
            Mục tiêu: Đánh giá mức độ phù hợp với vị trí ứng tuyển.

            Quy tắc:
            - Hỏi các câu liên quan kỹ năng, kinh nghiệm phù hợp.
            - Hỏi lý do nghỉ việc.
            - Hỏi mong muốn công việc mới và mức lương kỳ vọng.
            - Đảm bảo thu thập đầy đủ thông tin trước khi chuyển bước.
            - Không tóm tắt dữ liệu ứng viên trong cuộc hội thoại.
            - QUAN TRỌNG: Không cảm ơn, không kết thúc, không nói "sẽ liên hệ lại".
            - Chỉ xác nhận ngắn gọn khi xong, chờ hệ thống chuyển bước tiếp.
            """
        )

    async def on_enter(self):
        """Entry point: ask about skills and fit assessment."""
        await self.session.generate_reply(
            instructions="Tiếp theo, cho mình hỏi về kỹ năng và kinh nghiệm của bạn liên quan đến vị trí này, cùng lý do bạn rời khỏi công việc gần nhất."
        )

    @function_tool
    async def record_fit_assessment(
        self,
        relevant_skills: str,
        reason_for_leaving: str,
        expected_salary: str,
    ):
        """Ghi nhận đánh giá mức độ phù hợp của ứng viên"""
        if not relevant_skills.strip() or not reason_for_leaving.strip() or not expected_salary.strip():
            await self.session.generate_reply(
                instructions="Xin lỗi, bạn vui lòng cung cấp đầy đủ thông tin về kỹ năng, lý do rời khỏi công việc, và mức lương kỳ vọng."
            )
            return
        
        logger.info("Collected fit assessment: relevant_skills=%s, reason_for_leaving=%s, expected_salary=%s", 
                   relevant_skills, reason_for_leaving, expected_salary)
        
        # Save to session storage
        save_to_storage(
            self.session,
            "fit_assessment",
            {
                "relevant_skills": relevant_skills,
                "reason_for_leaving": reason_for_leaving,
                "expected_salary": expected_salary
            }
        )
        
        self.complete(
            FitAssessment(
                relevant_skills=relevant_skills,
                reason_for_leaving=reason_for_leaving,
                expected_salary=expected_salary,
            )
        )
