export async function fetchScan() {
  const base = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8010';
  const res = await fetch(base + '/scan');
  if (!res.ok) throw new Error('scan failed');
  return res.json();
}

export async function fetchAnalyze(name_or_code) {
  const base = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8010';
  const url = base + '/analyze?name_or_code=' + encodeURIComponent(name_or_code);
  const res = await fetch(url);
  if (!res.ok) throw new Error('analyze failed');
  return res.json();
}

export async function fetchUniverse() {
  const base = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8010';
  const res = await fetch(base + '/universe');
  if (!res.ok) throw new Error('universe failed');
  return res.json();
}


