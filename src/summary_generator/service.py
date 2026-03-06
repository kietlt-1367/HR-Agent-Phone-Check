import json
import logging
from typing import Any

import aiohttp

from models.models import (
    AdditionalInfo,
    CandidateScoring,
    ClosingNotes,
    FitAssessment,
    InterviewSummary,
    PersonalInfo,
    WorkExperience,
)

logger = logging.getLogger(__name__)


async def generate_summary_and_scoring(
    gemini_api_key: str,
    gemini_model: str,
    personal_info: PersonalInfo | None,
    work_experience: WorkExperience | None,
    fit_assessment: FitAssessment | None,
    additional_info: AdditionalInfo | None,
    closing_notes: ClosingNotes | None,
) -> tuple[InterviewSummary, CandidateScoring]:
    """
    Generate interview summary and candidate scoring using LLM.

    Args:
        gemini_api_key: Gemini API key
        gemini_model: Gemini model id (e.g. gemini-2.0-flash)
        personal_info: Candidate personal information
        work_experience: Candidate work experience
        fit_assessment: Fit assessment results
        additional_info: Additional candidate info
        closing_notes: Candidate questions and closing remarks

    Returns:
        Tuple of (InterviewSummary, CandidateScoring)
    """

    # Prepare interview data for LLM analysis
    interview_data = {
        "personal": {
            "full_name": personal_info.full_name if personal_info else "Unknown",
            "applied_position": personal_info.applied_position
            if personal_info
            else "Unknown",
        },
        "experience": {
            "company": work_experience.company if work_experience else None,
            "title": work_experience.title if work_experience else None,
            "duration": work_experience.duration if work_experience else None,
        },
        "fit_assessment": {
            "skills": fit_assessment.relevant_skills if fit_assessment else None,
            "reason_for_leaving": fit_assessment.reason_for_leaving
            if fit_assessment
            else None,
            "expected_salary": fit_assessment.expected_salary
            if fit_assessment
            else None,
        },
        "availability": {
            "available": additional_info.availability if additional_info else None,
            "start_date": additional_info.start_date if additional_info else None,
        },
        "candidate_questions": closing_notes.candidate_questions
        if closing_notes
        else [],
    }

    if not gemini_api_key:
        logger.warning(
            "GEMINI_API_KEY is not configured. Returning fallback summary/scoring."
        )
        return (
            InterviewSummary(
                strengths=["Chưa cấu hình GEMINI_API_KEY nên chưa thể sinh summary."],
                concerns=["Thiếu cấu hình AI provider bên ngoài."],
                recommendation="maybe",
                summary_text="Không thể sinh tóm tắt do thiếu cấu hình Gemini.",
            ),
            CandidateScoring(
                communication_score=5,
                experience_fit_score=5,
                salary_alignment_score=5,
                overall_score=5,
                communication_feedback="Chưa cấu hình Gemini.",
                experience_fit_feedback="Chưa cấu hình Gemini.",
                salary_alignment_feedback="Chưa cấu hình Gemini.",
            ),
        )

    # Generate summary
    summary_prompt = f"""Based on the following interview data, generate a professional summary evaluation:

Interview Data:
{json.dumps(interview_data, indent=2, ensure_ascii=False)}

Please provide:
1. List of 3-5 key strengths (in Vietnamese)
2. List of 2-4 concerns or red flags (in Vietnamese)
3. Recommendation: "proceed" (strong fit), "maybe" (acceptable but with concerns), or "pass" (not recommended)
4. A concise free-form summary (2-3 sentences in Vietnamese)

Format your response as JSON with keys: strengths, concerns, recommendation, summary_text
"""

    summary_text = await _call_gemini_text(
        api_key=gemini_api_key,
        model=gemini_model,
        prompt=summary_prompt,
        temperature=0.5,
    )

    try:
        summary_text = summary_text.strip()
        # Extract JSON from response
        if "```json" in summary_text:
            summary_text = summary_text.split("```json")[1].split("```")[0].strip()
        elif "```" in summary_text:
            summary_text = summary_text.split("```")[1].split("```")[0].strip()

        summary_data = json.loads(summary_text)
        summary = InterviewSummary(
            strengths=summary_data.get("strengths", []),
            concerns=summary_data.get("concerns", []),
            recommendation=summary_data.get("recommendation", "maybe"),
            summary_text=summary_data.get("summary_text", ""),
        )
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Error parsing summary response: {e}")
        summary = InterviewSummary(
            strengths=["Unable to generate summary"],
            concerns=[],
            recommendation="maybe",
            summary_text="",
        )

    # Generate scoring
    scoring_prompt = f"""Based on the following interview data, score the candidate on a scale of 1-10 for each criterion:

Interview Data:
{json.dumps(interview_data, indent=2, ensure_ascii=False)}

Score and provide feedback for:
1. Communication (clarity, professionalism, engagement): 1-10
2. Experience Fit (relevant skills, industry experience, growth trajectory): 1-10
3. Salary Alignment (salary expectations vs market rate for position): 1-10

Calculate overall_score as the average of the three scores.

Format your response as JSON with keys: communication_score, communication_feedback, experience_fit_score, experience_fit_feedback, salary_alignment_score, salary_alignment_feedback, overall_score
All feedback should be in Vietnamese.
"""

    scoring_text = await _call_gemini_text(
        api_key=gemini_api_key,
        model=gemini_model,
        prompt=scoring_prompt,
        temperature=0.1,
    )

    try:
        scoring_text = scoring_text.strip()
        # Extract JSON from response
        if "```json" in scoring_text:
            scoring_text = scoring_text.split("```json")[1].split("```")[0].strip()
        elif "```" in scoring_text:
            scoring_text = scoring_text.split("```")[1].split("```")[0].strip()

        scoring_data = json.loads(scoring_text)
        scoring = CandidateScoring(
            communication_score=float(scoring_data.get("communication_score", 5)),
            experience_fit_score=float(scoring_data.get("experience_fit_score", 5)),
            salary_alignment_score=float(scoring_data.get("salary_alignment_score", 5)),
            overall_score=float(scoring_data.get("overall_score", 5)),
            communication_feedback=scoring_data.get("communication_feedback", ""),
            experience_fit_feedback=scoring_data.get("experience_fit_feedback", ""),
            salary_alignment_feedback=scoring_data.get("salary_alignment_feedback", ""),
        )
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.error(f"Error parsing scoring response: {e}")
        scoring = CandidateScoring(
            communication_score=5,
            experience_fit_score=5,
            salary_alignment_score=5,
            overall_score=5,
            communication_feedback="Unable to generate feedback",
            experience_fit_feedback="",
            salary_alignment_feedback="",
        )

    return summary, scoring


def _extract_json_text(raw_text: str) -> str:
    text = raw_text.strip()
    if "```json" in text:
        return text.split("```json", 1)[1].split("```", 1)[0].strip()
    if "```" in text:
        return text.split("```", 1)[1].split("```", 1)[0].strip()
    return text


async def _call_gemini_text(
    api_key: str,
    model: str,
    prompt: str,
    temperature: float = 0.5,
) -> str:
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )
    payload: dict[str, Any] = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "responseMimeType": "application/json",
        },
    }

    timeout = aiohttp.ClientTimeout(total=40)
    async with aiohttp.ClientSession(timeout=timeout) as session, session.post(
        url, json=payload
    ) as resp:
        body = await resp.text()
        if resp.status != 200:
            raise RuntimeError(f"Gemini API error {resp.status}: {body[:300]}")

        data = json.loads(body)
        candidates = data.get("candidates", [])
        if not candidates:
            raise RuntimeError("Gemini response missing candidates")

        parts = candidates[0].get("content", {}).get("parts", [])
        text_chunks = [p.get("text", "") for p in parts if p.get("text")]
        if not text_chunks:
            raise RuntimeError("Gemini response missing text parts")
        return _extract_json_text("\n".join(text_chunks))
