const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

async function handleResponse(res) {
  if (!res.ok) {
    let detail = `Request failed with status ${res.status}`
    try {
      const body = await res.json()
      if (body.detail) {
        detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
      }
    } catch {
      // response wasn't JSON - keep the generic message
    }
    throw new Error(detail)
  }
  return res.json()
}

export async function uploadResume(file) {
  const formData = new FormData()
  formData.append('file', file)

  const res = await fetch(`${API_BASE}/resume/upload`, {
    method: 'POST',
    body: formData,
  })
  return handleResponse(res)
}

export async function runMatch(resumeText, jobDescription) {
  const res = await fetch(`${API_BASE}/match`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ resume_text: resumeText, job_description: jobDescription }),
  })
  return handleResponse(res)
}
