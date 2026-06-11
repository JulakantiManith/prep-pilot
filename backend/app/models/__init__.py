"""Database models and data types for the AI Interview Coach backend."""

from app.models.answer import Answer, AnswerCreate, ConfidenceResult, SpeechMetrics
from app.models.analytics import (
    AnalyticsOverview,
    AnalyticsTrends,
    Resume,
    ResumeCreate,
    ScoreTrend,
)
from app.models.feedback import (
    FeedbackReport,
    PresentationScores,
    SessionFeedback,
    SessionFeedbackCreate,
)
from app.models.session import (
    Difficulty,
    InterviewType,
    Session,
    SessionCreate,
    SessionStatus,
    SessionType,
)
from app.models.user import Profile, ProfileUpdate, User, UserCreate

__all__ = [
    # Enums
    "SessionType",
    "InterviewType",
    "Difficulty",
    "SessionStatus",
    # User models
    "User",
    "UserCreate",
    "Profile",
    "ProfileUpdate",
    # Session models
    "Session",
    "SessionCreate",
    # Answer models
    "Answer",
    "AnswerCreate",
    "SpeechMetrics",
    "ConfidenceResult",
    # Feedback models
    "FeedbackReport",
    "PresentationScores",
    "SessionFeedback",
    "SessionFeedbackCreate",
    # Analytics models
    "AnalyticsOverview",
    "AnalyticsTrends",
    "ScoreTrend",
    "Resume",
    "ResumeCreate",
]
