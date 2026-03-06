import asyncio
import logging
from datetime import datetime
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class WebhookResult:
    """Result of webhook delivery."""

    def __init__(
        self, success: bool, status_code: int | None = None, error: str | None = None
    ):
        self.success = success
        self.status_code = status_code
        self.error = error
        self.timestamp = datetime.utcnow().isoformat()


async def send_interview_webhook(
    webhook_url: str,
    interview_data: dict[str, Any],
    timeout_seconds: int = 30,
    retry_count: int = 3,
    retry_delay_seconds: float = 1.0,
) -> WebhookResult:
    """
    Send interview results to webhook URL with retry logic.

    Args:
        webhook_url: Target webhook URL
        interview_data: Interview result data to POST
        timeout_seconds: Request timeout
        retry_count: Number of retries on failure
        retry_delay_seconds: Delay between retries

    Returns:
        WebhookResult indicating success/failure
    """

    if not webhook_url:
        logger.warning("Webhook URL not configured, skipping webhook send")
        return WebhookResult(success=False, error="Webhook URL not configured")

    # Prepare payload
    payload = {
        "timestamp": datetime.utcnow().isoformat(),
        "interview": interview_data,
    }

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "LiveKit-HR-Agent/1.0",
    }

    last_error = None

    for attempt in range(retry_count):
        try:
            logger.info(
                f"Sending webhook (attempt {attempt + 1}/{retry_count}): {webhook_url}"
            )

            timeout = aiohttp.ClientTimeout(total=timeout_seconds)
            async with aiohttp.ClientSession(timeout=timeout) as session, session.post(
                webhook_url,
                json=payload,
                headers=headers,
            ) as response:
                response_text = await response.text()

                if response.status in (200, 201, 202, 204):
                    logger.info(
                        f"Webhook sent successfully (status {response.status})"
                    )
                    return WebhookResult(
                        success=True,
                        status_code=response.status,
                    )
                else:
                    last_error = f"HTTP {response.status}: {response_text[:200]}"
                    logger.warning(
                        f"Webhook failed with status {response.status}: {response_text[:200]}"
                    )

        except asyncio.TimeoutError:
            last_error = f"Request timeout after {timeout_seconds}s"
            logger.warning(f"Webhook timeout: {last_error}")

        except aiohttp.ClientError as e:
            last_error = f"Connection error: {e!s}"
            logger.warning(f"Webhook connection error: {last_error}")

        except Exception as e:
            last_error = f"Unexpected error: {e!s}"
            logger.error(f"Webhook error: {last_error}", exc_info=True)

        # Wait before retry
        if attempt < retry_count - 1:
            logger.info(f"Retrying in {retry_delay_seconds}s...")
            await asyncio.sleep(retry_delay_seconds)

    return WebhookResult(
        success=False,
        error=last_error or "Unknown error",
    )


def prepare_interview_payload(session_data: dict[str, Any]) -> dict[str, Any]:
    """
    Prepare interview data for webhook payload.

    Converts dataclass objects to dicts and cleans up for JSON serialization.

    Args:
        session_data: Interview session data

    Returns:
        Clean payload ready for JSON serialization
    """

    payload = {}

    # Session metadata
    payload["session_id"] = session_data.get("session_id", "")
    payload["room_name"] = session_data.get("room_name", "")
    payload["participant_id"] = session_data.get("participant_id", "")
    payload["started_at"] = session_data.get("started_at", "")
    payload["completed_at"] = session_data.get("completed_at", "")

    # Interview data
    payload["candidate"] = {
        "full_name": session_data.get("personal_info", {}).get("full_name", ""),
        "applied_position": session_data.get("personal_info", {}).get(
            "applied_position", ""
        ),
    }

    payload["experience"] = session_data.get("work_experience", {})
    payload["fit_assessment"] = session_data.get("fit_assessment", {})
    payload["availability"] = session_data.get("additional_info", {})
    payload["questions"] = session_data.get("closing_notes", {}).get(
        "candidate_questions", []
    )

    # Analysis results
    payload["summary"] = session_data.get("summary") or session_data.get(
        "interview_summary", {}
    )
    payload["scoring"] = session_data.get("scoring") or session_data.get(
        "candidate_scoring", {}
    )
    payload["analytics"] = session_data.get("analytics", {})

    return payload
