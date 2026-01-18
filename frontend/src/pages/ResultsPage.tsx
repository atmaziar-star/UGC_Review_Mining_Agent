import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { apiClient, AnalysisResults } from '../api/client'

export default function ResultsPage() {
  const { jobId } = useParams<{ jobId: string }>()
  const navigate = useNavigate()
  const [results, setResults] = useState<AnalysisResults | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [rerunning, setRerunning] = useState(false)

  useEffect(() => {
    if (!jobId) {
      navigate('/')
      return
    }

    const fetchResults = async () => {
      try {
        const data = await apiClient.getJobResults(jobId)
        setResults(data)
        setLoading(false)
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Unknown error'
        if (message.includes('processing') || message.includes('pending')) {
          // Poll again after delay
          setTimeout(() => fetchResults(), 2000)
        } else {
          setError(message)
          setLoading(false)
        }
      }
    }

    fetchResults()
    const interval = setInterval(fetchResults, 3000) // Poll every 3 seconds

    return () => clearInterval(interval)
  }, [jobId, navigate])

  const handleCopyBrief = () => {
    if (results?.executive_brief) {
      navigator.clipboard.writeText(results.executive_brief)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const handleDownloadJSON = () => {
    if (results) {
      const jsonStr = JSON.stringify(results, null, 2)
      const blob = new Blob([jsonStr], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `analysis-${jobId}.json`
      a.click()
      URL.revokeObjectURL(url)
    }
  }

  const handleRerun = async () => {
    if (!jobId) return
    setRerunning(true)
    try {
      await apiClient.rerunAnalysis(jobId)
      // Reload results
      setTimeout(() => window.location.reload(), 2000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to rerun analysis')
      setRerunning(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Processing your reviews...</p>
        </div>
      </div>
    )
  }

  if (error && !results) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="bg-white rounded-lg shadow-xl p-8 max-w-md">
          <h2 className="text-2xl font-bold text-red-600 mb-4">Error</h2>
          <p className="text-gray-700 mb-6">{error}</p>
          <button
            onClick={() => navigate('/')}
            className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700"
          >
            Back to Home
          </button>
        </div>
      </div>
    )
  }

  if (!results) return null

  const ratingData = [
    { label: '5 Stars', value: results.rating_distribution.rating_5, color: 'bg-green-500' },
    { label: '4 Stars', value: results.rating_distribution.rating_4, color: 'bg-blue-500' },
    { label: '3 Stars', value: results.rating_distribution.rating_3, color: 'bg-yellow-500' },
    { label: '2 Stars', value: results.rating_distribution.rating_2, color: 'bg-orange-500' },
    { label: '1 Star', value: results.rating_distribution.rating_1, color: 'bg-red-500' },
  ]
  const maxRating = Math.max(...ratingData.map(d => d.value))

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-8">
      <div className="container mx-auto px-4 max-w-6xl">
        <div className="mb-6">
          <button
            onClick={() => navigate('/')}
            className="text-blue-600 hover:text-blue-800 font-medium mb-4"
          >
            ← Back to Home
          </button>
        </div>

        {/* Header */}
        <div className="bg-white rounded-lg shadow-xl p-6 mb-6">
          {results.filename && (
            <h2 className="text-lg font-medium text-gray-700 mb-3">
              Review Sentiment Analysis of: <span className="font-semibold text-gray-900">{results.filename}</span>
            </h2>
          )}
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Analysis Results</h1>
          <div className="flex items-center gap-4 text-sm text-gray-600 flex-wrap">
            <span>Total Reviews: {results.total_reviews}</span>
            <span>•</span>
            <span>Sentiment: <span className={`font-semibold capitalize ${
              results.sentiment_summary === 'positive' ? 'text-green-600' :
              results.sentiment_summary === 'negative' ? 'text-red-600' : 'text-yellow-600'
            }`}>{results.sentiment_summary}</span></span>
            <span>•</span>
            <span>Positive: {results.positive_sentiment_pct.toFixed(1)}%</span>
            {results.analysis_time_seconds && (
              <>
                <span>•</span>
                <span className="font-semibold text-blue-600">
                  ⏱️ Analysis Time: {results.analysis_time_seconds.toFixed(1)}s
                </span>
              </>
            )}
          </div>
        </div>

        {/* Rating Distribution */}
        <div className="bg-white rounded-lg shadow-xl p-6 mb-6">
          <h2 className="text-2xl font-semibold text-gray-900 mb-4">Rating Distribution</h2>
          <div className="space-y-3">
            {ratingData.map((item) => (
              <div key={item.label}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-700">{item.label}</span>
                  <span className="text-gray-900 font-medium">{item.value}</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-4">
                  <div
                    className={`${item.color} h-4 rounded-full transition-all`}
                    style={{ width: `${maxRating > 0 ? (item.value / maxRating) * 100 : 0}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* Top Loved Themes */}
          <div className="bg-white rounded-lg shadow-xl p-6">
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">Top Loved Themes</h2>
            {results.top_loved_themes.length === 0 ? (
              <p className="text-gray-500 text-sm">No themes identified</p>
            ) : (
              <div className="space-y-4">
                {results.top_loved_themes.map((theme, idx) => (
                  <div key={idx} className="border-l-4 border-green-500 pl-4">
                    <h3 className="font-semibold text-gray-900 mb-1">{theme.theme_label}</h3>
                    <p className="text-sm text-gray-600 mb-2">Mentioned in {theme.count} reviews</p>
                    {theme.quotes.length > 0 && (
                      <div className="space-y-2">
                        {theme.quotes.map((quote, qIdx) => (
                          <div key={qIdx} className="bg-green-50 p-3 rounded text-sm">
                            <p className="font-medium text-gray-900">{quote.title}</p>
                            <p className="text-gray-700 mt-1">{quote.snippet}</p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Top Improvement Themes */}
          <div className="bg-white rounded-lg shadow-xl p-6">
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">Needs Improvement</h2>
            {results.top_improvement_themes.length === 0 ? (
              <p className="text-gray-500 text-sm">No improvement themes identified</p>
            ) : (
              <div className="space-y-4">
                {results.top_improvement_themes.map((theme, idx) => (
                  <div key={idx} className="border-l-4 border-red-500 pl-4">
                    <h3 className="font-semibold text-gray-900 mb-1">{theme.theme_label}</h3>
                    <p className="text-sm text-gray-600 mb-2">Mentioned in {theme.count} reviews</p>
                    {theme.quotes.length > 0 && (
                      <div className="space-y-2">
                        {theme.quotes.map((quote, qIdx) => (
                          <div key={qIdx} className="bg-red-50 p-3 rounded text-sm">
                            <p className="font-medium text-gray-900">{quote.title}</p>
                            <p className="text-gray-700 mt-1">{quote.snippet}</p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Recent Trends */}
        <div className="bg-white rounded-lg shadow-xl p-6 mb-6">
          <h2 className="text-2xl font-semibold text-gray-900 mb-4">Recent Trends</h2>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Period</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Total Reviews</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Positive</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Neutral</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Negative</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                <tr>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">Last {results.trends.window_days} days</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{results.trends.total_reviews}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-green-600">{results.trends.positive_count}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-yellow-600">{results.trends.neutral_count}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-red-600">{results.trends.negative_count}</td>
                </tr>
                <tr>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">Overall</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{results.total_reviews}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-green-600">
                    {results.rating_distribution.rating_4 + results.rating_distribution.rating_5}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-yellow-600">{results.rating_distribution.rating_3}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-red-600">
                    {results.rating_distribution.rating_1 + results.rating_distribution.rating_2}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* Executive Brief */}
        <div className="bg-white rounded-lg shadow-xl p-6 mb-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-2xl font-semibold text-gray-900">Executive Brief</h2>
            <button
              onClick={handleCopyBrief}
              className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700"
            >
              {copied ? 'Copied!' : 'Copy to Clipboard'}
            </button>
          </div>
          <div className="prose max-w-none">
            <p className="text-gray-700 whitespace-pre-line">{results.executive_brief}</p>
          </div>
        </div>

        {/* Actions */}
        <div className="bg-white rounded-lg shadow-xl p-6">
          <div className="flex gap-4">
            <button
              onClick={handleRerun}
              disabled={rerunning}
              className="px-6 py-2 bg-gray-600 text-white rounded-md font-medium hover:bg-gray-700 disabled:bg-gray-400"
            >
              {rerunning ? 'Rerunning...' : 'Re-run Analysis'}
            </button>
            <button
              onClick={handleDownloadJSON}
              className="px-6 py-2 bg-green-600 text-white rounded-md font-medium hover:bg-green-700"
            >
              Download JSON
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
