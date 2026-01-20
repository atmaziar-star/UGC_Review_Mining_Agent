# UGC & Review Mining Agent

A full-stack web application for analyzing product reviews from CSV files, extracting insights, themes, and generating executive summaries using LLM-powered analysis.

## Features

- **CSV Upload & Analysis**: Upload Amazon-style review CSV files for processing
- **Theme Extraction**: Automatically identify top "loved" and "needs improvement" themes
- **Sentiment Analysis**: Calculate overall sentiment from rating distribution
- **Trend Analysis**: Compare recent reviews (last 60 days) vs overall performance
- **Executive Brief**: Generate actionable insights and recommendations
- **Continuous Mining Support**: Project-based structure for re-running analyses and future integrations

## Tech Stack

- **Frontend**: React + Vite + TypeScript + Tailwind CSS
- **Backend**: Python FastAPI
- **Database**: SQLite (MVP, designed to be swapped to Postgres)
- **LLM**: Groq API (GPT OSS models) - Fast inference with LPU technology
- **Deployment**: Render

## Project Structure

```
UGC_Review_Mining_Agent/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app entry point
│   │   ├── routes.py        # API endpoints
│   │   ├── llm.py           # LLM integration
│   │   ├── parsing.py       # CSV parsing & normalization
│   │   ├── models.py        # Data models
│   │   └── db.py            # Database setup
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── pages/           # React pages
│   │   ├── api/             # API client
│   │   └── ...
│   ├── package.json
│   └── vite.config.ts
├── render.yaml              # Render deployment config
└── README.md
```

## Local Development

### Prerequisites

- Python 3.11 or 3.12 (recommended - Python 3.13 may have compatibility issues)
- Node.js 18+
- Groq API Key (get one at https://console.groq.com)

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   # Create .env file and add your Groq API key
   echo "GROQ_API_KEY=your_groq_api_key_here" > .env
   echo "FRONTEND_ORIGIN=*" >> .env
   # Get your API key at https://console.groq.com
   ```

5. Initialize the database:
   ```bash
   python -m app.db
   ```

6. Run the backend server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

The backend will be available at `http://localhost:8000`

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Set up environment variables (optional):
   ```bash
   # Create .env.local if you need to override API URL
   echo "VITE_API_URL=http://localhost:8000" > .env.local
   ```

4. Run the development server:
   ```bash
   npm run dev
   ```

The frontend will be available at `http://localhost:5173`

## CSV Format

The application expects CSV files with the following columns (flexible mapping):

- Review Title
- Review Content
- Review Rating (e.g., "5.0 out of 5 stars")
- Review Date (e.g., "Reviewed in the United States on January 12, 2026")
- Review Badge (e.g., "Verified Purchase")
- Product URL
- Review ID (optional)
- Reviewer's Name (optional)

Extra columns are ignored. The parser attempts to map variations in column names automatically.

## API Endpoints

- `GET /api/health` - Health check
- `POST /api/analyze` - Upload CSV and start analysis (returns job_id)
- `GET /api/jobs/{job_id}` - Get analysis results (includes analysis_time_seconds)
- `POST /api/jobs/{job_id}/rerun` - Re-run analysis for existing job
- `GET /api/samples` - List available sample review files
- `GET /api/samples/{filename}` - Get a sample CSV file
- `GET /api/connectors` - List available connectors (placeholder)
- `POST /api/connectors/oauth/mock` - Mock OAuth endpoint (placeholder)

## Deployment to Render

See `commands and deployment steps.md` (excluded from git) for detailed step-by-step deployment instructions.

**Quick Overview:**
1. Deploy **Backend Service** first (Python web service)
   - Set `GROQ_API_KEY` and `FRONTEND_ORIGIN` environment variables
   - Root Directory: `backend`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
2. Deploy **Frontend Service** (Node web service serving static files)
   - Set `VITE_API_URL` to your backend URL
   - Root Directory: `frontend`
   - Build Command: `npm install && npm run build`
   - Start Command: `cd frontend && npx serve -s dist -l $PORT`
3. Update backend `FRONTEND_ORIGIN` with your frontend URL

**Important**: See `commands and deployment steps.md` for complete manual setup instructions.

## GitHub Repository Setup

See `commands and deployment steps.md` for exact git commands to initialize and push to GitHub.

## Sample Data

A sample CSV file is included in `Sample_Review_Files/Amazon_Yeti_Cooler_reviews.csv` for testing.

## License

This project is part of a capstone assignment.
