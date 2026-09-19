import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Card, DemoTag, ErrorNote, KV, PageHeader } from '../../components/ui.jsx'
import ImageCapture from '../../components/ImageCapture.jsx'
import { api } from '../../lib/api'

const MAX_MB = 5

export default function Analyzer() {
  const [preview, setPreview] = useState(null)
  const [details, setDetails] = useState({ item_name: '', expiry_date: '', batch_number: '' })
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  const [currentFile, setCurrentFile] = useState(null)

  const onFile = async (event, overrideDetails = null) => {
    const file = event?.target ? event.target.files?.[0] : (event instanceof File ? event : currentFile)
    if (!file) return

    setError(null)
    setResult(null)

    const isImg = (file.type && file.type.startsWith('image/')) || /\.(jpe?g|png|webp|gif|bmp)$/i.test(file.name || '')
    if (!isImg) {
      setError(new Error('That file is not an image. Upload a JPG or PNG.'))
      return
    }
    if (file.size > MAX_MB * 1024 * 1024) {
      setError(new Error(`That image is over ${MAX_MB} MB. Try a smaller photo.`))
      return
    }

    setCurrentFile(file)
    setPreview(URL.createObjectURL(file))
    setBusy(true)
    try {
      setResult(await api.analyze(file, overrideDetails || details))
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
        subtitle="Photograph the pack. The trained model returns one of its learned labels; anything unclear is sent for human review."
      />

      <div className="split">
        <Card>
          <div className="between" style={{ marginBottom: 12 }}>
            <h3>Upload an image</h3>
            {result?.is_simulated && <DemoTag />}
          </div>
          <ImageCapture onCapture={onFile} onUpload={onFile} disabled={busy} />
             <div className="manual-details">
               <h4>Enter details manually (optional)</h4>
               <label htmlFor="medicine-name">Medicine or item name</label>
               <input id="medicine-name" value={details.item_name}
                 onChange={(e) => setDetails({ ...details, item_name: e.target.value })}
                 placeholder="e.g. Dolo-650" disabled={busy} />
               <label htmlFor="medicine-expiry">Expiry date</label>
               <input id="medicine-expiry" value={details.expiry_date}
                 onChange={(e) => setDetails({ ...details, expiry_date: e.target.value })}
                 placeholder="e.g. DEC 2029 or 12/2029" disabled={busy} />
               <label htmlFor="medicine-batch">Batch number</label>
               <input id="medicine-batch" value={details.batch_number}
                 onChange={(e) => setDetails({ ...details, batch_number: e.target.value })}
                 placeholder="Optional" disabled={busy} />
               {currentFile && (
                 <button className="btn sm" type="button" style={{ marginTop: 8 }} onClick={() => onFile(currentFile)} disabled={busy}>
                   Update analysis with details
                 </button>
               )}
             </div>
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
              <KV label="Model label">{result.category}</KV>
              <KV label="Text on package">
                {result.ocr_text || <span className="mut">Not readable</span>}
              </KV>
              <KV label="Entered name">
                {result.item_name || <span className="mut">Not provided</span>}
              </KV>
              <KV label="Expiry date">
                {result.expiry_date || <span className="mut">Not detected</span>}
              </KV>
              <KV label="Batch number">
                {result.batch_number || <span className="mut">Not provided</span>}
              </KV>
              {result.ocr_text && (
                <p className="xs mut">Text recognized from packaging.</p>
              )}
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
              {result.human_verification_required && (
                <div className="note" style={{ marginTop: 10 }}>
                  {result.model_quality?.reason || 'Human verification required before this item is accepted.'}
                </div>
              )}

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
