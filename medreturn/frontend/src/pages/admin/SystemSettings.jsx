import { useEffect, useState } from 'react'
import { Card, ErrorNote, KV, Loading, PageHeader } from '../../components/ui.jsx'
import { api } from '../../lib/api'

export default function SystemSettings() {
  const [settings, setSettings] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => { api.adminSettings().then(setSettings).catch(setError) }, [])

  if (error) return <ErrorNote error={error} />
  if (!settings) return <Loading />

  return (
    <>
      <PageHeader
        title="System settings"
        subtitle="Runtime configuration the decision engine and reward rules read."
      />
      <div className="split">
        <Card>
          <h3 style={{ marginBottom: 10 }}>Decision engine</h3>
          <KV label="Demo mode">
            <span className={`pill ${settings.demo_mode ? 'p-amber' : 'p-green'}`}>
              {settings.demo_mode ? 'On' : 'Off'}
            </span>
          </KV>
          <KV label="Confidence threshold">
            <span className="mono">{settings.confidence_threshold}</span>
          </KV>
          <KV label="Credits per verified return">
            <span className="mono">{settings.credits_per_verified_return}</span>
          </KV>
          <KV label="Email transport"><span className="mono">{settings.email_transport}</span></KV>
          <KV label="Maps provider"><span className="mono">{settings.maps_provider}</span></KV>
          <KV label="Hardware">
            <span className={`pill ${settings.hardware_simulated ? 'p-amber' : 'p-green'}`}>
              {settings.hardware_simulated ? 'Simulated' : 'Connected'}
            </span>
          </KV>
          <div className="note" style={{ marginTop: 14 }}>
            These values come from environment variables on the server. Edit the backend
            <code>.env</code> and restart the API to change them.
          </div>
        </Card>

        <Card>
          <h3 style={{ marginBottom: 10 }}>Supported classes</h3>
          <p className="mut sm">
            Hospital waste classes must match the labels the model was trained on. Editing
            one without retraining the other produces confident but wrong routing.
          </p>
          <div className="chips" style={{ marginTop: 10 }}>
            {settings.supported_waste_classes.map((c) => (
              <span className="chip on" key={c}>{c}</span>
            ))}
          </div>
          <div className="sep" />
          <h3 style={{ marginBottom: 10 }}>Household return categories</h3>
          <div className="chips">
            {settings.supported_return_categories.map((c) => (
              <span className="chip" key={c}>{c}</span>
            ))}
          </div>
        </Card>
      </div>
    </>
  )
}
