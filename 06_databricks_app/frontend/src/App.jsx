import React, { useEffect, useState } from 'react'
import { api } from './api.js'

const usd = (n) => n == null ? '—' : new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n)
const pct = (n) => n == null ? '—' : `${(n * 100).toFixed(1)}%`
const tier = (s) => s >= 0.66 ? 'high' : s >= 0.33 ? 'med' : 'low'

function Kpi({ label, value, sub }) {
  return (
    <div className="kpi">
      <div className="kpi-value">{value}</div>
      <div className="kpi-label">{label}</div>
      {sub && <div className="kpi-sub">{sub}</div>}
    </div>
  )
}

export default function App() {
  const [sum, setSum] = useState(null)
  const [queue, setQueue] = useState([])
  const [gap, setGap] = useState([])
  const [q, setQ] = useState('member appealing a denied high-cost claim')
  const [results, setResults] = useState(null)
  const [searching, setSearching] = useState(false)
  const [question, setQuestion] = useState('Which disposition has the biggest downstream-action gap?')
  const [answer, setAnswer] = useState('')
  const [asking, setAsking] = useState(false)
  const [err, setErr] = useState('')

  useEffect(() => {
    api.summary().then(setSum).catch(e => setErr(String(e)))
    api.triageQueue().then(setQueue).catch(e => setErr(String(e)))
    api.dispositionGap().then(setGap).catch(e => setErr(String(e)))
  }, [])

  const runSearch = async () => {
    setSearching(true); setResults(null)
    try { setResults((await api.search(q)).results || []) }
    catch (e) { setErr(String(e)) } finally { setSearching(false) }
  }
  const runAsk = async () => {
    setAsking(true); setAnswer('')
    try { setAnswer((await api.chat(question)).answer) }
    catch (e) { setErr(String(e)) } finally { setAsking(false) }
  }

  const maxGap = Math.max(1, ...gap.map(g => g.dispositions))

  return (
    <div className="app">
      <header>
        <h1>Claims Operations Console</h1>
        <span className="badge">Cascade Benefit Systems · fictional · synthetic data</span>
      </header>

      {err && <div className="err">{err}</div>}

      <section className="kpis">
        <Kpi label="Total billed" value={usd(sum?.total_billed)} sub={`${sum?.claims?.toLocaleString?.() ?? ''} claims`} />
        <Kpi label="Denied + pending pool" value={usd(sum?.rework_pool)} sub="rework exposure" />
        <Kpi label="Downstream-action fired" value={pct(sum?.action_fired_rate)} sub="the event-blindness gap" />
        <Kpi label="Flagged for review" value={sum?.flagged_for_review?.toLocaleString?.() ?? '—'} sub="needs a coder" />
      </section>

      <div className="grid">
        <section className="card">
          <h2>Triage queue <small>ML-prioritized</small></h2>
          <table>
            <thead><tr><th>Claim</th><th>Score</th><th>Status</th><th>Reason</th><th>Billed</th></tr></thead>
            <tbody>
              {queue.map(r => (
                <tr key={r.claim_id}>
                  <td className="mono">{r.claim_id}</td>
                  <td><span className={`score ${tier(r.score)}`}>{r.score}</span></td>
                  <td>{r.status}</td>
                  <td className="muted">{r.denial_reason || '—'}</td>
                  <td>{usd(r.billed_amount)}</td>
                </tr>
              ))}
              {!queue.length && <tr><td colSpan="5" className="muted">loading…</td></tr>}
            </tbody>
          </table>
        </section>

        <section className="card">
          <h2>Disposition-action gap</h2>
          {gap.map(g => (
            <div className="bar-row" key={g.disposition}>
              <div className="bar-label">{g.disposition}</div>
              <div className="bar-track"><div className="bar-fill" style={{ width: `${(g.dispositions / maxGap) * 100}%` }} /></div>
              <div className="bar-val">{pct(g.action_fired_rate)} fired · {g.dispositions.toLocaleString()}</div>
            </div>
          ))}
          {!gap.length && <div className="muted">loading…</div>}
        </section>

        <section className="card">
          <h2>Find similar prior cases <small>hybrid search</small></h2>
          <div className="row">
            <input value={q} onChange={e => setQ(e.target.value)} placeholder="describe the case…" />
            <button onClick={runSearch} disabled={searching}>{searching ? 'Searching…' : 'Search'}</button>
          </div>
          <ul className="results">
            {results?.map(r => (
              <li key={r.claim_id}><span className="mono">{r.claim_id}</span> <span className="rrf">{r.rrf_score}</span><div className="muted">{r.narrative}</div></li>
            ))}
            {results && !results.length && <li className="muted">no matches</li>}
          </ul>
        </section>

        <section className="card">
          <h2>Ask</h2>
          <div className="row">
            <input value={question} onChange={e => setQuestion(e.target.value)} />
            <button onClick={runAsk} disabled={asking}>{asking ? '…' : 'Ask'}</button>
          </div>
          {answer && <pre className="answer">{answer}</pre>}
        </section>
      </div>
    </div>
  )
}
