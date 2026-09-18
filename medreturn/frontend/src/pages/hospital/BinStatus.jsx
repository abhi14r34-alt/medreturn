import { useEffect, useState } from 'react'
import { DemoTag, ErrorNote, Loading, PageHeader } from '../../components/ui.jsx'
import { api } from '../../lib/api'

export default function BinStatus() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => { api.bins().then(setData).catch(setError) }, [])

  if (error) return <ErrorNote error={error} />
  if (!data) return <Loading />

  return (
    <>
      <PageHeader
        title="Bin status"
        subtitle="Fill levels derived from accepted event weights."
        actions={!data.sensor_connected ? <DemoTag>SENSOR SIMULATION</DemoTag> : null}
      />
      <div className="grid g3">
        {data.compartments.map((bin) => {
          const tone = bin.fill_percent > 85 ? 'red' : bin.fill_percent > 60 ? 'amber' : 'teal'
          const color = `var(--${tone === 'red' ? 'red' : tone === 'amber' ? 'amber' : 'teal'})`
          return (
            <div className="bin" key={bin.name}>
              <div className="between">
                <b>{bin.name}</b>
                <span className={`pill p-${tone}`}>{bin.fill_percent}%</span>
              </div>
              <div className="xs mut mono" style={{ marginTop: 3 }}>{bin.compartment}</div>
              <div className="binlvl">
                <i style={{
                  height: `${bin.fill_percent}%`,
                  background: `linear-gradient(180deg, ${color}, transparent)`,
                }} />
              </div>
              <div className="between xs mut" style={{ marginTop: 8 }}>
                <span>{bin.weight_kg} kg</span>
                <span>capacity {bin.capacity_kg} kg</span>
              </div>
              {bin.fill_percent > 85 && (
                <div className="xs" style={{ color: 'var(--red)', marginTop: 6 }}>
                  Schedule emptying
                </div>
              )}
            </div>
          )
        })}
      </div>
      <p className="xs mut" style={{ marginTop: 12 }}>{data.note}</p>
    </>
  )
}
