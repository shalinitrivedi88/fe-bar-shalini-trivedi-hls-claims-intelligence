async function get(path) {
  const r = await fetch(path)
  if (!r.ok) throw new Error(`${path} -> ${r.status}`)
  return r.json()
}
async function post(path, body) {
  const r = await fetch(path, {
    method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!r.ok) throw new Error(`${path} -> ${r.status}`)
  return r.json()
}

export const api = {
  summary: () => get('/api/summary'),
  triageQueue: () => get('/api/triage-queue'),
  dispositionGap: () => get('/api/disposition-gap'),
  search: (q) => post('/api/search', { q }),
  chat: (question) => post('/api/chat', { question }),
}
