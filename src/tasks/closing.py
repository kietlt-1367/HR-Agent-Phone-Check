"""Closing task to finalize interview."""

import logging
from dataclasses import asdict

from livekit.agents import AgentTask, function_tool

from infra import prepare_interview_payload, send_interview_webhook
from models.data_storage import InterviewDataStorage, InterviewSession
from models.models import (
    AdditionalInfo,
    ClosingNotes,
    FitAssessment,
    PersonalInfo,
    WorkExperience,
)
from settings import get_settings
from summary_generator import generate_summary_and_scoring
from tasks.utils import get_interview_session, get_storage_from_session

logger = logging.getLogger(__name__)


class ClosingTask(AgentTask[ClosingNotes]):
    """Task to close the interview and collect final questions."""

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
        """Entry point: ask if candidate has questions."""
        await self.session.generate_reply(
            instructions="Xác nhận rằng bạn đã có đủ thông tin cần thiết. Hỏi ứng viên có câu hỏi nào thêm không."
        )

    @function_tool
    async def record_closing_notes(self, candidate_questions: list[str]) -> None:
        """Ghi nhận các câu hỏi của ứng viên, generate summary & scoring, và hoàn thành buổi phỏng vấn."""

        await self.session.generate_reply(
            instructions="Cảm ơn bạn vì đã tham gia buổi phỏng vấn này. Kết quả sẽ được gửi cho bạn sau."
        )

        logger.info(
            "Completing ClosingTask with candidate_questions: %s", candidate_questions
        )

        # Get session and storage
        storage: InterviewDataStorage = get_storage_from_session(self.session)
        session: InterviewSession = get_interview_session(self.session)

        if storage and session:
            session.closing_notes = {"candidate_questions": candidate_questions}

            # Generate summary and scoring using LLM
            try:
                # Parse data from session
                personal_data = session.personal_info
                personal_info = (
                    PersonalInfo(
                        full_name=personal_data.get("full_name", "Unknown")
                        if personal_data
                        else "Unknown",
                        applied_position=personal_data.get(
                            "applied_position", "Unknown"
                        )
                        if personal_data
                        else "Unknown",
                    )
                    if personal_data
                    else None
                )

                work_data = session.work_experience
                work_experience = (
                    WorkExperience(
                        company=work_data.get("company", "") if work_data else "",
                        title=work_data.get("title", "") if work_data else "",
                        duration=work_data.get("duration", "") if work_data else "",
                    )
                    if work_data
                    else None
                )

                fit_data = session.fit_assessment
                fit_assessment = (
                    FitAssessment(
                        relevant_skills=fit_data.get("relevant_skills", "")
                        if fit_data
                        else "",
                        reason_for_leaving=fit_data.get("reason_for_leaving", "")
                        if fit_data
                        else "",
                        expected_salary=fit_data.get("expected_salary", "")
                        if fit_data
                        else "",
                    )
                    if fit_data
                    else None
                )

                additional_data = session.additional_info
                additional_info = (
                    AdditionalInfo(
                        availability=additional_data.get("availability", "")
                        if additional_data
                        else "",
                        start_date=additional_data.get("start_date", "")
                        if additional_data
                        else "",
                    )
                    if additional_data
                    else None
                )

                closing_data = session.closing_notes
                closing_notes = (
                    ClosingNotes(
                        candidate_questions=closing_data.get("candidate_questions", [])
                        if closing_data
                        else [],
                    )
                    if closing_data
                    else None
                )

                # Generate summary and scoring
                logger.info("Generating summary and scoring...")
                settings = get_settings()
                summary, scoring = await generate_summary_and_scoring(
                    gemini_api_key=settings.gemini_api_key,
                    gemini_model=settings.llm.gemini_model,
                    personal_info=personal_info,
                    work_experience=work_experience,
                    fit_assessment=fit_assessment,
                    additional_info=additional_info,
                    closing_notes=closing_notes,
                )

                # Store in session
                session.interview_summary = asdict(summary)
                session.candidate_scoring = asdict(scoring)

                logger.info(
                    f"Summary generated - Recommendation: {summary.recommendation}"
                )
                logger.info(f"Scoring - Overall: {scoring.overall_score}/10")

            except Exception as e:
                logger.error(f"Error generating summary/scoring: {e}", exc_info=True)

            storage.complete_session(session)

            # Send webhook if configured
            settings = get_settings()
            if settings.webhook.url:
                try:
                    logger.info(
                        f"Sending interview results to webhook: {settings.webhook.url}"
                    )

                    # Prepare payload
                    payload = prepare_interview_payload(session.to_dict())

                    # Send webhook with retries
                    result = await send_interview_webhook(
                        webhook_url=settings.webhook.url,
                        interview_data=payload,
                        timeout_seconds=settings.webhook.timeout_seconds,
                        retry_count=settings.webhook.retry_count,
                        retry_delay_seconds=settings.webhook.retry_delay_seconds,
                    )

                    if result.success:
                        logger.info(
                            f"Webhook sent successfully (status {result.status_code})"
                        )
                    else:
                        logger.error(f"Webhook failed: {result.error}")

                except Exception as e:
                    logger.error(f"Error sending webhook: {e}", exc_info=True)
            else:
                logger.debug("Webhook URL not configured, skipping webhook send")

        self.complete(
            ClosingNotes(
                candidate_questions=candidate_questions,
            )
        )
