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

export async function fetchSnapshots() {
  const base = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8010';
  const res = await fetch(base + '/snapshots');
  if (!res.ok) throw new Error('snapshots failed');
  return res.json();
}

export async function fetchValidateFromSnapshot(asOf, topK) {
  const base = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8010';
  const url = base + `/validate_from_snapshot?as_of=${encodeURIComponent(asOf)}&top_k=${encodeURIComponent(topK)}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('validate_from_snapshot failed');
  return res.json();
}

export async function reloadConfig() {
  const base = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8010';
  const res = await fetch(base + '/_reload_config', { method: 'POST' });
  if (!res.ok) throw new Error('reload_config failed');
  return res.json();
}

export async function sendScanResult(to, topN=5){
  const base = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8010';
  const url = base + '/send_scan_result?to=' + encodeURIComponent(to) + '&top_n=' + encodeURIComponent(topN);
  const res = await fetch(url, { method: 'POST' });
  if (!res.ok) throw new Error('send_scan_result failed');
  return res.json();
}


