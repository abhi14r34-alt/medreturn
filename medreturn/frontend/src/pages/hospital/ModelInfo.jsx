import { useEffect, useState } from 'react'
import { Card, ErrorNote, KV, Loading, PageHeader } from '../../components/ui.jsx'
import { api } from '../../lib/api'
import { useAuth } from '../../lib/auth.jsx'
import { formatDate } from '../../lib/format'

const PIPELINE = [
  'Dataset', 'Cleaning', 'Train/val/test split', 'Preprocessing 224×224',
  'Augmentation', 'Transfer learning on MobileNetV3', 'Validation each epoch',
  'Best checkpoint selection', 'Test evaluation', 'Save model.pth',
]

const LEARNING_LOOP = [
  'AI prediction', 'Human verification', 'Verified dataset', 'Dataset version',
  'Retraining', 'New model version', 'Controlled deployment',
]

export default function ModelInfo() {
  const { user } = useAuth()
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetcher = user.role === 'admin' ? api.adminModel : api.hospitalModel
    fetcher().then(setData).catch(setError)
  }, [user.role])

  if (error) return <ErrorNote error={error} />
  if (!data) return <Loading />

  const { runtime, versions } = data
  const hasMetrics = versions.some((v) => v.accuracy != null)

  return (
    <>
      <PageHeader
        title="Model information"
        subtitle="What is deployed, how it was built, and what is still missing."
      />

      <div className="split">
        <Card>
          <div className="between" style={{ marginBottom: 12 }}>
            <h3>Runtime</h3>
            <span className={`pill ${runtime.mode === 'REAL' ? 'p-green' : 'p-amber'}`}>
              {runtime.mode === 'REAL' ? 'Real inference' : 'Demo mode'}
            </span>
          </div>
          <KV label="Checkpoint loaded">{runtime.loaded ? 'Yes' : 'No'}</KV>
          <KV label="Checkpoint path">
            <span className="mono sm" style={{ wordBreak: 'break-all' }}>{runtime.checkpoint_path}</span>
          </KV>
          <KV label="Model version"><span className="mono">{runtime.model_version}</span></KV>
          <KV label="Confidence threshold">
            <span className="mono">{runtime.confidence_threshold}</span>
          </KV>
          <KV label="Classes from checkpoint">
            <span className="mono">{runtime.supported_classes.length || '—'}</span>
          </KV>
          {runtime.load_error && (
            <div className="note" style={{
              marginTop: 12, borderColor: 'rgba(245,165,36,.3)',
              background: 'rgba(245,165,36,.07)', color: '#f0cf9a',
            }}>
              {runtime.load_error}. Analysis runs the demo path and every result is
              labelled as simulated.
            </div>
          )}
        </Card>

        <Card>
          <h3 style={{ marginBottom: 10 }}>Reported metrics</h3>
          {hasMetrics ? (
            <p className="mut sm">Figures below come from a held-out test split.</p>
          ) : (
            <div className="note" style={{
              borderColor: 'rgba(245,165,36,.3)',
              background: 'rgba(245,165,36,.07)', color: '#f0cf9a',
            }}>
              No accuracy, precision, recall or F1 figures are shown, because no labelled
              test set has been evaluated yet. Publishing invented numbers would
              misrepresent the system. Run <code>python -m ml.evaluate</code> and the real
              figures appear here.
            </div>
          )}
          <div className="sep" />
          <h3 style={{ marginBottom: 10 }}>Training pipeline</h3>
          <div className="flow">
            {PIPELINE.map((step, index) => (
              <div key={step}>
                <div className="step">
                  <b>{String(index + 1).padStart(2, '0')}</b>{step}
                </div>
                {index < PIPELINE.length - 1 && <div className="arw">↓</div>}
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Card style={{ marginTop: 16 }}>
        <h3 style={{ marginBottom: 10 }}>Version history</h3>
        <div className="tblwrap">
          <table>
            <thead>
              <tr><th>Version</th><th>Architecture</th><th>Dataset</th><th>Trained</th>
                  <th>Accuracy</th><th>F1</th><th>Status</th></tr>
            </thead>
            <tbody>
              {versions.map((v) => (
                <tr key={v.id}>
                  <td className="mono">{v.version}</td>
                  <td>{v.name}</td>
                  <td className="mut sm">{v.dataset_version}</td>
                  <td className="mut sm">{formatDate(v.trained_at)}</td>
                  <td className="mono">{v.accuracy ?? '—'}</td>
                  <td className="mono">{v.f1_score ?? '—'}</td>
                  <td>
                    <span className={`pill ${v.status === 'DEPLOYED' ? 'p-green' : 'p-grey'}`}>
                      {v.status === 'DEPLOYED' ? 'Deployed' : 'Archived'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="xs mut" style={{ marginTop: 10 }}>{data.metrics_note}</p>
      </Card>

      <Card style={{ marginTop: 16 }}>
        <h3 style={{ marginBottom: 10 }}>Learning loop</h3>
        <p className="mut sm">
          Human verifications from quarantine become labelled examples. They are collected
          into a dataset version and used for a future training run. They never retrain the
          deployed model automatically, and a new version is only promoted deliberately.
        </p>
        <div className="row" style={{ flexWrap: 'wrap', gap: 6, marginTop: 10 }}>
          {LEARNING_LOOP.map((step, index) => (
            <span key={step} style={{ display: 'contents' }}>
              <span className="pill p-grey">{step}</span>
              {index < LEARNING_LOOP.length - 1 && <span className="mut">→</span>}
            </span>
          ))}
        </div>
      </Card>
    </>
  )
}
