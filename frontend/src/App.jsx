import { useState } from 'react'
import ResumeUpload from './components/ResumeUpload'
import JobDescriptionInput from './components/JobDescriptionInput'
import MatchResults from './components/MatchResults'
import { uploadResume, runMatch } from './services/api'

export default function App() {
  const [fileName, setFileName] = useState('')
  const [resumeText, setResumeText] = useState('')
  const [resumePreview, setResumePreview] = useState(null)
  const [jobDescription, setJobDescription] = useState('')
  const [matchResult, setMatchResult] = useState(null)

  const [uploading, setUploading] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [error, setError] = useState('')

  const handleFileSelected = async (file) => {
    setError('')
    setFileName(file.name)
    setMatchResult(null)
    setUploading(true)
    try {
      const data = await uploadResume(file)
      setResumeText(data.resume_text)
      setResumePreview(data.resume)
    } catch (err) {
      setError(err.message)
      setResumeText('')
      setResumePreview(null)
    } finally {
      setUploading(false)
    }
  }

  const handleAnalyze = async () => {
    setError('')
    if (!resumeText) {
      setError('Please upload a resume first.')
      return
    }
    if (!jobDescription.trim()) {
      setError('Please paste a job description first.')
      return
    }
    setAnalyzing(true)
    setMatchResult(null)
    try {
      const result = await runMatch(resumeText, jobDescription)
      setMatchResult(result)
    } catch (err) {
      setError(err.message)
    } finally {
      setAnalyzing(false)
    }
  }

  const busy = uploading || analyzing

  return (
    <div className="app">
      <header className="app-header">
        <h1>TalentMatch</h1>
        <p>Resume-to-job matching with transparent, Python-calculated scoring.</p>
      </header>

      <div className="grid">
        <ResumeUpload fileName={fileName} onFileSelected={handleFileSelected} disabled={busy} />
        <JobDescriptionInput value={jobDescription} onChange={setJobDescription} disabled={busy} />
      </div>

      {resumePreview && (
        <div className="card preview-card">
          <h2>Extracted from resume</h2>
          <p>{resumePreview.name || 'Unknown name'} — {resumePreview.skills.length} skills detected, {resumePreview.experience_years} yrs experience</p>
        </div>
      )}

      <button className="analyze-btn" onClick={handleAnalyze} disabled={busy}>
        {analyzing ? 'Analyzing...' : uploading ? 'Reading resume...' : 'Analyze Match'}
      </button>

      {error && <div className="error-banner">{error}</div>}

      <MatchResults result={matchResult} />
    </div>
  )
}
