import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Card, DemoTag, ErrorNote, KV, PageHeader } from '../../components/ui.jsx'
import ImageCapture from '../../components/ImageCapture.jsx'
import { api } from '../../lib/api'

const INLETS = ['Ward 3 Inlet', 'OT Block Inlet', 'Lab Inlet', 'ICU Inlet']

export default function WasteAnalyzer() {
  const [location, setLocation] = useState(INLETS[0])
  const [weight, setWeight] = useState(1.2)
  const [details, setDetails] = useState({ item_name: '', expiry_date: '', batch_number: '' })
  const [preview, setPreview] = useState(null)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  const onFile = async (event) => {
    const file = event?.target ? event.target.files?.[0] : event
    if (!file) return
    setError(null)
    setResult(null)

    const isImg = (file.type && file.type.startsWith('image/')) || /\.(jpe?g|png|webp|gif|bmp)$/i.test(file.name || '')
    if (!isImg) {
      setError(new Error('That file is not an image. Upload a JPG or PNG.'))
      return
    }

    setPreview(URL.createObjectURL(file))
    setBusy(true)
    try {
      setResult(await api.predictWaste(file, Number(weight), location, details))
    } catch (err) {
      setError(err)
    } finally {
      setBusy(false)
    }
  }

  const accepted = result?.decision === 'ACCEPTED'

  return (
    <>
      <PageHeader
        title="AI waste analyzer"
        subtitle="Image → preprocessing → model → confidence → decision engine → route or quarantine → log."
      />
      <div className="split">
        <Card>
          <div className="between" style={{ marginBottom: 12 }}>
            <h3>Capture or upload</h3>
            {result?.is_simulated && <DemoTag />}
          </div>
          <div className="fld">
            <label htmlFor="loc">Inlet location</label>
            <select id="loc" value={location} onChange={(e) => setLocation(e.target.value)}>
              {INLETS.map((i) => <option key={i}>{i}</option>)}
            </select>
          </div>
          <div className="fld">
            <label htmlFor="wt">Measured weight (kg)</label>
            <input id="wt" type="number" step="0.05" value={weight}
                   onChange={(e) => setWeight(e.target.value)} />
          </div>
             <div className="manual-details">
               <h4>Enter details manually (optional)</h4>
               <label htmlFor="waste-name">Waste or medicine name</label>
               <input id="waste-name" value={details.item_name}
                 onChange={(e) => setDetails({ ...details, item_name: e.target.value })}
                 placeholder="e.g. used syringe or Dolo-650" disabled={busy} />
               <label htmlFor="waste-expiry">Expiry date</label>
               <input id="waste-expiry" value={details.expiry_date}
                 onChange={(e) => setDetails({ ...details, expiry_date: e.target.value })}
                 placeholder="Optional" disabled={busy} />
               <label htmlFor="waste-batch">Batch number</label>
               <input id="waste-batch" value={details.batch_number}
                 onChange={(e) => setDetails({ ...details, batch_number: e.target.value })}
                 placeholder="Optional" disabled={busy} />
             </div>
          <ImageCapture onCapture={onFile} onUpload={onFile} disabled={busy} />
          {preview && <img className="preview-img" src={preview} alt="Waste item" />}
        </Card>

        <Card>
          <div className="between" style={{ marginBottom: 10 }}>
            <h3>Decision</h3>
            {result?.is_simulated && <DemoTag />}
          </div>
          <ErrorNote error={error} />

          {busy && (
            <>
              <p className="mut sm">Preprocessing · 224×224 · normalising · running classifier…</p>
              <div className="bar"><i style={{ width: '55%' }} /></div>
            </>
          )}

          {!busy && !result && !error && (
            <p className="mut sm">Upload an image to run the pipeline.</p>
          )}

          {result && (
            <>
              <KV label="Event ID"><span className="mono">{result.event_id}</span></KV>
              <KV label="Predicted class">{result.predicted_class}</KV>
              <KV label="Text on item">
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
                    background: accepted ? 'var(--green)' : 'var(--amber)',
                  }} />
                </div>
              </div>

              <div style={{
                background: accepted ? 'rgba(61,214,140,.09)' : 'rgba(245,165,36,.09)',
                border: `1px solid ${accepted ? 'rgba(61,214,140,.3)' : 'rgba(245,165,36,.35)'}`,
                borderRadius: 10, padding: 14,
              }}>
                <div className="between">
                  <b>{accepted ? 'Accepted' : 'Quarantined'}</b>
                  <span className={`pill ${accepted ? 'p-green' : 'p-amber'}`}>{result.route}</span>
                </div>
                <p className="sm mut" style={{ margin: '8px 0 0' }}>
                  {accepted
                    ? 'Class is supported and confidence clears the gate. The controller opens the matching compartment.'
                    : `${result.reason}. The item is held for human verification and is not routed.`}
                </p>
              </div>

              {result.human_verification_required && (
                <div className="note" style={{ marginTop: 10 }}>
                  {result.model_quality?.reason || 'Human verification required. This item remains in quarantine until reviewed.'}
                </div>
              )}

              {result.hardware_simulated && (
                <div className="note" style={{ marginTop: 12 }}>
                  <b>Hardware simulation.</b> {result.hardware_detail}
                </div>
              )}

              <Link className="btn sm" style={{ marginTop: 12 }}
                    to={accepted ? '/hospital/traceability' : '/hospital/quarantine'}>
                {accepted ? 'View in traceability' : 'Open quarantine queue'}
              </Link>
            </>
          )}
        </Card>
      </div>
    </>
  )
}
