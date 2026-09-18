import { Card, PageHeader } from '../components/ui.jsx'

export default function About() {
  return (
    <div className="narrow" style={{ padding: '44px 22px' }}>
      <PageHeader
        title="About MedReturn"
        subtitle="Built for Smart India Hackathon 2026, problem statement SIH26115."
      />
      <Card>
        <p>
          Hospitals segregate waste under time pressure, and households have nowhere obvious
          to send expired medicine. Both problems end the same way: pharmaceutical and
          infectious waste in general refuse.
        </p>
        <p>
          MedReturn puts a camera and a decision engine at the point where waste is handled,
          and a pickup service at the point where households give medicine up. Every decision
          writes a record that can be traced later.
        </p>
        <p className="mut sm" style={{ margin: 0 }}>
          Stack: React and Vite on the front, FastAPI with Pydantic and SQLAlchemy behind it,
          MySQL for storage, and PyTorch transfer learning on MobileNetV3 for classification.
        </p>
      </Card>
    </div>
  )
}
