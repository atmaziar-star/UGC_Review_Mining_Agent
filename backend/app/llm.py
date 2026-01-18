"""LLM integration for theme extraction and brief generation."""
import json
import re
from typing import Dict, List, Optional

from groq import Groq

from app.models import ReviewInput, ThemeMention, ThemeSummary, TrendWindow


# Groq uses very fast LPU (Language Processing Unit) for inference
GROQ_MODEL = "openai/gpt-oss-120b"  # Fast and high quality

# Initialize Groq client
def get_groq_client() -> Groq:
    """Get Groq client."""
    import os
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in environment variables")
    
    return Groq(api_key=api_key)


def extract_themes_from_chunk(reviews: List[ReviewInput], chunk_id: int) -> List[ThemeMention]:
    """Extract themes from a chunk of reviews using LLM.
    
    Args:
        reviews: List of reviews in this chunk
        chunk_id: Identifier for this chunk
        
    Returns:
        List of ThemeMention objects
    """
    client = get_groq_client()
    
    # Prepare review data for LLM - optimized to reduce token usage
    review_data = []
    for review in reviews:
        # Limit content to 800 chars - enough for theme extraction, reduces tokens significantly
        content = (review.review_content or "")[:800]
        # Skip very short reviews that likely won't have meaningful themes
        if len(content.strip()) < 20:
            continue
        review_data.append({
            "id": review.review_id or f"review_{chunk_id}_{len(review_data)}",
            "title": (review.review_title or "")[:100],  # Limit title too
            "content": content,
            "rating": review.rating
        })
    
    if not review_data:
        return []
    
    # Use compact JSON (no indentation) to reduce token usage
    reviews_json = json.dumps(review_data, separators=(',', ':'))
    
    prompt = f"""Analyze these product reviews and extract themes from each.

For each review, identify up to 3 themes. For each theme provide:
- Label (1-4 words, e.g., "ice retention", "durability")
- Polarity: "love" (positive) or "improve" (negative/complaints)
- Snippet: exact quote where theme is mentioned (50-150 chars)

Reviews:
{reviews_json}

Return a JSON array with this structure:
[
  {{
    "review_id": "string",
    "themes": [
      {{
        "theme_label": "string",
        "polarity": "love" or "improve",
        "snippet": "exact quote from review mentioning this theme"
      }}
    ]
  }}
]

IMPORTANT: Return ONLY valid JSON. No markdown, no explanations."""
    
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,  # Use cheaper model for theme extraction - faster and more cost-effective
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts themes from product reviews. Only Return valid JSON with no placeholder text."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=6000  # Increased for larger chunks - Groq supports 32k context
        )
        
        content = response.choices[0].message.content.strip()
        
        # Remove markdown code blocks if present
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        result = json.loads(content)
        
        # Convert to ThemeMention objects with actual snippets
        mentions = []
        review_idx = 0
        for item in result:
            review_id = item.get("review_id")
            themes = item.get("themes", [])
            
            # Match with original review
            review = reviews[review_idx] if review_idx < len(reviews) else None
            review_idx += 1
            
            if not review:
                continue
            
            title = review.review_title or ""
            full_content = review.review_content or ""
            
            for theme in themes:
                # Use the snippet provided by LLM if available, otherwise extract from content
                theme_label = theme.get("theme_label", "").lower().strip()
                llm_snippet = theme.get("snippet", "")
                
                # If LLM provided snippet, use it; otherwise find relevant portion
                if llm_snippet:
                    snippet = llm_snippet
                else:
                    # Fallback: extract snippet around theme label keywords
                    snippet = extract_snippet_for_theme(full_content, theme_label)
                
                mention = ThemeMention(
                    theme_label=theme_label,
                    polarity=theme.get("polarity", "love"),
                    review_id=review_id,
                    review_title=title,
                    review_snippet=snippet
                )
                mentions.append(mention)
        
        return mentions
    
    except json.JSONDecodeError as e:
        content_preview = content[:500] if 'content' in locals() else "N/A"
        print(f"JSON decode error in chunk {chunk_id}: {e}")
        print(f"Response content: {content_preview}")
        return []
    except Exception as e:
        print(f"Error extracting themes from chunk {chunk_id}: {e}")
        return []


