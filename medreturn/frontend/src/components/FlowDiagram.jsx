/** The workflow diagrams from the problem statement, rendered as a column. */

export const HOSPITAL_FLOW = [
  'Mixed waste arrives',
  'Controlled feed',
  'Camera and sensors',
  'AI classification',
  'Confidence check',
  'Route or quarantine',
  'Digital record',
]

export const HOUSEHOLD_FLOW = [
  'Upload medicine photo',
  'AI identification',
  'Eligibility result',
  'Pickup request',
  'Schedule and assign',
  'Track to your door',
  'Safe handoff',
  'Credits after verification',
]

export default function FlowDiagram({ steps, accent = 'var(--teal)' }) {
  return (
    <div className="flow">
      {steps.map((step, index) => (
        <div key={step}>
          <div className="step">
            <b style={{ color: accent }}>{String(index + 1).padStart(2, '0')}</b>
            {step}
          </div>
          {index < steps.length - 1 && <div className="arw">↓</div>}
        </div>
      ))}
    </div>
  )
}
