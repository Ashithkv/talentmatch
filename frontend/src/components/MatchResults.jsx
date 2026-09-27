function ScoreRing({ score }) {
  const color = score >= 75 ? '#22c55e' : score >= 50 ? '#eab308' : '#ef4444'
  return (
    <div className="score-ring" style={{ borderColor: color }}>
      <span style={{ color }}>{Math.round(score)}</span>
      <small>/ 100</small>
    </div>
  )
}

function SkillTags({ items, variant }) {
  if (!items || items.length === 0) return <span className="muted">None</span>
  return (
    <div className="tag-row">
      {items.map((s) => (
        <span key={s} className={`tag ${variant}`}>{s}</span>
      ))}
    </div>
  )
}

export default function MatchResults({ result }) {
  if (!result) return null
  const { resume, job, match } = result

  return (
    <div className="results">
      <div className="card summary-card">
        <h2>Candidate Summary</h2>
        <ul className="summary-list">
          <li><strong>Name:</strong> {resume.name || 'Not detected'}</li>
          <li><strong>Email:</strong> {resume.email || 'Not detected'}</li>
          <li><strong>Phone:</strong> {resume.phone || 'Not detected'}</li>
          <li><strong>Experience:</strong> {resume.experience_years} years</li>
          <li><strong>Education:</strong> {resume.education.join('; ') || 'Not detected'}</li>
        </ul>
        <SkillTags items={resume.skills} variant="neutral" />
      </div>

      <div className="card score-card">
        <h2>Match Score {job.job_title ? `— ${job.job_title}` : ''}</h2>
        <div className="score-row">
          <ScoreRing score={match.overall_score} />
          <div className="score-breakdown">
            <div>Skills (50%): <strong>{match.skills.skill_score.toFixed(1)}</strong></div>
            <div>Experience (25%): <strong>{match.experience.experience_score.toFixed(1)}</strong></div>
            <div>Title relevance (15%): <strong>{match.title.title_score.toFixed(1)}</strong></div>
            <div>Location (10%): <strong>{match.location.location_score.toFixed(1)}</strong></div>
          </div>
        </div>

        <p className="explanation">{match.explanation}</p>
      </div>

      <div className="card">
        <h2>Skills Comparison</h2>
        <p className="label">✅ Matched required</p>
        <SkillTags items={match.skills.matched_required} variant="good" />
        <p className="label">❌ Missing required</p>
        <SkillTags items={match.skills.missing_required} variant="bad" />
        <p className="label">➕ Matched preferred</p>
        <SkillTags items={match.skills.matched_preferred} variant="good" />
      </div>

      <div className="card two-col">
        <div>
          <h2>Experience</h2>
          <p>Candidate: <strong>{match.experience.candidate_years} yrs</strong></p>
          <p>Required: <strong>{match.experience.required_years} yrs</strong></p>
          <p>{match.experience.meets_requirement ? '✅ Meets requirement' : '⚠️ Below requirement'}</p>
        </div>
        <div>
          <h2>Location</h2>
          <p>Candidate signal: <strong>{match.location.candidate_location || 'Not found'}</strong></p>
          <p>Job location: <strong>{match.location.job_location || 'Not specified'}</strong></p>
          <p>{match.location.matches ? '✅ Match' : '⚠️ No match found'}</p>
        </div>
      </div>
    </div>
  )
}
