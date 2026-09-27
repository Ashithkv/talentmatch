import { useRef } from 'react'

export default function ResumeUpload({ fileName, onFileSelected, disabled }) {
  const inputRef = useRef(null)

  const handleChange = (e) => {
    const file = e.target.files?.[0]
    if (file) onFileSelected(file)
  }

  return (
    <div className="card">
      <h2>1. Upload Resume</h2>
      <div
        className="dropzone"
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
      >
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          onChange={handleChange}
          disabled={disabled}
          hidden
        />
        <p>{fileName ? `📄 ${fileName}` : 'Click to choose a PDF resume'}</p>
      </div>
    </div>
  )
}
