const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface AnalyzeResponse {
  job_id: string;
  status: string;
}

export interface AnalysisResults {
  job_id: string;
  total_reviews: number;
  rating_distribution: {
    rating_1: number;
    rating_2: number;
    rating_3: number;
    rating_4: number;
    rating_5: number;
  };
  sentiment_summary: string;
  positive_sentiment_pct: number;
  top_loved_themes: ThemeSummary[];
  top_improvement_themes: ThemeSummary[];
  trends: TrendWindow;
  executive_brief: string;
  analysis_time_seconds?: number;
  filename?: string;
  created_at: string;
  updated_at: string;
}

export interface SampleFile {
  filename: string;
  path: string;
}


export interface ThemeSummary {
  theme_label: string;
  count: number;
  polarity: string;
  quotes: Array<{ title: string; snippet: string }>;
}

export interface TrendWindow {
  window_days: number;
  total_reviews: number;
  positive_count: number;
  negative_count: number;
  neutral_count: number;
  themes_improve: ThemeSummary[];
}

export const apiClient = {
  async analyzeFile(file: File): Promise<AnalyzeResponse> {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch(`${API_URL}/api/analyze`, {
      method: 'POST',
      body: formData,
    });
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || 'Failed to upload file');
    }
    
    return response.json();
  },
  
  async getJobResults(jobId: string): Promise<AnalysisResults> {
    const response = await fetch(`${API_URL}/api/jobs/${jobId}`);
    
    if (!response.ok) {
      if (response.status === 202) {
        // Still processing
        const data = await response.json();
        throw new Error(`Job ${data.status}`);
      }
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || 'Failed to fetch results');
    }
    
    return response.json();
  },
  
  async rerunAnalysis(jobId: string): Promise<{ job_id: string; status: string }> {
    const response = await fetch(`${API_URL}/api/jobs/${jobId}/rerun`, {
      method: 'POST',
    });
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || 'Failed to rerun analysis');
    }
    
    return response.json();
  },
  
  async getConnectors() {
    const response = await fetch(`${API_URL}/api/connectors`);
    return response.json();
  },
  
  async getSampleFiles(): Promise<{ samples: SampleFile[] }> {
    const response = await fetch(`${API_URL}/api/samples`);
    if (!response.ok) {
      throw new Error('Failed to fetch sample files');
    }
    return response.json();
  },
  
  async loadSampleFile(filename: string): Promise<File> {
    const response = await fetch(`${API_URL}/api/samples/${filename}`);
    if (!response.ok) {
      throw new Error('Failed to load sample file');
    }
    const blob = await response.blob();
    return new File([blob], filename, { type: 'text/csv' });
  },
};
