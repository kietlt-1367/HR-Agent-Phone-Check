"""
Main HR Screening Agent implementation.

This agent conducts phone screening interviews in Vietnamese,
collecting candidate information through a structured workflow.
"""

import asyncio
import logging
import time
from datetime import datetime

from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
    inference,
    room_io,
)
from livekit.agents.beta.workflows import TaskGroup
from livekit.plugins import noise_cancellation, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from models.data_storage import InterviewDataStorage
from models.models import InterviewAnalytics, SessionUserData
from settings import get_settings
from tasks.additional_info import AdditionalInfoTask
from tasks.closing import ClosingTask
from tasks.fit_assessment import FitAssessmentTask
from tasks.personal_info import PersonalInfoTask
from tasks.work_experience import WorkExperienceTask

logger = logging.getLogger("agent")

settings = get_settings()


class HRScreeningAgent(Agent):
    """
    HR Screening Agent that conducts structured phone interviews.

    The agent guides candidates through 5 phases:
    1. Personal information collection
    2. Work experience review
    3. Fit assessment
    4. Additional information (availability)
    5. Closing and questions

    After completing all tasks, the agent automatically disconnects.
    """

    def __init__(self, job_ctx: JobContext) -> None:
        super().__init__(
            instructions="""Bạn là trợ lý tuyển dụng nhân sự của công ty công nghệ cho buổi phone screen.
            Bạn giao tiếp với ứng viên để thu thập thêm thông tin cho công ty.
            Bạn giao tiếp bằng tiếng Việt.
            Trả lời ngắn gọn, chuyên nghiệp và thân thiện.
            Luôn đợi ứng viên nói xong trước khi hỏi tiếp.
            Tuyệt đối không tóm tắt hoặc đọc lại dữ liệu cá nhân trong hội thoại; chỉ ghi nhận nội bộ.""",
        )
        self._job_ctx = job_ctx

    async def on_enter(self):
        """Execute the interview workflow and disconnect after completion."""
        workflow_start_at = datetime.utcnow().isoformat()
        workflow_start_time = time.time()
        task_timings = {}

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

        # Execute the workflow with timeout
        logger.info("Starting HR Screening Workflow...")

        try:
            # Run workflow with timeout protection
            results = await asyncio.wait_for(tg, timeout=settings.agent.timeout_seconds)
            r = results.task_results

            # Calculate task timings from task_timings dict if available
            # For now, we'll calculate from results execution
            workflow_end_time = time.time()
            total_duration = workflow_end_time - workflow_start_time

            # Log final results
            final_report = {
                "personal": r.get("personal"),
                "experience": r.get("experience"),
                "fit": r.get("fit"),
                "additional": r.get("additional"),
                "closing": r.get("closing"),
            }

            logger.info(f"FINAL INTERVIEW RESULTS: {final_report}")
            logger.info(f"Interview duration: {total_duration:.2f} seconds")

            # Create analytics data
            analytics = InterviewAnalytics(
                total_duration_seconds=total_duration,
                task_durations=task_timings,
                start_time=workflow_start_at,
                end_time=datetime.utcnow().isoformat(),
                tasks_completed=list(r.keys()),
            )

            # Store analytics in session
            userdata: SessionUserData = self.session.userdata
            userdata.interview_session.analytics = analytics
            userdata.storage.update_session(userdata.interview_session)

        except asyncio.TimeoutError:
            logger.error(
                f"Interview workflow timed out after {settings.agent.timeout_seconds} seconds"
            )
            await self.session.generate_reply(
                instructions="Xin lỗi, phiên phỏng vấn đã hết thời gian. Chúng tôi sẽ liên hệ lại với bạn sau."
            )

        except Exception as e:
            logger.error(f"Error during interview workflow: {e}", exc_info=True)
            await self.session.generate_reply(
                instructions="Xin lỗi, có lỗi xảy ra. Chúng tôi sẽ liên hệ lại với bạn sau."
            )

        finally:
            # Auto-disconnect after completing all tasks (or on error/timeout)
            logger.info("Interview session ending. Disconnecting agent...")
            self._job_ctx.shutdown()


# Server Setup

server = AgentServer(
    ws_url=settings.livekit_url,
    api_key=settings.livekit_api_key,
    api_secret=settings.livekit_api_secret,
)


def prewarm(proc: JobProcess):
    """Prewarm VAD model for faster startup."""
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session()
async def my_agent(ctx: JobContext):
    """
    Main entry point for agent sessions.

    Sets up storage, creates agent session, and handles lifecycle.
    """
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    try:
        # Initialize data storage
        storage = InterviewDataStorage(storage_dir=settings.storage.data_dir)
        interview_session = storage.create_session(
            room_name=ctx.room.name,
            participant_id=None,  # Will be set when participant joins
        )

        logger.info(f"Created interview session: {interview_session.session_id}")

        # Create userdata instance
        userdata = SessionUserData(storage=storage, interview_session=interview_session)

        session = AgentSession[SessionUserData](
            userdata=userdata,
            # Set language to Vietnamese for the HR screening flow
            stt=inference.STT(model=settings.stt.model, language=settings.stt.language),
            llm=inference.LLM(model=settings.llm.model),
            tts=inference.TTS(
                model=settings.tts.model,
                voice=settings.tts.voice,
                language=settings.tts.language,
            ),
            turn_detection=MultilingualModel(),
            vad=ctx.proc.userdata["vad"],
            preemptive_generation=settings.agent.preemptive_generation,
        )

        await session.start(
            agent=HRScreeningAgent(ctx),
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

        logger.info(f"Session ended for interview: {interview_session.session_id}")

    except Exception as e:
        logger.error(f"Error in agent session: {e}", exc_info=True)
        ctx.shutdown()


if __name__ == "__main__":
    cli.run_app(server)
