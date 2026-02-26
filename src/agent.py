import logging
from dataclasses import dataclass
from typing import List

from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    AgentTask,
    JobContext,
    JobProcess,
    cli,
    inference,
    room_io,
    function_tool,
)
from livekit.agents.beta.workflows import TaskGroup
from livekit.plugins import noise_cancellation, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("agent")

load_dotenv(".env.local")

# Data Models

@dataclass
class PersonalInfo:
    full_name: str
    applied_position: str

@dataclass
class WorkExperience:
    company: str
    title: str
    duration: str

@dataclass
class FitAssessment:
    relevant_skills: str
    reason_for_leaving: str
    expected_salary: str

@dataclass
class AdditionalInfo:
    availability: str
    start_date: str

@dataclass
class ClosingNotes:
    candidate_questions: List[str]


# Workflow Tasks 

class PersonalInfoTask(AgentTask[PersonalInfo]):
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
        await self.session.generate_reply(
            instructions=(
                "Chào ứng viên lịch sự, sau đó hỏi họ tên và vị trí ứng tuyển."
            )
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
        with open("collected_info.txt", "a", encoding="utf-8") as f:
            f.write(f"PersonalInfo: {{'full_name': '{full_name}', 'applied_position': '{applied_position}'}}\n")
        
        self.complete(
            PersonalInfo(
                full_name=full_name,
                applied_position=applied_position,
            )
        )


class WorkExperienceTask(AgentTask[WorkExperience]):
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
        await self.session.generate_reply(
            instructions=(
                "Tiếp theo, cho mình hỏi công việc hiện tại hoặc gần nhất: công ty, vị trí, thời gian làm việc."
            )
        )

    @function_tool
    async def record_recent_job(self, company: str, title: str, duration: str):
        """Ghi nhận thông tin kinh nghiệm làm việc gần nhất"""
        if not company.strip() or not title.strip() or not duration.strip():
            await self.session.generate_reply(
                instructions="Xin lỗi, bạn vui lòng cung cấp đầy đủ thông tin công ty, vị trí và thời gian làm việc."
            )
            return
        
        logger.info("Collected work experience: company=%s, title=%s, duration=%s", company, title, duration)
        with open("collected_info.txt", "a", encoding="utf-8") as f:
            f.write(f"WorkExperience: {{'company': '{company}', 'title': '{title}', 'duration': '{duration}'}}\n")
        
        self.complete(
            WorkExperience(
                company=company,
                title=title,
                duration=duration,
            )
        )


class FitAssessmentTask(AgentTask[FitAssessment]):
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
        await self.session.generate_reply(
            instructions=(
                "Tiếp theo, cho mình hỏi về kỹ năng và kinh nghiệm của bạn liên quan đến vị trí này, cùng lý do bạn rời khỏi công việc gần nhất."
            )
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
        
        logger.info("Collected fit assessment: relevant_skills=%s, reason_for_leaving=%s, expected_salary=%s", relevant_skills, reason_for_leaving, expected_salary)
        with open("collected_info.txt", "a", encoding="utf-8") as f:
            f.write(f"FitAssessment: {{'relevant_skills': '{relevant_skills}', 'reason_for_leaving': '{reason_for_leaving}', 'expected_salary': '{expected_salary}'}}\n")
        
        self.complete(
            FitAssessment(
                relevant_skills=relevant_skills,
                reason_for_leaving=reason_for_leaving,
                expected_salary=expected_salary,
            )
        )


class AdditionalInfoTask(AgentTask[AdditionalInfo]):
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
        await self.session.generate_reply(
            instructions=(
                "Tiếp theo, cho mình hỏi về khả năng nhận việc và thời gian bạn có thể bắt đầu đi làm."
            )
        )

    @function_tool
    async def record_availability(self, availability: str, start_date: str):
        """Ghi nhận thông tin tính khả dụng của ứng viên"""
        if not availability.strip() or not start_date.strip():
            await self.session.generate_reply(
                instructions="Xin lỗi, bạn vui lòng cung cấp đầy đủ thông tin về khả năng nhận việc và thời gian đi làm."
            )
            return
        
        logger.info("Collected additional info: availability=%s, start_date=%s", availability, start_date)
        with open("collected_info.txt", "a", encoding="utf-8") as f:
            f.write(f"AdditionalInfo: {{'availability': '{availability}', 'start_date': '{start_date}'}}\n")
        
        self.complete(
            AdditionalInfo(
                availability=availability,
                start_date=start_date,
            )
        )


class ClosingTask(AgentTask[ClosingNotes]):
    def __init__(self):
        super().__init__(
            instructions="""
            Mục tiêu: Chốt lại buổi phonecheck.

            Quy tắc:
            1. Hỏi ứng viên có câu hỏi nào không.
            2. Cấm trả lời câu hỏi của ứng viên, chỉ ghi nhận.
            3. Hỏi lặp lại "Còn câu hỏi nào khác nữa không?" cho đến khi ứng viên không có câu hỏi gì thêm.
            4. Khi ứng viên không còn câu hỏi, gọi record_closing_notes() với danh sách tất cả câu hỏi.
            5. Sau đó cảm ơn ứng viên vì đã tham gia buổi phỏng vấn, thông báo kết quả sẽ được gửi sau.
            - Không liệt kê lại thông tin cá nhân đã thu thập.
            """
        )

    async def on_enter(self):
        await self.session.generate_reply(
            instructions=(
                "Xác nhận rằng bạn đã có đủ thông tin cần thiết. Hỏi ứng viên có câu hỏi nào thêm không."
            )
        )

    @function_tool
    async def record_closing_notes(self, candidate_questions: List[str]) -> None:
        """Ghi nhận các câu hỏi của ứng viên và hoàn thành buổi phỏng vấn."""

        await self.session.generate_reply(
            instructions="Cảm ơn bạn vì đã tham gia buổi phỏng vấn này. Kết quả sẽ được gửi cho bạn sau."
        )
        
        logger.info("Completing ClosingTask with candidate_questions: %s", candidate_questions)
        with open("collected_info.txt", "a", encoding="utf-8") as f:
            f.write(f"ClosingNotes: {{'candidate_questions': {candidate_questions}}}\n")
        
        self.complete(
            ClosingNotes(
                candidate_questions=candidate_questions,
            )
        )


# Main Agent Implementation

class HRScreeningAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""Bạn là trợ lý tuyển dụng nhân sự của công ty công nghệ cho buổi phone screen.
            Bạn giao tiếp với ứng viên để thu thập thêm thông tin cho công ty.
            Bạn giao tiếp bằng tiếng Việt.
            Trả lời ngắn gọn, chuyên nghiệp và thân thiện.
            Luôn đợi ứng viên nói xong trước khi hỏi tiếp.
            Tuyệt đối không tóm tắt hoặc đọc lại dữ liệu cá nhân trong hội thoại; chỉ ghi nhận nội bộ.""",
        )

    async def on_enter(self):
        tg = TaskGroup(chat_ctx=self.chat_ctx)

        tg.add(
            lambda: PersonalInfoTask(),
            id="personal",
            description="Chào mừng và xác nhận thông tin cá nhân",
        )
        tg.add(
            lambda: WorkExperienceTask(),
            id="experience",
            description="Xác nhận kinh nghiệm làm việc",
        )
        tg.add(
            lambda: FitAssessmentTask(),
            id="fit",
            description="Đánh giá mức độ phù hợp",
        )
        tg.add(
            lambda: AdditionalInfoTask(),
            id="additional",
            description="Kiểm tra thông tin bổ sung & xác thực",
        )
        tg.add(
            lambda: ClosingTask(),
            id="closing",
            description="Chốt buổi phonecheck, cảm ơn ứng viên sau khi kết thúc",
        )

        # Execute the workflow
        logger.info("Starting HR Screening Workflow...")
        results = await tg
        r = results.task_results

        # Access results directly by ID
        final_report = {
            "personal": r.get("personal"),
            "experience": r.get("experience"),
            "fit": r.get("fit"),
            "additional": r.get("additional"),
            "closing": r.get("closing")
        }

        logger.info(f"FINAL INTERVIEW RESULTS: {final_report}")


# Server Setup

server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session()
async def my_agent(ctx: JobContext):
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    try: 
        session = AgentSession(
            # Set language to Vietnamese for the HR screening flow
            stt=inference.STT(model="elevenlabs/scribe_v2_realtime", language="vi"), 
            llm=inference.LLM(model="openai/gpt-4.1-mini"),
            tts=inference.TTS(
                model="cartesia/sonic-3", 
                voice="935a9060-373c-49e4-b078-f4ea6326987a",
                language="vi"
            ),
            turn_detection=MultilingualModel(),
            vad=ctx.proc.userdata["vad"],
            preemptive_generation=True,
        )

        await session.start(
            agent=HRScreeningAgent(),
            room=ctx.room,
            room_options=room_io.RoomOptions(
                audio_input=room_io.AudioInputOptions(
                    noise_cancellation=lambda params: (
                        noise_cancellation.BVCTelephony()
                        if params.participant.kind
                        == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                        else noise_cancellation.BVC()
                    ),
                ),
            ),
        )

        await ctx.connect()
    except Exception as e:
        print(f"Error: {e}")
        ctx.shutdown()


if __name__ == "__main__":
    cli.run_app(server)
