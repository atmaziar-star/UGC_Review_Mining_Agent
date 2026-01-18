"""Data models and schemas."""
from datetime import date, datetime
from typing import Dict, List, Optional

from pydantic import BaseModel


class ReviewInput(BaseModel):
    """Parsed review from CSV."""
    review_id: Optional[str] = None
    reviewer_name: Optional[str] = None
    review_title: Optional[str] = None
    review_content: Optional[str] = None
    rating: int
    review_date: Optional[date] = None
    review_badge: Optional[str] = None
    product_url: Optional[str] = None


class ThemeMention(BaseModel):
    """Theme mention extracted from a review."""
    theme_label: str
    polarity: str  # "love" or "improve"
    review_id: Optional[str] = None
    review_title: Optional[str] = None
    review_snippet: Optional[str] = None


class ThemeSummary(BaseModel):
    """Aggregated theme summary."""
    theme_label: str
    count: int
    polarity: str  # "love" or "improve"
    quotes: List[Dict[str, str]]  # List of {title, snippet}


class RatingDistribution(BaseModel):
    """Rating distribution counts."""
    rating_1: int = 0
    rating_2: int = 0
    rating_3: int = 0
    rating_4: int = 0
    rating_5: int = 0


class TrendWindow(BaseModel):
    """Trend comparison for a time window."""
    window_days: int
    total_reviews: int
    positive_count: int
    negative_count: int
    neutral_count: int
    themes_improve: List[ThemeSummary] = []


class AnalysisResults(BaseModel):
    """Complete analysis results for a job."""
    job_id: str
    total_reviews: int
    rating_distribution: RatingDistribution
    sentiment_summary: str  # "positive", "neutral", "negative"
    positive_sentiment_pct: float
    top_loved_themes: List[ThemeSummary]
    top_improvement_themes: List[ThemeSummary]
    trends: TrendWindow
    executive_brief: str
    analysis_time_seconds: Optional[float] = None  # Time taken to complete analysis
    filename: Optional[str] = None  # Name of the processed file
    created_at: datetime
    updated_at: datetime


class JobStatus(BaseModel):
    """Job status response."""
    job_id: str
    status: str  # "pending", "processing", "completed", "error"
    created_at: datetime
    updated_at: datetime
    total_reviews: int = 0


class AnalyzeResponse(BaseModel):
    """Response from analyze endpoint."""
    job_id: str
    status: str