def extract_snippet_for_theme(content: str, theme_label: str, snippet_length: int = 200) -> str:
    """Extract relevant snippet from content that mentions the theme.
    
    Args:
        content: Full review content
        theme_label: Theme label to search for
        snippet_length: Desired snippet length
        
    Returns:
        Relevant snippet from content
    """
    if not content or not theme_label:
        return (content or "")[:snippet_length]
    
    # Split theme label into keywords
    keywords = theme_label.lower().split()
    content_lower = content.lower()
    
    # Find first occurrence of any keyword
    best_pos = len(content)
    for keyword in keywords:
        pos = content_lower.find(keyword)
        if pos != -1 and pos < best_pos:
            best_pos = pos
    
    # Extract snippet centered around the match
    if best_pos < len(content):
        start = max(0, best_pos - snippet_length // 2)
        end = min(len(content), best_pos + snippet_length // 2)
        snippet = content[start:end]
        
        # Try to start at sentence boundary
        if start > 0:
            # Find last period/sentence end before start
            last_period = content.rfind('.', 0, start)
            if last_period > start - 100:  # Not too far back
                snippet = content[last_period + 1:end].strip()
        
        # Ensure we have enough context
        if len(snippet) < 50 and len(content) > snippet_length:
            return content[:snippet_length]
        
        return snippet[:snippet_length]
    
    # Fallback: return beginning of content
    return content[:snippet_length]


def normalize_theme_label(label: str) -> str:
    """Normalize theme labels for aggregation."""
    # Lowercase, strip punctuation, normalize whitespace
    normalized = re.sub(r'[^\w\s]', '', label.lower().strip())
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized


def aggregate_themes(mentions: List[ThemeMention], top_n: int = 3) -> Dict[str, List[ThemeSummary]]:
    """Aggregate theme mentions by label and polarity.
    
    Returns:
        Dict with "love" and "improve" keys, each containing top_n ThemeSummary objects
    """
    # Group by normalized label and polarity
    theme_groups: Dict[str, Dict[str, List[ThemeMention]]] = {}
    
    for mention in mentions:
        normalized_label = normalize_theme_label(mention.theme_label)
        if not normalized_label:
            continue
        
        if normalized_label not in theme_groups:
            theme_groups[normalized_label] = {"love": [], "improve": []}
        
        polarity = mention.polarity if mention.polarity in ["love", "improve"] else "love"
        theme_groups[normalized_label][polarity].append(mention)
    
    # Create summaries for each polarity
    love_themes = []
    improve_themes = []
    
    for label, groups in theme_groups.items():
        for polarity in ["love", "improve"]:
            mentions_list = groups[polarity]
            if not mentions_list:
                continue
            
            # Get unique quotes (up to 2)
            quotes = []
            seen_titles = set()
            for mention in mentions_list[:10]:  # Limit to avoid duplicates
                if mention.review_title and mention.review_title not in seen_titles:
                    quotes.append({
                        "title": mention.review_title or "",
                        "snippet": mention.review_snippet or ""
                    })
                    seen_titles.add(mention.review_title)
                    if len(quotes) >= 2:
                        break
            
            theme_summary = ThemeSummary(
                theme_label=label,
                count=len(mentions_list),
                polarity=polarity,
                quotes=quotes
            )
            
            if polarity == "love":
                love_themes.append(theme_summary)
            else:
                improve_themes.append(theme_summary)
    
    # Sort by count and return top_n
    love_themes.sort(key=lambda x: x.count, reverse=True)
    improve_themes.sort(key=lambda x: x.count, reverse=True)
    
    return {
        "love": love_themes[:top_n],
        "improve": improve_themes[:top_n]
    }


def generate_executive_brief(
    total_reviews: int,
    rating_distribution: Dict[str, int],
    sentiment_summary: str,
    top_loved_themes: List[ThemeSummary],
    top_improvement_themes: List[ThemeSummary],
    trends: TrendWindow
) -> str:
    """Generate executive brief using LLM."""
    client = get_groq_client()
    
    stats_summary = {
        "total_reviews": total_reviews,
        "rating_distribution": rating_distribution,
        "sentiment": sentiment_summary,
        "top_loved_themes": [
            {"theme": t.theme_label, "count": t.count}
            for t in top_loved_themes
        ],
        "top_improvement_themes": [
            {"theme": t.theme_label, "count": t.count}
            for t in top_improvement_themes
        ],
        "recent_trends": {
            "window_days": trends.window_days,
            "recent_reviews": trends.total_reviews,
            "recent_positive": trends.positive_count,
            "recent_negative": trends.negative_count
        }
    }
    
    prompt = f"""Based on the following product review analysis, write a concise executive brief (3-4 paragraphs) that includes:

1. Overall sentiment summary
2. Top 3 most loved aspects (with context)
3. Top 3 areas needing improvement (with context)
4. Recent trends (comparison of last {trends.window_days} days vs overall)
5. Actionable recommendations for:
   - Product improvements
   - Content/marketing ideas

Analysis Data:
{json.dumps(stats_summary, separators=(',', ':'))}

Write in a professional, actionable tone. Be specific and data-driven.
Keep in mind that this will be directly input into a webpage, so ensure regular text formatting and avoid markdown."""
    
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are a business analyst writing executive summaries based on product review data."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=2000  # Groq supports larger outputs
        )
        
        brief = response.choices[0].message.content.strip()
        return brief
    
    except Exception as e:
        print(f"Error generating executive brief: {e}")
        # Fallback brief
        return f"""Executive Summary:

Overall sentiment is {sentiment_summary}. Based on {total_reviews} reviews, the product shows strong performance in {', '.join([t.theme_label for t in top_loved_themes[:3]])}.

Key strengths include {top_loved_themes[0].theme_label if top_loved_themes else 'quality'} mentioned in {top_loved_themes[0].count if top_loved_themes else 0} reviews.

Areas for improvement include {', '.join([t.theme_label for t in top_improvement_themes[:3]]) if top_improvement_themes else 'general feedback'}.

Recent trends indicate {'improving' if trends.positive_count > trends.negative_count else 'declining'} sentiment in the last {trends.window_days} days.
"""
