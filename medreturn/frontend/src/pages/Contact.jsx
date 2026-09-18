import { Card, KV, PageHeader } from '../components/ui.jsx'

export default function Contact() {
  return (
    <div className="narrow" style={{ padding: '44px 22px' }}>
      <PageHeader title="Contact" subtitle="Prototype support contacts, for the demo." />
      <Card>
        <KV label="Support email"><span className="mono">support@medreturn.in</span></KV>
        <KV label="Helpline"><span className="mono">1800-123-4567</span></KV>
        <KV label="Operations">Ludhiana, Punjab</KV>
        <KV label="Hospital onboarding"><span className="mono">partners@medreturn.in</span></KV>
      </Card>
    </div>
  )
}
