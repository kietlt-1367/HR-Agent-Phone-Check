"""Additional information collection task."""

import logging

from livekit.agents import AgentTask, function_tool

from models.models import AdditionalInfo
from tasks.utils import save_to_storage

logger = logging.getLogger(__name__)


class AdditionalInfoTask(AgentTask[AdditionalInfo]):
    """Task to collect additional information about availability."""

    def __init__(self):
        super().__init__(
            instructions="""
            Mục tiêu: Kiểm tra thông tin bổ sung và xác thực.

            Quy tắc:
            - Hỏi khả năng nhận việc và thời gian có thể đi làm.
            - Không đọc lại dữ liệu cá nhân đã thu thập.
            - QUAN TRỌNG: Không cảm ơn, không kết thúc, không nói "sẽ liên hệ lại".
            - Chỉ xác nhận ngắn gọn khi xong, chờ hệ thống chuyển bước tiếp.
            """
        )

    async def on_enter(self):
        """Entry point: ask about availability."""
        await self.session.generate_reply(
            instructions="Tiếp theo, cho mình hỏi về khả năng nhận việc và thời gian bạn có thể bắt đầu đi làm."
        )

    @function_tool
    async def record_availability(self, availability: str, start_date: str):
        """Ghi nhận thông tin tính khả dụng của ứng viên"""
        if not availability.strip() or not start_date.strip():
            await self.session.generate_reply(
                instructions="Xin lỗi, bạn vui lòng cung cấp đầy đủ thông tin về khả năng nhận việc và thời gian đi làm."
            )
            return

        logger.info(
            "Collected additional info: availability=%s, start_date=%s",
            availability,
            start_date,
        )

        # Save to session storage
        save_to_storage(
            self.session,
            "additional_info",
            {"availability": availability, "start_date": start_date},
        )

        self.complete(
            AdditionalInfo(
                availability=availability,
                start_date=start_date,
            )
        )
