"""API routes."""
import json
import time
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse, FileResponse

from app import db
from app.llm import aggregate_themes, extract_themes_from_chunk, generate_executive_brief
from app.models import AnalysisResults, AnalyzeResponse, JobStatus, RatingDistribution, ThemeSummary, TrendWindow
from app.parsing import parse_csv

router = APIRouter()

# Constants
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_ROWS = 10000
CHUNK_SIZE = 35  # Reviews per LLM batch (optimized for Groq's 32k context)


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@router.post("/analyze", response_model=AnalyzeResponse, status_code=status.HTTP_201_CREATED)
async def analyze_reviews(file: UploadFile = File(...)):
    """Upload and analyze CSV file of reviews.
    
    Returns job_id for polling results.
    """
    # Check file size
    file_content = await file.read()
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum of {MAX_FILE_SIZE / (1024*1024):.1f}MB"
        )
    
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    # Get filename
    filename = file.filename or "uploaded_file.csv"
    
    # Create job record
    conn = db.get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO jobs (id, status, total_reviews, filename) VALUES (?, ?, ?, ?)",
        (job_id, "pending", 0, filename)
    )
    conn.commit()
    
    try:
        # Parse CSV
        reviews = parse_csv(file_content, max_rows=MAX_ROWS)
        
        # Update job status
        cursor.execute(
            "UPDATE jobs SET status = ?, total_reviews = ? WHERE id = ?",
            ("processing", len(reviews), job_id)
        )
        conn.commit()
        
        # Store reviews in database
        for review in reviews:
            cursor.execute(
                """INSERT INTO reviews 
                   (job_id, review_id, reviewer_name, review_title, review_content, 
                    rating, review_date, review_badge, product_url)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    job_id,
                    review.review_id,
                    review.reviewer_name,
                    review.review_title,
                    review.review_content,
                    review.rating,
                    review.review_date.isoformat() if review.review_date else None,
                    review.review_badge,
                    review.product_url
                )
            )
        conn.commit()
        
        # Run analysis asynchronously (in production, use background tasks)
        # For MVP, run synchronously but return job_id immediately
        # In a real app, use FastAPI BackgroundTasks
        await process_analysis(job_id, reviews)
        
        return AnalyzeResponse(job_id=job_id, status="processing")
    
    except ValueError as e:
        # Update job status to error
        cursor.execute("UPDATE jobs SET status = ? WHERE id = ?", ("error", job_id))
        conn.commit()
        conn.close()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        cursor.execute("UPDATE jobs SET status = ? WHERE id = ?", ("error", job_id))
        conn.commit()
        conn.close()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Processing error: {str(e)}")
    finally:
        conn.close()


async def process_analysis(job_id: str, reviews: List):
    """Process analysis for a job."""
    start_time = time.time()
    try:
        # Calculate rating distribution
        rating_dist = RatingDistribution()
        for review in reviews:
            if review.rating == 1:
                rating_dist.rating_1 += 1
            elif review.rating == 2:
                rating_dist.rating_2 += 1
            elif review.rating == 3:
                rating_dist.rating_3 += 1
            elif review.rating == 4:
                rating_dist.rating_4 += 1
            elif review.rating == 5:
                rating_dist.rating_5 += 1
        
        # Calculate sentiment
        positive_count = rating_dist.rating_4 + rating_dist.rating_5
        negative_count = rating_dist.rating_1 + rating_dist.rating_2
        neutral_count = rating_dist.rating_3
        total = len(reviews)
        
        positive_pct = (positive_count / total * 100) if total > 0 else 0
        
        if positive_pct >= 60:
            sentiment = "positive"
        elif positive_pct >= 40:
            sentiment = "neutral"
        else:
            sentiment = "negative"
        
        # Extract themes in chunks
        all_mentions = []
        for i in range(0, len(reviews), CHUNK_SIZE):
            chunk = reviews[i:i + CHUNK_SIZE]
            chunk_id = i // CHUNK_SIZE
            mentions = extract_themes_from_chunk(chunk, chunk_id)
            all_mentions.extend(mentions)
        
        # Aggregate themes
        theme_aggregates = aggregate_themes(all_mentions, top_n=3)
        top_loved = theme_aggregates["love"]
        top_improve = theme_aggregates["improve"]
        
        # Calculate trends (last 60 days vs overall)
        now = date.today()
        sixty_days_ago = now - timedelta(days=60)
        
        recent_reviews = [r for r in reviews if r.review_date and r.review_date >= sixty_days_ago]
        recent_positive = sum(1 for r in recent_reviews if r.rating >= 4)
        recent_negative = sum(1 for r in recent_reviews if r.rating <= 2)
        recent_neutral = len(recent_reviews) - recent_positive - recent_negative
        
        trends = TrendWindow(
            window_days=60,
            total_reviews=len(recent_reviews),
            positive_count=recent_positive,
            negative_count=recent_negative,
            neutral_count=recent_neutral,
            themes_improve=top_improve
        )
        
        # Generate executive brief
        exec_brief = generate_executive_brief(
            total_reviews=total,
            rating_distribution=rating_dist.dict(),
            sentiment_summary=sentiment,
            top_loved_themes=top_loved,
            top_improvement_themes=top_improve,
            trends=trends
        )
        
        # Calculate analysis time
        analysis_time = time.time() - start_time
        
        # Get filename from job
        conn_check = db.get_db()
        cursor_check = conn_check.cursor()
        cursor_check.execute("SELECT filename FROM jobs WHERE id = ?", (job_id,))
        job_row = cursor_check.fetchone()
        filename = job_row["filename"] if job_row else None
        conn_check.close()
        
        # Build results object
        results = AnalysisResults(
            job_id=job_id,
            total_reviews=total,
            rating_distribution=rating_dist,
            sentiment_summary=sentiment,
            positive_sentiment_pct=positive_pct,
            top_loved_themes=top_loved,
            top_improvement_themes=top_improve,
            trends=trends,
            executive_brief=exec_brief,
            analysis_time_seconds=round(analysis_time, 2),
            filename=filename,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Store results
        conn = db.get_db()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT OR REPLACE INTO job_results (job_id, results_json, updated_at)
               VALUES (?, ?, ?)""",
            (job_id, results.model_dump_json(), datetime.now())
        )
        cursor.execute("UPDATE jobs SET status = ?, updated_at = ? WHERE id = ?", ("completed", datetime.now(), job_id))
        conn.commit()
        conn.close()
    
    except Exception as e:
        # Mark job as error
        conn = db.get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE jobs SET status = ? WHERE id = ?", ("error", job_id))
        conn.commit()
        conn.close()
        print(f"Error processing job {job_id}: {e}")
        raise


