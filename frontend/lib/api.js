export async function fetchScan() {
  const res = await fetch(process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000/scan');
  if (!res.ok) throw new Error('scan failed');
  return res.json();
}

export async function fetchAnalyze(name_or_code) {
  const base = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000';
  const url = base + '/analyze?name_or_code=' + encodeURIComponent(name_or_code);
  const res = await fetch(url);
  if (!res.ok) throw new Error('analyze failed');
  return res.json();
}


