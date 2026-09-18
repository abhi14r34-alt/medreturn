import { Card, PageHeader } from '../components/ui.jsx'

const DOES_NOT = [
  'Claim 100% classification accuracy',
  'Guarantee safe disposal on its own',
  'Give medical or diagnostic advice',
  'Confirm that a medicine is genuine, safe or legal from a photograph',
  'Claim regulatory approval',
  'Operate autonomously without human checks',
]

const DOES = [
  'Assist identification against a configured list of supported categories',
  'Hold uncertain items for human verification',
  'Keep a traceable record of every decision',
  'Label simulated data as DEMO MODE',
  'Award credits only after physical verification',
]

export default function Safety() {
  return (
    <div className="narrow" style={{ padding: '44px 22px' }}>
      <PageHeader
        title="Safety and limitations"
        subtitle="Read this before treating any output as authoritative."
      />
      <Card>
        <h3 style={{ marginBottom: 10 }}>What this system does not do</h3>
        {DOES_NOT.map((item) => (
          <div className="kv" key={item}>
            <span>{item}</span>
            <span className="pill p-red">No</span>
          </div>
        ))}
      </Card>
      <Card style={{ marginTop: 14 }}>
        <h3 style={{ marginBottom: 10 }}>What it does do</h3>
        {DOES.map((item) => (
          <div className="kv" key={item}>
            <span>{item}</span>
            <span className="pill p-green">Yes</span>
          </div>
        ))}
      </Card>
      <div className="note" style={{ marginTop: 14 }}>
        Sharps, cytotoxic drugs and controlled substances must follow your local biomedical
        waste rules. Handle them as your facility's protocol requires, whatever this screen
        says.
      </div>
    </div>
  )
}
