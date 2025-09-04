import { useState, useEffect } from 'react';
import { fetchScan, fetchAnalyze, fetchUniverse, fetchSnapshots, fetchValidateFromSnapshot, reloadConfig } from '../lib/api';
import { sendScanResult } from '../lib/api';
import ResultTable from '../components/ResultTable';
import ValidateTable from '../components/ValidateTable';

export default function Page() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [q, setQ] = useState('005930');
  const [analyze, setAnalyze] = useState(null);
  const [universe, setUniverse] = useState(null);
  const [validate, setValidate] = useState(null);
  const [topK, setTopK] = useState(20);
  const [last, setLast] = useState({ type: null, data: null });
  const [snapshots, setSnapshots] = useState([]);
  const [snapAsOf, setSnapAsOf] = useState('');
  const [showDetails, setShowDetails] = useState((process.env.NEXT_PUBLIC_SHOW_DETAILS || '').toLowerCase() === 'true');
  const [kakaoTo, setKakaoTo] = useState('010');
  const [kakaoTopN, setKakaoTopN] = useState(5);

  const runScan = async () => {
    setLoading(true);
    try {
      const json = await fetchScan();
      setData(json);
      setLast({ type: 'scan', data: json });
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
      setLast({ type: 'analyze', data: json });
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
      setLast({ type: 'universe', data: json });
    } catch (e) {
      setUniverse({ error: String(e) });
    } finally {
      setLoading(false);
    }
  };

  // 기존 /validate 제거 → 스냅샷 기반 검증만 사용

  useEffect(() => {
    // 페이지 진입 시 자동으로 유니버스를 로드해 화면에 표시
    loadUniverse();
    // 스냅샷 목록 로드
    fetchSnapshots().then(r=>setSnapshots(r.items||[])).catch(()=>{});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <h1 className="text-2xl font-semibold">국내주식 조건 스캐너</h1>

      

      {/* 전략 라벨 설명 + 현재 가중치 */}
      <div className="bg-amber-50 border border-amber-200 rounded p-4 text-sm leading-6">
        <div className="font-semibold mb-1">전략 라벨 설명</div>
        <ul className="list-disc pl-5 space-y-1">
          <li><span className="font-medium">골든크로스 형성</span>: 최근 구간에서 <code>TEMA20</code>이 <code>DEMA10</code>을 상향 돌파했거나 현재 <code>TEMA20</code>이 위에 위치</li>
          <li><span className="font-medium">모멘텀 양전환</span>: <code>MACD_OSC</code>가 0보다 큼(양의 모멘텀)</li>
          <li><span className="font-medium">거래확대</span>: 현재 <code>VOL</code>이 <code>VOL_MA5 × VOL_MA5_MULT</code> 이상</li>
          <li><span className="font-medium">관망</span>: 위 조건이 충족되지 않아 대기 권고</li>
        </ul>
        <div className="text-xs text-gray-700 mt-2">
          현재 가중치/컷라인은 백엔드 `/ _reload_config`로 갱신 후 `/scan` 응답 메타 참조 필요(차후 표기 연동 예정).
        </div>
      </div>

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
        <div className="flex items-center gap-2 ml-4">
          <input className="border rounded px-2 py-1 w-20" type="number" min={1} value={topK} onChange={(e)=>setTopK(parseInt(e.target.value||'1',10))} title="top K" />
          <select className="border rounded px-2 py-1" value={snapAsOf} onChange={(e)=>setSnapAsOf(e.target.value)}>
            <option value="">스냅샷 선택</option>
            {snapshots.map(s=> (
              <option key={s.file} value={s.as_of}>{s.as_of} (matched {s.matched_count})</option>
            ))}
          </select>
          <button className="px-3 py-2 bg-slate-600 text-white rounded" onClick={async()=>{
            setLoading(true);
            try{ await reloadConfig(); } finally { setLoading(false); }
          }} disabled={loading}>리로드 설정</button>
          <button className="px-3 py-2 bg-indigo-600 text-white rounded" onClick={async()=>{
            if(!snapAsOf) return;
            setLoading(true);
            try{
              const r = await fetchValidateFromSnapshot(snapAsOf, topK);
              setValidate(r);
              setLast({ type: 'validate', data: r });
            }catch(e){ setValidate({error:String(e)}); }
            finally{ setLoading(false); }
          }} disabled={loading || !snapAsOf}>
            {loading ? '검증중...' : '스냅샷 검증'}
          </button>
        </div>
        <label className="ml-auto flex items-center gap-2 text-sm">
          <input type="checkbox" checked={showDetails} onChange={(e)=>setShowDetails(e.target.checked)} />
          고급 지표 보기
        </label>
      </div>
      <div className="flex items-center gap-2 text-sm">
        <input className="border rounded px-2 py-1 w-40" placeholder="수신번호(숫자)" value={kakaoTo} onChange={e=>setKakaoTo(e.target.value)} />
        <input className="border rounded px-2 py-1 w-20" type="number" min={1} max={20} value={kakaoTopN} onChange={e=>setKakaoTopN(parseInt(e.target.value||'5',10))} />
        <button className="px-3 py-2 bg-pink-600 text-white rounded" onClick={async()=>{
          setLoading(true);
          try{
            const r = await sendScanResult(kakaoTo, kakaoTopN);
            alert(r.status === 'ok' ? '발송 성공' : '발송 실패: ' + JSON.stringify(r.provider||r));
          }catch(e){ alert('발송 오류: ' + String(e)); }
          finally{ setLoading(false); }
        }} disabled={loading}>카카오 발송</button>
      </div>

      {/* 최근 실행 결과 - 버튼 아래에만 표시 */}
      {last && last.type && (
        <div className="border rounded p-4 bg-white shadow-sm space-y-2">
          <div className="text-sm text-gray-700">최근 실행: <span className="font-medium">{last.type}</span></div>
          {last.type === 'scan' && last.data && (
            <div className="space-y-2">
              <div className="text-sm text-gray-600">as_of: {last.data.as_of}, universe: {last.data.universe_count}, matched: {last.data.matched_count}</div>
              <div className="text-xs text-gray-600">weights: {last.data.score_weights ? JSON.stringify(last.data.score_weights) : '-'}, levels: S {last.data.score_level_strong} / W {last.data.score_level_watch}, dema_mode: {last.data.require_dema_slope}</div>
              <ResultTable items={last.data.items || []} showDetails={showDetails} />
            </div>
          )}
          {last.type === 'universe' && last.data && (
            <div className="space-y-2">
              <div className="text-sm text-gray-600">as_of: {last.data.as_of}, count: {(last.data.items||[]).length}</div>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2 text-sm">
                {(last.data.items||[]).map((u) => (
                  <div key={u.ticker} className="border rounded px-2 py-1 flex justify-between"><span className="font-mono">{u.ticker}</span><span>{u.name}</span></div>
                ))}
              </div>
            </div>
          )}
          {last.type === 'analyze' && last.data && (
            <pre className="bg-gray-100 p-3 rounded text-xs overflow-x-auto">{JSON.stringify(last.data, null, 2)}</pre>
          )}
          {last.type === 'validate' && last.data && (
            <div className="space-y-2">
              <div className="text-sm text-gray-600">snapshot: {last.data.snapshot_as_of}, top_k: {last.data.top_k}, count: {last.data.count}, win: {last.data.win_rate_pct}% avg: {last.data.avg_return_pct}% mdd: {last.data.mdd_pct}% | 최대수익률 평균: {last.data.avg_max_return_pct}% 최대: {last.data.max_max_return_pct}%</div>
              <ValidateTable items={last.data.items || []} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}


