"""Personal information collection task."""

import logging

from livekit.agents import AgentTask, function_tool
from models.models import PersonalInfo
from tasks.utils import save_to_storage

logger = logging.getLogger(__name__)


class PersonalInfoTask(AgentTask[PersonalInfo]):
    """Task to collect candidate's personal information."""
    
    def __init__(self):
        super().__init__(
            instructions="""
            Bạn là trợ lý HR thân thiện.
            Mục tiêu: Chào ứng viên và xác nhận thông tin cá nhân bắt buộc.

            Quy tắc:
            - Hãy giới thiệu bản thân bạn là trợ lý ảo của công ty, sau đó hỏi họ tên và vị trí ứng tuyển.
            - Bắt buộc: Họ tên, vị trí ứng tuyển.
            - Nếu thiếu thông tin, phải hỏi bổ sung cho đủ trước khi chuyển bước.
            - Không tóm tắt hoặc đọc lại dữ liệu cá nhân đã thu thập.
            - Không hỏi "cần hỗ trợ gì thêm" ở bước này.
            - QUAN TRỌNG: Không cảm ơn, không kết thúc cuộc gọi, không nói "sẽ liên hệ lại".
            - Chỉ xác nhận thông tin ngắn gọn khi xong bước này, chờ hệ thống chuyển bước tiếp.
            - Giọng điệu chuyên nghiệp, ấm áp, rõ ràng.
            """
        )

    async def on_enter(self):
        """Entry point: greet candidate and ask for basic info."""
        await self.session.generate_reply(
            instructions="Chào ứng viên lịch sự, sau đó hỏi họ tên và vị trí ứng tuyển."
        )
    
    @function_tool
    async def record_personal_info(self, full_name: str, applied_position: str):
        """Ghi nhận thông tin cá nhân của ứng viên"""
        if not full_name.strip() or not applied_position.strip():
            await self.session.generate_reply(
                instructions="Xin lỗi, bạn vui lòng cung cấp đầy đủ họ tên và vị trí ứng tuyển."
            )
            return
        
        logger.info("Collected personal info: full_name=%s, applied_position=%s", full_name, applied_position)
        
        # Save to session storage
        save_to_storage(
            self.session,
            "personal_info",
            {"full_name": full_name, "applied_position": applied_position}
        )
        
        self.complete(
            PersonalInfo(
                full_name=full_name,
                applied_position=applied_position,
            )
        )
