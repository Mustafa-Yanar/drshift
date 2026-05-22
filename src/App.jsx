import { useState } from 'react'
import { Plus, Trash2, Calendar, Settings, Activity } from 'lucide-react'
import './index.css'

function App() {
  const [doctors, setDoctors] = useState([
    { id: '1', name: 'Dr. Ahmet' },
    { id: '2', name: 'Dr. Ayşe' },
    { id: '3', name: 'Dr. Mehmet' },
    { id: '4', name: 'Dr. Fatma' },
    { id: '5', name: 'Dr. Ali' }
  ])
  const [newDocName, setNewDocName] = useState('')
  
  const [schedule, setSchedule] = useState(null)
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const addDoctor = (e) => {
    e.preventDefault()
    if (!newDocName.trim()) return
    const id = Date.now().toString()
    setDoctors([...doctors, { id, name: newDocName }])
    setNewDocName('')
  }

  const removeDoctor = (id) => {
    setDoctors(doctors.filter(d => d.id !== id))
  }

  const toggleExemption = (id) => {
    setDoctors(doctors.map(d => {
      if (d.id === id) {
        return { ...d, is_exempt: !d.is_exempt, target_total_minutes: d.is_exempt ? null : 420 }
      }
      return d
    }))
  }

  const updateTargetMinutes = (id, val) => {
    setDoctors(doctors.map(d => {
      if (d.id === id) {
        return { ...d, target_total_minutes: parseInt(val) || 0 }
      }
      return d
    }))
  }

  const generateSchedule = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch('/api/solve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ doctors, pre_assignments: [] })
      })
      const data = await response.json()
      if (response.ok && data.status === 'success') {
        setSchedule(data.schedule)
        setStats(data.stats)
      } else {
        setError(data.detail || data.message || 'Çözüm bulunamadı.')
      }
    } catch (err) {
      setError('Sunucu ile bağlantı kurulamadı.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app-container">
      <header>
        <h1>Dr.Shift</h1>
        <div className="subtitle">Akıllı Hastane Nöbet Çizelgeleyici</div>
      </header>

      <div className="grid-2">
        <div className="card">
          <div className="card-title"><Activity size={20} /> Doktor Yönetimi</div>
          
          <form onSubmit={addDoctor} className="flex-row" style={{ marginBottom: '1.5rem' }}>
            <div className="input-group" style={{ flex: 1, marginBottom: 0 }}>
              <input 
                type="text" 
                placeholder="Doktor Adı" 
                value={newDocName} 
                onChange={e => setNewDocName(e.target.value)} 
              />
            </div>
            <button type="submit"><Plus size={18} /> Ekle</button>
          </form>

          <div className="doctor-list">
            {doctors.map(doc => (
              <div key={doc.id} className="doctor-item">
                <div className="doc-info">
                  <div className="doc-name">{doc.name}</div>
                  {doc.is_exempt && (
                    <div className="input-group" style={{ margin: '0.5rem 0 0 0' }}>
                      <label style={{ fontSize: '0.75rem' }}>Hedef Süre (Dk)</label>
                      <input 
                        type="number" 
                        value={doc.target_total_minutes || ''} 
                        onChange={e => updateTargetMinutes(doc.id, e.target.value)}
                        style={{ padding: '0.25rem 0.5rem', fontSize: '0.85rem' }}
                      />
                    </div>
                  )}
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button 
                    type="button" 
                    className="secondary" 
                    title="Muafiyet / Özel Süre Ayarla"
                    onClick={() => toggleExemption(doc.id)}
                    style={{ padding: '0.5rem', opacity: doc.is_exempt ? 1 : 0.5 }}
                  >
                    <Settings size={16} />
                  </button>
                  <button type="button" className="danger" onClick={() => removeDoctor(doc.id)} style={{ padding: '0.5rem' }}>
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', textAlign: 'center' }}>
          <div className="card-title" style={{ justifyContent: 'center' }}>
            <Calendar size={24} /> Nöbet Çizelgesi Oluştur
          </div>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem', fontSize: '0.9rem' }}>
            {doctors.length} doktor için 09:00 - 00:00 saatleri arasındaki Yeşil ve Sarı alan nöbetlerini optimize et.
          </p>
          <button onClick={generateSchedule} disabled={loading || doctors.length === 0} style={{ padding: '1rem 2rem', fontSize: '1.1rem' }}>
            {loading ? <div className="loader" /> : 'Çizelgeyi Hesapla'}
          </button>
          {error && <div style={{ color: '#f87171', marginTop: '1rem', background: 'rgba(239, 68, 68, 0.1)', padding: '0.5rem 1rem', borderRadius: '0.5rem' }}>{error}</div>}
        </div>
      </div>

      {schedule && (
        <div className="card">
          <div className="card-title">Sonuçlar & Çizelge</div>
          
          <div className="timeline-container">
            <table className="timeline">
              <thead>
                <tr>
                  <th className="time-label">Saat</th>
                  <th>Sarı Alan</th>
                  <th>Yeşil Alan</th>
                </tr>
              </thead>
              <tbody>
                {schedule.map(p => (
                  <tr key={p.period}>
                    <td className="time-label">{p.time}</td>
                    <td>
                      <div className="shift-cell">
                        {p.yellow.map(dId => {
                          const doc = doctors.find(d => d.id === dId)
                          return <div key={dId} className="shift-block shift-yellow">{doc ? doc.name : dId}</div>
                        })}
                      </div>
                    </td>
                    <td>
                      <div className="shift-cell">
                        <div style={{ display: 'flex', gap: '4px', width: '100%', height: '100%' }}>
                          {p.green.map(dId => {
                            const doc = doctors.find(d => d.id === dId)
                            return <div key={dId} className="shift-block shift-green" style={{ position: 'relative', flex: 1, top: 0, bottom: 0, left: 0, right: 0 }}>{doc ? doc.name : dId}</div>
                          })}
                        </div>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

export default App
