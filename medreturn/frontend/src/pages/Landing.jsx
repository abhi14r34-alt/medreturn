import { Link } from 'react-router-dom'
import FlowDiagram, { HOSPITAL_FLOW, HOUSEHOLD_FLOW } from '../components/FlowDiagram.jsx'
import { Card } from '../components/ui.jsx'

export default function Landing() {
  return (
    <>
      <section className="hero">
        <div className="wrap">
          <div className="herogrid">
            <div>
              <span className="demo">PROTOTYPE · DEMO MODE</span>
              <h1 style={{ marginTop: 16 }}>Smart medical waste management</h1>
              <p className="sub">
                Safer hospitals and responsible households on one platform. AI assists the
                sorting decision; people confirm anything the model is unsure about.
              </p>
              <div className="row" style={{ flexWrap: 'wrap' }}>
                <Link className="btn pri" to="/login">Analyze waste</Link>
                <Link className="btn blue" to="/login">Return medicine</Link>
                <Link className="btn ghost" to="/how-it-works">See how it works</Link>
              </div>
            </div>

            <div className="preview">
              <div className="bar2">
                <i /><i /><i />
                <span className="xs mut mono" style={{ marginLeft: 6 }}>
                  segregation line
                </span>
                <span className="spacer" />
                <span className="demo" style={{ fontSize: 10 }}>DEMO</span>
              </div>
              <div className="body">
                {[
                  ['Sharps', 0.95, 'Routed'],
                  ['Pharmaceutical', 0.88, 'Routed'],
                  ['Glass', 0.64, 'Held'],
                  ['Infectious', 0.92, 'Routed'],
                ].map(([label, confidence, outcome]) => (
                  <div className="prow" key={label}>
                    <span style={{ flex: 1 }}>{label}</span>
                    <span
                      className={`pill ${confidence >= 0.8 ? 'p-green' : 'p-amber'} mono`}
                      style={{ fontSize: 11 }}
                    >
                      {Math.round(confidence * 100)}%
                    </span>
                    <span
                      className={`pill ${outcome === 'Routed' ? 'p-teal' : 'p-amber'}`}
                      style={{ fontSize: 11 }}
                    >
                      {outcome}
                    </span>
                  </div>
                ))}
                <div
                  className="prow"
                  style={{ borderStyle: 'dashed', background: 'transparent', color: 'var(--mut)' }}
                >
                  <span>Below 80% confidence never routes automatically</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="wrap" style={{ padding: '52px 22px' }}>
        <div className="split">
          <Card>
            <div className="between" style={{ marginBottom: 14 }}>
              <h2>Hospital</h2>
              <span className="pill p-teal">Segregation line</span>
            </div>
            <p className="mut sm">
              Waste passes a camera and sensor stage before any mechanical sorting happens.
              Anything the model scores below the confidence threshold is held back rather
              than routed.
            </p>
            <FlowDiagram steps={HOSPITAL_FLOW} accent="var(--teal)" />
          </Card>

          <Card>
            <div className="between" style={{ marginBottom: 14 }}>
              <h2>Household</h2>
              <span className="pill p-blue">Medicine return</span>
            </div>
            <p className="mut sm">
              Photograph what you want to return, get an eligibility answer, book a pickup,
              and follow it until a collector takes it away. Credits land only after the
              items are checked.
            </p>
            <FlowDiagram steps={HOUSEHOLD_FLOW} accent="var(--blue)" />
          </Card>
        </div>

        <div className="note" style={{ marginTop: 28 }}>
          This is a working prototype for SIH26115. It does not claim 100% classification
          accuracy, guaranteed safe disposal, medical advice, or regulatory approval.
          Simulated behaviour is labelled DEMO MODE wherever it appears.
        </div>
      </section>
    </>
  )
}
