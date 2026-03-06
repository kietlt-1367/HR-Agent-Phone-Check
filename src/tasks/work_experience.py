"""Work experience collection task."""

import logging

from livekit.agents import AgentTask, function_tool

from models.models import WorkExperience
from tasks.utils import save_to_storage

logger = logging.getLogger(__name__)


class WorkExperienceTask(AgentTask[WorkExperience]):
    """Task to collect candidate's work experience."""

    def __init__(self):
        super().__init__(
            instructions="""
            Mục tiêu: Xác nhận kinh nghiệm làm việc gần nhất.

            Quy tắc:
            - Lắng nghe và xác nhận ngắn gọn trước khi hỏi tiếp.
            - Thu thập: Công ty, vị trí, thời gian làm việc.
            - Hỏi thêm: kỹ năng nổi bật, công nghệ sử dụng, thành tựu đạt được.
            - Không tóm tắt lại dữ liệu cá nhân của ứng viên.
            - QUAN TRỌNG: Không cảm ơn, không kết thúc, không nói "sẽ liên hệ lại".
            - Chỉ xác nhận thông tin ngắn gọn khi xong, chờ hệ thống chuyển bước tiếp.
            """
        )

    async def on_enter(self):
        """Entry point: ask about recent work experience."""
        await self.session.generate_reply(
            instructions="Tiếp theo, cho mình hỏi công việc hiện tại hoặc gần nhất: công ty, vị trí, thời gian làm việc."
        )

    @function_tool
    async def record_recent_job(self, company: str, title: str, duration: str):
        """Ghi nhận thông tin kinh nghiệm làm việc gần nhất"""
        if not company.strip() or not title.strip() or not duration.strip():
            await self.session.generate_reply(
                instructions="Xin lỗi, bạn vui lòng cung cấp đầy đủ thông tin công ty, vị trí và thời gian làm việc."
            )
            return

        logger.info(
            "Collected work experience: company=%s, title=%s, duration=%s",
            company,
            title,
            duration,
        )

        # Save to session storage
        save_to_storage(
            self.session,
            "work_experience",
            {"company": company, "title": title, "duration": duration},
        )

        self.complete(
            WorkExperience(
                company=company,
                title=title,
                duration=duration,
            )
        )
