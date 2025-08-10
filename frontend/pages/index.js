import { useState, useEffect } from 'react';
import { fetchScan, fetchAnalyze, fetchUniverse } from '../lib/api';
import ResultTable from '../components/ResultTable';

export default function Page() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [q, setQ] = useState('005930');
  const [analyze, setAnalyze] = useState(null);
  const [universe, setUniverse] = useState(null);

  const runScan = async () => {
    setLoading(true);
    try {
      const json = await fetchScan();
      setData(json);
    } catch (e) {
      setData({ error: String(e) });
    } finally {
      setLoading(false);
    }
  };

  const runAnalyze = async () => {
    setLoading(true);
    try {
      const json = await fetchAnalyze(q);
      setAnalyze(json);
    } catch (e) {
      setAnalyze({ error: String(e) });
    } finally {
      setLoading(false);
    }
  };

  const loadUniverse = async () => {
    setLoading(true);
    try {
      const json = await fetchUniverse();
      setUniverse(json || { items: [] });
    } catch (e) {
      setUniverse({ error: String(e) });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // 페이지 진입 시 자동으로 유니버스를 로드해 화면에 표시
    loadUniverse();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <h1 className="text-2xl font-semibold">국내주식 조건 스캐너</h1>

      <div className="flex items-center gap-3">
        <button className="px-4 py-2 bg-blue-600 text-white rounded" onClick={runScan} disabled={loading}>
          {loading ? '실행중...' : '조건검색 실행 (/scan)'}
        </button>

        <button className="px-4 py-2 bg-emerald-600 text-white rounded" onClick={loadUniverse} disabled={loading}>
          {loading ? '로딩...' : '유니버스 보기 (/universe)'}
        </button>

        <input className="border rounded px-3 py-2" value={q} onChange={(e)=>setQ(e.target.value)} placeholder="종목명 또는 코드" />
        <button className="px-4 py-2 bg-gray-700 text-white rounded" onClick={runAnalyze} disabled={loading}>
          단일 분석 (/analyze)
        </button>
      </div>

      {data && (
        <div className="space-y-2">
          <div className="text-sm text-gray-600">as_of: {data.as_of}, universe: {data.universe_count}, matched: {data.matched_count}</div>
          <div className="text-sm text-gray-600">RSI mode: {data.rsi_mode} (period {data.rsi_period}, thr {data.rsi_threshold})</div>
          <ResultTable items={data.items || []} />
        </div>
      )}

      {universe && universe.items && (
        <div className="space-y-2">
          <h2 className="text-lg font-medium">거래대금 상위 유니버스</h2>
          <div className="text-sm text-gray-600">as_of: {universe.as_of}, count: {universe.items.length}</div>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2 text-sm">
            {universe.items.map((u) => (
              <div key={u.ticker} className="border rounded px-2 py-1 flex justify-between"><span className="font-mono">{u.ticker}</span><span>{u.name}</span></div>
            ))}
          </div>
        </div>
      )}

      {analyze && (
        <pre className="bg-gray-100 p-3 rounded text-xs overflow-x-auto">{JSON.stringify(analyze, null, 2)}</pre>
      )}
    </div>
  );
}


