import { useState, useEffect } from 'react';
import { fetchScan, fetchAnalyze, fetchUniverse, fetchSnapshots, fetchValidateFromSnapshot, reloadConfig } from '../lib/api';
import { sendScanResult, fetchScanPositions, autoAddPositions } from '../lib/api';
import ResultTable from '../components/ResultTable';
import ValidateTable from '../components/ValidateTable';
import Link from 'next/link';

export default function AdminScanner() {
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
  const [scanPositions, setScanPositions] = useState([]);
  const [autoPositionSettings, setAutoPositionSettings] = useState({
    scoreThreshold: 8,
    defaultQuantity: 10,
    entryDate: new Date().toISOString().split('T')[0],
    autoAddOnScan: false
  });

  const runScan = async () => {
    setLoading(true);
    try {
      const json = await fetchScan();
      setData(json);
      setLast({ type: 'scan', data: json });
      
      // 자동 포지션 추가 옵션이 켜져 있으면 실행
      if (autoPositionSettings.autoAddOnScan) {
        try {
          const result = await autoAddPositions(
            autoPositionSettings.scoreThreshold,
            autoPositionSettings.defaultQuantity,
            autoPositionSettings.entryDate
          );
          if (result.ok && result.added_count > 0) {
            alert(`스캔 완료 후 ${result.added_count}개 종목이 자동으로 포지션에 추가되었습니다.`);
            loadScanPositions(); // 포지션 목록 새로고침
          }
        } catch (e) {
          console.error('Auto position add failed:', e);
        }
      }
    } catch (e) {
      console.error('Scan failed:', e);
      alert('스캔 실행 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const runAnalyze = async () => {
    if (!q.trim()) {
      alert('종목코드를 입력해주세요.');
      return;
    }
    setLoading(true);
    try {
      const json = await fetchAnalyze(q);
      setAnalyze(json);
      setLast({ type: 'analyze', data: json });
    } catch (e) {
      console.error('Analyze failed:', e);
      alert('분석 실행 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const loadUniverse = async () => {
    setLoading(true);
    try {
      const json = await fetchUniverse();
      // universe가 배열인지 확인하고, 아니면 빈 배열로 설정
      const universeData = Array.isArray(json) ? json : [];
      setUniverse(universeData);
      setLast({ type: 'universe', data: universeData });
    } catch (e) {
      console.error('Universe load failed:', e);
      alert('유니버스 로드 중 오류가 발생했습니다.');
      setUniverse([]); // 오류 시 빈 배열로 설정
    } finally {
      setLoading(false);
    }
  };

  const loadSnapshots = async () => {
    setLoading(true);
    try {
      const json = await fetchSnapshots();
      // snapshots가 배열인지 확인하고, 아니면 빈 배열로 설정
      setSnapshots(Array.isArray(json) ? json : []);
    } catch (e) {
      console.error('Snapshots load failed:', e);
      alert('스냅샷 로드 중 오류가 발생했습니다.');
      setSnapshots([]); // 오류 시 빈 배열로 설정
    } finally {
      setLoading(false);
    }
  };

  const validateFromSnapshot = async () => {
    if (!snapAsOf) {
      alert('스냅샷 날짜를 선택해주세요.');
      return;
    }
    setLoading(true);
    try {
      const json = await fetchValidateFromSnapshot(snapAsOf);
      setValidate(json);
      setLast({ type: 'validate', data: json });
    } catch (e) {
      console.error('Validate failed:', e);
      alert('검증 실행 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const loadScanPositions = async () => {
    try {
      const positions = await fetchScanPositions();
      // positions가 배열인지 확인하고, 아니면 빈 배열로 설정
      setScanPositions(Array.isArray(positions) ? positions : []);
    } catch (e) {
      console.error('Failed to load scan positions:', e);
      setScanPositions([]); // 오류 시 빈 배열로 설정
    }
  };

  const sendKakaoAlert = async () => {
    if (!last.data || last.type !== 'scan') {
      alert('먼저 스캔을 실행해주세요.');
      return;
    }
    
    if (!kakaoTo.trim()) {
      alert('카카오톡 수신번호를 입력해주세요.');
      return;
    }

    try {
      const result = await sendScanResult(kakaoTo, kakaoTopN, last.data);
      if (result.ok) {
        alert('카카오톡 알림이 전송되었습니다.');
      } else {
        alert(`전송 실패: ${result.error || '알 수 없는 오류'}`);
      }
    } catch (e) {
      console.error('Kakao send failed:', e);
      alert('카카오톡 전송 중 오류가 발생했습니다.');
    }
  };

  const handleConfigReload = async () => {
    try {
      await reloadConfig();
      alert('설정이 다시 로드되었습니다.');
    } catch (e) {
      console.error('Config reload failed:', e);
      alert('설정 재로드 중 오류가 발생했습니다.');
    }
  };

  useEffect(() => {
    loadSnapshots();
    loadScanPositions();
  }, []);

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-7xl mx-auto">
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <div className="flex items-center justify-between mb-6">
            <h1 className="text-2xl font-bold text-gray-900">관리자 스캐너</h1>
            <div className="flex space-x-4">
              <Link href="/customer-scanner" className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600">
                고객용 스캐너
              </Link>
              <Link href="/premier-scanner" className="bg-purple-500 text-white px-4 py-2 rounded hover:bg-purple-600">
                프리미어 스캐너
              </Link>
            </div>
          </div>

          {/* 스캔 실행 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div className="space-y-4">
              <h2 className="text-lg font-semibold">스캔 실행</h2>
              <button
                onClick={runScan}
                disabled={loading}
                className="w-full bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600 disabled:opacity-50"
              >
                {loading ? '실행 중...' : '전체 스캔 실행'}
              </button>
              
              <button
                onClick={loadUniverse}
                disabled={loading}
                className="w-full bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 disabled:opacity-50"
              >
                {loading ? '로딩 중...' : '유니버스 로드'}
              </button>
            </div>

            <div className="space-y-4">
              <h2 className="text-lg font-semibold">개별 분석</h2>
              <div className="flex space-x-2">
                <input
                  type="text"
                  value={q}
                  onChange={(e) => setQ(e.target.value)}
                  placeholder="종목코드 (예: 005930)"
                  className="flex-1 px-3 py-2 border border-gray-300 rounded"
                />
                <button
                  onClick={runAnalyze}
                  disabled={loading}
                  className="bg-indigo-500 text-white px-4 py-2 rounded hover:bg-indigo-600 disabled:opacity-50"
                >
                  분석
                </button>
              </div>
            </div>
          </div>

          {/* 스냅샷 검증 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div className="space-y-4">
              <h2 className="text-lg font-semibold">스냅샷 검증</h2>
              <div className="flex space-x-2">
                <select
                  value={snapAsOf}
                  onChange={(e) => setSnapAsOf(e.target.value)}
                  className="flex-1 px-3 py-2 border border-gray-300 rounded"
                >
                  <option value="">스냅샷 선택</option>
                  {snapshots.map((snap) => (
                    <option key={snap} value={snap}>
                      {snap}
                    </option>
                  ))}
                </select>
                <button
                  onClick={validateFromSnapshot}
                  disabled={loading || !snapAsOf}
                  className="bg-yellow-500 text-white px-4 py-2 rounded hover:bg-yellow-600 disabled:opacity-50"
                >
                  검증
                </button>
              </div>
            </div>

            <div className="space-y-4">
              <h2 className="text-lg font-semibold">설정 관리</h2>
              <button
                onClick={handleConfigReload}
                className="w-full bg-gray-500 text-white px-4 py-2 rounded hover:bg-gray-600"
              >
                설정 재로드
              </button>
            </div>
          </div>

          {/* 카카오톡 알림 */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                수신번호
              </label>
              <input
                type="text"
                value={kakaoTo}
                onChange={(e) => setKakaoTo(e.target.value)}
                placeholder="01012345678"
                className="w-full px-3 py-2 border border-gray-300 rounded"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                상위 N개
              </label>
              <input
                type="number"
                value={kakaoTopN}
                onChange={(e) => setKakaoTopN(parseInt(e.target.value))}
                min="1"
                max="20"
                className="w-full px-3 py-2 border border-gray-300 rounded"
              />
            </div>
            <div className="flex items-end">
              <button
                onClick={sendKakaoAlert}
                className="w-full bg-pink-500 text-white px-4 py-2 rounded hover:bg-pink-600"
              >
                카카오톡 전송
              </button>
            </div>
          </div>
        </div>

        {/* 결과 표시 */}
        {data && (
          <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
            <h2 className="text-xl font-semibold mb-4">스캔 결과</h2>
            <div className="mb-4">
              <span className="text-sm text-gray-600">
                매칭된 종목: {data.matched_count}개 / 전체: {data.universe_count}개
              </span>
            </div>
            <ResultTable data={data} showDetails={showDetails} />
          </div>
        )}

        {analyze && (
          <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
            <h2 className="text-xl font-semibold mb-4">분석 결과: {q}</h2>
            <ResultTable data={analyze} showDetails={showDetails} />
          </div>
        )}

        {universe && (
          <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
            <h2 className="text-xl font-semibold mb-4">유니버스 ({universe.length}개)</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2">
              {universe.map((code) => (
                <span key={code} className="text-sm bg-gray-100 px-2 py-1 rounded">
                  {code}
                </span>
              ))}
            </div>
          </div>
        )}

        {validate && (
          <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
            <h2 className="text-xl font-semibold mb-4">검증 결과: {snapAsOf}</h2>
            <ValidateTable data={validate} />
          </div>
        )}

        {/* 스캔 포지션 */}
        {scanPositions.length > 0 && (
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-xl font-semibold mb-4">스캔 포지션 ({scanPositions.length}개)</h2>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      종목코드
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      종목명
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      수량
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      진입일
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      점수
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {scanPositions.map((pos, index) => (
                    <tr key={index}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {pos.ticker}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {pos.name}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {pos.quantity}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {pos.entry_date}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {pos.score}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}