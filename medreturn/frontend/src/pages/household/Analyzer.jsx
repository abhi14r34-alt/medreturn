import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Card, DemoTag, ErrorNote, KV, PageHeader } from '../../components/ui.jsx'
import ImageCapture from '../../components/ImageCapture.jsx'
import { api } from '../../lib/api'

const MAX_MB = 5

export default function Analyzer() {
  const [preview, setPreview] = useState(null)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  const onFile = async (event) => {
    const file = event?.target ? event.target.files?.[0] : event
    if (!file) return

    setError(null)
    setResult(null)

    if (!file.type.startsWith('image/')) {
      setError(new Error('That file is not an image. Upload a JPG or PNG.'))
      return
    }
    if (file.size > MAX_MB * 1024 * 1024) {
      setError(new Error(`That image is over ${MAX_MB} MB. Try a smaller photo.`))
      return
    }

    setPreview(URL.createObjectURL(file))
    setBusy(true)
    try {
      setResult(await api.analyze(file))
    } catch (err) {
      setError(err)
    } finally {
      setBusy(false)
    }
  }

  const eligible = result?.eligibility_status === 'ELIGIBLE'

  return (
    <>
      <PageHeader
        title="Medicine analyzer"
        subtitle="Photograph the pack. The model suggests a category and a confidence score; anything unclear is sent for human review."
      />

      <div className="split">
        <Card>
          <div className="between" style={{ marginBottom: 12 }}>
            <h3>Upload an image</h3>
            {result?.is_simulated && <DemoTag />}
          </div>
          <ImageCapture onCapture={onFile} onUpload={onFile} disabled={busy} />
          <p className="xs mut" style={{ marginTop: 10 }}>JPG or PNG, up to {MAX_MB} MB</p>
          {preview && <img className="preview-img" src={preview} alt="Selected medicine" />}
        </Card>

        <Card>
          <div className="between" style={{ marginBottom: 10 }}>
            <h3>Result</h3>
            {result?.is_simulated && <DemoTag />}
          </div>

          <ErrorNote error={error} />

          {busy && (
            <>
              <p className="mut sm">Preprocessing and analyzing…</p>
              <div className="bar"><i style={{ width: '45%' }} /></div>
            </>
          )}

          {!busy && !result && !error && (
            <p className="mut sm">Upload an image to see the analysis.</p>
          )}

          {result && (
            <>
              <KV label="Detected item">{result.detected_item}</KV>
              <KV label="Packaging category">{result.category}</KV>
              <KV label="Confidence">
                <span className="mono">{Math.round(result.confidence * 100)}%</span>
              </KV>
              <KV label="Threshold">
                <span className="mono">{Math.round(result.confidence_threshold * 100)}%</span>
              </KV>
              <KV label="Inference">
                <span className={`pill ${result.is_simulated ? 'p-amber' : 'p-green'}`}>
                  {result.inference_mode}
                </span>
              </KV>

              <div style={{ margin: '14px 0' }}>
                <div className="bar">
                  <i style={{
                    width: `${Math.round(result.confidence * 100)}%`,
                    background: eligible
                      ? 'linear-gradient(90deg,var(--blue),var(--teal))'
                      : 'linear-gradient(90deg,#8a5a12,var(--amber))',
                  }} />
                </div>
              </div>

              <p className="sm" style={{ color: eligible ? 'var(--green)' : 'var(--amber)' }}>
                {result.message}
              </p>

              <Link
                className={`btn ${eligible ? 'pri' : ''}`}
                style={{ width: '100%', marginTop: 8 }}
                to={`/app/request?return_id=${result.return_id}`}
              >
                Request pickup
              </Link>

              <p className="xs mut" style={{ margin: '12px 0 0' }}>{result.disclaimer}</p>
            </>
          )}
        </Card>
      </div>
    </>
  )
}
