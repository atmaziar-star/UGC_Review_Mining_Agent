"""CSV parsing and data normalization."""
import csv
import io
import re
from datetime import date, datetime
from typing import Dict, List, Optional

from app.models import ReviewInput


def parse_rating(rating_str: Optional[str]) -> int:
    """Parse rating string to integer (1-5).
    
    Examples:
        "5.0 out of 5 stars" -> 5
        "4 out of 5 stars" -> 4
        "3.0" -> 3
    """
    if not rating_str:
        return 3  # Default neutral
    
    # Extract first number
    match = re.search(r'(\d+)', str(rating_str))
    if match:
        rating = int(match.group(1))
        return max(1, min(5, rating))  # Clamp to 1-5
    return 3


def parse_date(date_str: Optional[str]) -> Optional[date]:
    """Parse date string to date object.
    
    Examples:
        "Reviewed in the United States on January 12, 2026" -> date(2026, 1, 12)
    """
    if not date_str:
        return None
    
    # Extract date part after "on"
    match = re.search(r'on\s+([A-Za-z]+\s+\d+,\s+\d+)', str(date_str))
    if match:
        date_part = match.group(1)
        try:
            return datetime.strptime(date_part, "%B %d, %Y").date()
        except ValueError:
            try:
                return datetime.strptime(date_part, "%b %d, %Y").date()
            except ValueError:
                pass
    
    return None


def normalize_column_name(col_name: str) -> str:
    """Normalize column names for flexible matching."""
    col_lower = col_name.lower().strip()
    # Map variations
    mapping = {
        "review title": "review_title",
        "review content": "review_content",
        "review rating": "review_rating",
        "review date": "review_date",
        "review badge": "review_badge",
        "reviewer's name": "reviewer_name",
        "reviewer name": "reviewer_name",
        "product url": "product_url",
        "review id": "review_id",
    }
    return mapping.get(col_lower, col_lower.replace(" ", "_").replace("'", ""))


def clean_text(text: Optional[str], max_length: int = 5000) -> Optional[str]:
    """Clean and truncate review text."""
    if not text:
        return None
    text = str(text).strip()
    if len(text) > max_length:
        text = text[:max_length] + "..."
    return text


def parse_csv(file_content: bytes, max_rows: int = 10000) -> List[ReviewInput]:
    """Parse CSV file content into ReviewInput objects.
    
    Args:
        file_content: Raw CSV file bytes
        max_rows: Maximum number of rows to process
        
    Returns:
        List of ReviewInput objects
        
    Raises:
        ValueError: If CSV is malformed or exceeds limits
    """
    try:
        text_content = file_content.decode('utf-8')
    except UnicodeDecodeError:
        # Try with common encodings
        for encoding in ['latin-1', 'iso-8859-1', 'cp1252']:
            try:
                text_content = file_content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise ValueError("Could not decode CSV file. Please ensure it's UTF-8 encoded.")
    
    reader = csv.DictReader(io.StringIO(text_content))
    
    # Normalize column names
    normalized_columns = {col: normalize_column_name(col) for col in reader.fieldnames or []}
    
    reviews = []
    row_count = 0
    
    for row in reader:
        if row_count >= max_rows:
            raise ValueError(f"CSV exceeds maximum row limit of {max_rows}")
        
        # Map to normalized column names
        normalized_row = {normalized_columns.get(k, k): v for k, v in row.items()}
        
        # Extract fields with fallbacks
        rating_str = normalized_row.get("review_rating") or normalized_row.get("rating")
        date_str = normalized_row.get("review_date") or normalized_row.get("date")
        review_content = normalized_row.get("review_content") or normalized_row.get("content")
        review_title = normalized_row.get("review_title") or normalized_row.get("title")
        reviewer_name = normalized_row.get("reviewer_name") or normalized_row.get("reviewer")
        
        rating = parse_rating(rating_str)
        review_date = parse_date(date_str)
        
        review = ReviewInput(
            review_id=normalized_row.get("review_id"),
            reviewer_name=reviewer_name,
            review_title=clean_text(review_title, 500),
            review_content=clean_text(review_content),
            rating=rating,
            review_date=review_date,
            review_badge=normalized_row.get("review_badge"),
            product_url=normalized_row.get("product_url")
        )
        
        reviews.append(review)
        row_count += 1
    
    if not reviews:
        raise ValueError("CSV file appears to be empty or contains no valid reviews")
    
    return reviews