@router.get("/jobs/{job_id}", response_model=AnalysisResults)
async def get_job_results(job_id: str):
    """Get analysis results for a job."""
    conn = db.get_db()
    cursor = conn.cursor()
    
    # Check job status
    cursor.execute("SELECT status FROM jobs WHERE id = ?", (job_id,))
    job_row = cursor.fetchone()
    if not job_row:
        conn.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    
    job_status = job_row["status"]
    if job_status == "pending" or job_status == "processing":
        conn.close()
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={"job_id": job_id, "status": job_status}
        )
    
    if job_status == "error":
        conn.close()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Job processing failed")
    
    # Get results and filename from job
    cursor.execute("SELECT results_json FROM job_results WHERE job_id = ?", (job_id,))
    result_row = cursor.fetchone()
    
    if not result_row:
        conn.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Results not found")
    
    # Get filename from job if not in results
    cursor.execute("SELECT filename FROM jobs WHERE id = ?", (job_id,))
    job_row = cursor.fetchone()
    filename = job_row["filename"] if job_row else None
    conn.close()
    
    results_dict = json.loads(result_row["results_json"])
    # Ensure filename is included
    if filename and "filename" not in results_dict:
        results_dict["filename"] = filename
    
    return AnalysisResults(**results_dict)


@router.post("/jobs/{job_id}/rerun")
async def rerun_analysis(job_id: str):
    """Re-run analysis for an existing job."""
    conn = db.get_db()
    cursor = conn.cursor()
    
    # Check job exists
    cursor.execute("SELECT id FROM jobs WHERE id = ?", (job_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    
    # Get stored reviews
    cursor.execute(
        """SELECT review_id, reviewer_name, review_title, review_content, 
           rating, review_date, review_badge, product_url
           FROM reviews WHERE job_id = ?""",
        (job_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No reviews found for this job")
    
    # Convert rows back to ReviewInput objects
    from app.models import ReviewInput
    reviews = []
    for row in rows:
        review_date = None
        if row["review_date"]:
            review_date = datetime.fromisoformat(row["review_date"]).date()
        
        review = ReviewInput(
            review_id=row["review_id"],
            reviewer_name=row["reviewer_name"],
            review_title=row["review_title"],
            review_content=row["review_content"],
            rating=row["rating"],
            review_date=review_date,
            review_badge=row["review_badge"],
            product_url=row["product_url"]
        )
        reviews.append(review)
    
    # Update job status
    conn = db.get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE jobs SET status = ? WHERE id = ?", ("processing", job_id))
    conn.commit()
    conn.close()
    
    # Process analysis
    await process_analysis(job_id, reviews)
    
    return {"job_id": job_id, "status": "processing"}


@router.get("/connectors")
async def get_connectors():
    """Get list of available connectors (placeholder)."""
    return {
        "connectors": [
            {"id": "twitter", "name": "X (Twitter)", "status": "coming_soon"},
            {"id": "instagram", "name": "Instagram", "status": "coming_soon"},
            {"id": "facebook", "name": "Facebook", "status": "coming_soon"},
            {"id": "youtube", "name": "YouTube", "status": "coming_soon"},
            {"id": "shopify", "name": "Shopify Reviews", "status": "coming_soon"}
        ]
    }


@router.post("/connectors/oauth/mock")
async def mock_oauth():
    """Placeholder OAuth endpoint (not functional)."""
    return {"message": "OAuth integration coming soon", "status": "not_implemented"}


@router.get("/samples")
async def get_sample_files():
    """Get list of available sample review files."""
    samples_dir = Path(__file__).parent.parent.parent / "Sample_Review_Files"
    samples = []
    
    if samples_dir.exists():
        for file_path in samples_dir.glob("*.csv"):
            samples.append({
                "filename": file_path.name,
                "path": f"Sample_Review_Files/{file_path.name}"
            })
    
    return {"samples": samples}


@router.get("/samples/{filename}")
async def get_sample_file(filename: str):
    """Get a sample CSV file."""
    samples_dir = Path(__file__).parent.parent.parent / "Sample_Review_Files"
    file_path = samples_dir / filename
    
    # Security check - ensure file is within samples directory
    if not file_path.exists() or not str(file_path).startswith(str(samples_dir)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sample file not found")
    
    return FileResponse(
        path=file_path,
        media_type="text/csv",
        filename=filename
    )
