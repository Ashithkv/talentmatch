export default function JobDescriptionInput({ value, onChange, disabled }) {
  return (
    <div className="card">
      <h2>2. Job Description</h2>
      <textarea
        className="job-textarea"
        placeholder="Paste the full job description here..."
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        rows={10}
      />
    </div>
  )
}
