import { useEffect, useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiClient, SampleFile } from '../api/client'

export default function HomePage() {
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [samples, setSamples] = useState<SampleFile[]>([])
  const [loadingSampleFilename, setLoadingSampleFilename] = useState<string | null>(null)
  const [uploadElapsedTime, setUploadElapsedTime] = useState(0)
  const [sampleElapsedTime, setSampleElapsedTime] = useState(0)
  const uploadIntervalRef = useRef<NodeJS.Timeout | null>(null)
  const sampleIntervalRef = useRef<NodeJS.Timeout | null>(null)
  const uploadStartTimeRef = useRef<number | null>(null)
  const sampleStartTimeRef = useRef<number | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    // Load sample files on mount
    const loadSamples = async () => {
      try {
        const response = await apiClient.getSampleFiles()
        setSamples(response.samples)
      } catch (err) {
        console.error('Failed to load sample files:', err)
      }
    }
    loadSamples()
  }, [])

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0]
    if (selectedFile) {
      if (selectedFile.type !== 'text/csv' && !selectedFile.name.endsWith('.csv')) {
        setError('Please select a CSV file')
        return
      }
      setFile(selectedFile)
      setError(null)
    }
  }

  const startUploadTimer = () => {
    uploadStartTimeRef.current = Date.now()
    setUploadElapsedTime(0)
    uploadIntervalRef.current = setInterval(() => {
      if (uploadStartTimeRef.current) {
        setUploadElapsedTime(Math.floor((Date.now() - uploadStartTimeRef.current) / 1000))
      }
    }, 1000)
  }

  const stopUploadTimer = () => {
    if (uploadIntervalRef.current) {
      clearInterval(uploadIntervalRef.current)
      uploadIntervalRef.current = null
    }
    uploadStartTimeRef.current = null
    setUploadElapsedTime(0)
  }

  const startSampleTimer = () => {
    sampleStartTimeRef.current = Date.now()
    setSampleElapsedTime(0)
    sampleIntervalRef.current = setInterval(() => {
      if (sampleStartTimeRef.current) {
        setSampleElapsedTime(Math.floor((Date.now() - sampleStartTimeRef.current) / 1000))
      }
    }, 1000)
  }

  const stopSampleTimer = () => {
    if (sampleIntervalRef.current) {
      clearInterval(sampleIntervalRef.current)
      sampleIntervalRef.current = null
    }
    sampleStartTimeRef.current = null
    setSampleElapsedTime(0)
    setLoadingSampleFilename(null)
  }

  useEffect(() => {
    return () => {
      if (uploadIntervalRef.current) {
        clearInterval(uploadIntervalRef.current)
      }
      if (sampleIntervalRef.current) {
        clearInterval(sampleIntervalRef.current)
      }
    }
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file) {
      setError('Please select a file')
      return
    }

    setUploading(true)
    setError(null)
    startUploadTimer()

    try {
      const response = await apiClient.analyzeFile(file)
      stopUploadTimer()
      navigate(`/results/${response.job_id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to upload file')
      setUploading(false)
      stopUploadTimer()
    }
  }

  const handleSampleReview = async (sample: SampleFile) => {
    setLoadingSampleFilename(sample.filename)
    setError(null)
    startSampleTimer()

    try {
      const sampleFile = await apiClient.loadSampleFile(sample.filename)
      const response = await apiClient.analyzeFile(sampleFile)
      stopSampleTimer()
      navigate(`/results/${response.job_id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load sample file')
      stopSampleTimer()
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-12 max-w-4xl">
        <div className="bg-white rounded-lg shadow-xl p-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            UGC & Review Mining Agent
          </h1>
          <p className="text-gray-600 mb-8">
            Upload a CSV file of product reviews to extract insights, themes, and sentiment analysis.
          </p>

          <form onSubmit={handleSubmit} className="mb-8">
            <div className="mb-6">
              <label htmlFor="file" className="block text-sm font-medium text-gray-700 mb-2">
                Upload CSV File
              </label>
              <input
                id="file"
                type="file"
                accept=".csv"
                onChange={handleFileChange}
                className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                disabled={uploading}
              />
            </div>

            {error && (
              <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-md">
                <p className="text-red-800 text-sm">{error}</p>
              </div>
            )}

            <button
              type="submit"
              disabled={!file || uploading || loadingSampleFilename !== null}
              className="w-full bg-blue-600 text-white py-3 px-6 rounded-md font-semibold hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              {uploading ? (
                <span className="flex items-center justify-center gap-2">
                  <span>Analyzing...</span>
                  <span className="text-blue-200">({uploadElapsedTime}s)</span>
                </span>
              ) : (
                'Analyze Reviews'
              )}
            </button>
          </form>

          {/* Sample Reviews Section */}
          {samples.length > 0 && (
            <div className="border-t pt-8 mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">Run with Sample Reviews</h2>
              <p className="text-gray-600 mb-4 text-sm">
                Try the analysis with pre-loaded sample review files
              </p>
              <div className="space-y-2">
                {samples.map((sample) => {
                  const isThisSampleLoading = loadingSampleFilename === sample.filename
                  return (
                    <button
                      key={sample.filename}
                      onClick={() => handleSampleReview(sample)}
                      disabled={uploading || loadingSampleFilename !== null}
                      className="w-full text-left p-4 bg-indigo-50 border border-indigo-200 rounded-md hover:bg-indigo-100 disabled:bg-gray-50 disabled:cursor-not-allowed transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-indigo-900">{sample.filename}</span>
                        <span className="text-sm text-indigo-600">
                          {isThisSampleLoading ? `Analyzing... (${sampleElapsedTime}s)` : '→ Run Analysis'}
                        </span>
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>
          )}

          {/* Future Data Sources Card */}
          <div className="border-t pt-8">
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">Future Data Sources</h2>
            <p className="text-gray-600 mb-4 text-sm">
              Connect external data sources for continuous mining (coming soon)
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {['X (Twitter)', 'Instagram', 'Facebook', 'YouTube', 'Shopify Reviews'].map((source) => (
                <button
                  key={source}
                  disabled
                  className="p-4 border-2 border-gray-200 rounded-md text-gray-500 bg-gray-50 cursor-not-allowed text-sm font-medium"
                >
                  Connect {source}
                  <span className="block text-xs text-gray-400 mt-1">Coming soon</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
