import FlowDiagram, { HOSPITAL_FLOW, HOUSEHOLD_FLOW } from '../components/FlowDiagram.jsx'
import { Card, PageHeader } from '../components/ui.jsx'

export default function HowItWorks() {
  return (
    <div className="narrow" style={{ padding: '44px 22px' }}>
      <PageHeader title="How it works" subtitle="Two workflows, one record trail." />
      <div className="split">
        <Card>
          <h3 style={{ marginBottom: 12 }}>Hospital line</h3>
          <FlowDiagram steps={HOSPITAL_FLOW} />
        </Card>
        <Card>
          <h3 style={{ marginBottom: 12 }}>Household return</h3>
          <FlowDiagram steps={HOUSEHOLD_FLOW} accent="var(--blue)" />
        </Card>
      </div>

      <Card className="" style={{ marginTop: 18 }}>
        <h3>The confidence gate</h3>
        <p className="mut sm">
          Every prediction is checked against two conditions before anything moves: the
          predicted class must be in the configured supported list, and confidence must be
          at or above the threshold set in the backend environment. If either fails, the
          item goes to quarantine and waits for a person.
        </p>
      </Card>

      <Card style={{ marginTop: 14 }}>
        <h3>Credits</h3>
        <p className="mut sm">
          Uploading a photo earns nothing. A credit transaction is written only after a
          pickup reaches COLLECTED and an operator marks the items VERIFIED.
        </p>
      </Card>
    </div>
  )
}
