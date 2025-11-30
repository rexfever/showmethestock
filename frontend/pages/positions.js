import { useState, useEffect } from 'react';
import { fetchPositions, addPosition, updatePosition, deletePosition } from '../lib/api';

export default function PositionsPage() {
  const [positions, setPositions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newPosition, setNewPosition] = useState({
    ticker: '',
    entry_date: new Date().toISOString().split('T')[0],
    entry_price: '',
    quantity: ''
  });
  const [editingPosition, setEditingPosition] = useState(null);
  const [exitForm, setExitForm] = useState({
    exit_date: new Date().toISOString().split('T')[0],
    exit_price: ''
  });

  const loadPositions = async () => {
    setLoading(true);
    try {
      const data = await fetchPositions();
      setPositions(data.items || []);
    } catch (e) {
      console.error('Failed to load positions:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPositions();
  }, []);

  const handleAddPosition = async () => {
    if (!newPosition.ticker || !newPosition.entry_price || !newPosition.quantity) {
      alert('모든 필드를 입력해주세요.');
      return;
    }

    setLoading(true);
    try {
      const result = await addPosition(newPosition);
      if (result.ok) {
        setNewPosition({ ticker: '', entry_date: new Date().toISOString().split('T')[0], entry_price: '', quantity: '' });
        setShowAddForm(false);
        loadPositions();
      } else {
        alert('포지션 추가 실패: ' + result.error);
      }
    } catch (e) {
      alert('포지션 추가 오류: ' + String(e));
    } finally {
      setLoading(false);
    }
  };

  const handleExitPosition = async (positionId) => {
    if (!exitForm.exit_price) {
      alert('청산가를 입력해주세요.');
      return;
    }

    setLoading(true);
    try {
      const result = await updatePosition(positionId, exitForm);
      if (result.ok) {
        setEditingPosition(null);
        setExitForm({ exit_date: new Date().toISOString().split('T')[0], exit_price: '' });
        loadPositions();
      } else {
        alert('청산 처리 실패: ' + result.error);
      }
    } catch (e) {
      alert('청산 처리 오류: ' + String(e));
    } finally {
      setLoading(false);
    }
  };

  const handleDeletePosition = async (positionId) => {
    if (!confirm('정말 삭제하시겠습니까?')) return;

    setLoading(true);
    try {
      const result = await deletePosition(positionId);
      if (result.ok) {
        loadPositions();
      } else {
        alert('삭제 실패: ' + result.error);
      }
    } catch (e) {
      alert('삭제 오류: ' + String(e));
    } finally {
      setLoading(false);
    }
  };

  const totalReturnAmount = positions.reduce((sum, p) => sum + (p.return_amount || 0), 0);
  const totalReturnPct = positions.length > 0 ? 
    positions.reduce((sum, p) => sum + (p.return_pct || 0), 0) / positions.length : 0;

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">포지션 관리</h1>
        <button
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          onClick={() => setShowAddForm(!showAddForm)}
        >
          {showAddForm ? '취소' : '포지션 추가'}
        </button>
      </div>

      {/* 요약 정보 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white p-4 rounded shadow">
          <div className="text-sm text-gray-600">총 포지션</div>
          <div className="text-2xl font-bold">{positions.length}개</div>
        </div>
        <div className="bg-white p-4 rounded shadow">
          <div className="text-sm text-gray-600 mb-1">총 수익률</div>
          <div className={`text-2xl font-bold ${totalReturnPct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {totalReturnPct.toFixed(2)}%
          </div>
          {/* 목표 달성 여부 표시 */}
          {totalReturnPct !== null && totalReturnPct !== undefined && (
            (() => {
              const targetReturn = 5.0; // 기본 목표 수익률 5%
              const isAchieved = totalReturnPct >= targetReturn;
              const progress = Math.min((totalReturnPct / targetReturn) * 100, 100);
              return (
                <div className="mt-2">
                  <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                    <span>목표: {targetReturn}%</span>
                    <span className={isAchieved ? 'text-green-600 font-semibold' : 'text-gray-500'}>
                      {isAchieved ? '✅ 달성' : `${(targetReturn - totalReturnPct).toFixed(2)}% 남음`}
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-1.5">
                    <div 
                      className={`h-1.5 rounded-full transition-all ${isAchieved ? 'bg-green-500' : 'bg-blue-500'}`}
                      style={{ width: `${Math.max(0, progress)}%` }}
                    />
                  </div>
                </div>
              );
            })()
          )}
        </div>
        <div className="bg-white p-4 rounded shadow">
          <div className="text-sm text-gray-600">총 수익금</div>
          <div className={`text-2xl font-bold ${totalReturnAmount >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {totalReturnAmount.toLocaleString()}원
          </div>
        </div>
      </div>

      {/* 포지션 추가 폼 */}
      {showAddForm && (
        <div className="bg-white p-4 rounded shadow">
          <h3 className="text-lg font-semibold mb-4">새 포지션 추가</h3>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <input
              className="border rounded px-3 py-2"
              placeholder="종목코드 (예: 005930)"
              value={newPosition.ticker}
              onChange={(e) => setNewPosition({...newPosition, ticker: e.target.value})}
            />
            <input
              type="date"
              className="border rounded px-3 py-2"
              value={newPosition.entry_date}
              onChange={(e) => setNewPosition({...newPosition, entry_date: e.target.value})}
            />
            <input
              type="number"
              className="border rounded px-3 py-2"
              placeholder="진입가"
              value={newPosition.entry_price}
              onChange={(e) => setNewPosition({...newPosition, entry_price: e.target.value})}
            />
            <input
              type="number"
              className="border rounded px-3 py-2"
              placeholder="수량"
              value={newPosition.quantity}
              onChange={(e) => setNewPosition({...newPosition, quantity: e.target.value})}
            />
          </div>
          <div className="mt-4 flex gap-2">
            <button
              className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
              onClick={handleAddPosition}
              disabled={loading}
            >
              추가
            </button>
            <button
              className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
              onClick={() => setShowAddForm(false)}
            >
              취소
            </button>
          </div>
        </div>
      )}

      {/* 포지션 목록 */}
      <div className="bg-white rounded shadow overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead className="bg-gray-100">
              <tr>
                <th className="p-3 text-left">종목</th>
                <th className="p-3 text-left">진입일</th>
                <th className="p-3 text-left">수량</th>
                <th className="p-3 text-left">점수(당시)</th>
                <th className="p-3 text-left">전략(당시)</th>
                <th className="p-3 text-left">현재 수익률(%)</th>
                <th className="p-3 text-left">기간내 최대 수익률(%)</th>
                <th className="p-3 text-left">상태</th>
                <th className="p-3 text-left">액션</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((position) => (
                <tr key={position.id} className="border-t">
                  <td className="p-3">
                    <div>
                      <div className="font-medium">{position.name}</div>
                      <div className="text-sm text-gray-500">({position.ticker})</div>
                    </div>
                  </td>
                  <td className="p-3">{position.entry_date}</td>
                  <td className="p-3">{position.quantity}주</td>
                  <td className="p-3">
                    {position.score !== null ? position.score : '-'}
                  </td>
                  <td className="p-3">
                    {position.strategy || '-'}
                  </td>
                  <td className="p-3">
                    {position.current_return_pct !== null ? (
                      <div>
                        <span className={position.current_return_pct >= 0 ? 'text-green-600' : 'text-red-600'}>
                          {position.current_return_pct.toFixed(2)}%
                        </span>
                        {/* 목표 달성 여부 표시 */}
                        {position.current_return_pct !== null && position.current_return_pct !== undefined && (
                          (() => {
                            const targetReturn = 5.0; // 기본 목표 수익률 5%
                            const isAchieved = position.current_return_pct >= targetReturn;
                            return (
                              <div className="text-xs mt-1">
                                <span className={isAchieved ? 'text-green-600 font-semibold' : 'text-gray-500'}>
                                  {isAchieved ? '✅ 목표 달성' : `목표까지 ${(targetReturn - position.current_return_pct).toFixed(2)}%`}
                                </span>
                              </div>
                            );
                          })()
                        )}
                      </div>
                    ) : '-'}
                  </td>
                  <td className="p-3">
                    {position.max_return_pct !== null ? (
                      <span className={position.max_return_pct >= 0 ? 'text-green-600' : 'text-red-600'}>
                        {position.max_return_pct.toFixed(2)}%
                      </span>
                    ) : '-'}
                  </td>
                  <td className="p-3">
                    <span className={`px-2 py-1 rounded text-xs ${
                      position.status === 'open' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                    }`}>
                      {position.status === 'open' ? '보유중' : '청산완료'}
                    </span>
                  </td>
                  <td className="p-3">
                    <div className="flex gap-2">
                      {position.status === 'open' && (
                        <button
                          className="px-2 py-1 bg-red-600 text-white rounded text-xs hover:bg-red-700"
                          onClick={() => setEditingPosition(position.id)}
                        >
                          청산
                        </button>
                      )}
                      <button
                        className="px-2 py-1 bg-gray-600 text-white rounded text-xs hover:bg-gray-700"
                        onClick={() => handleDeletePosition(position.id)}
                      >
                        삭제
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 청산 모달 */}
      {editingPosition && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded shadow-lg w-96">
            <h3 className="text-lg font-semibold mb-4">포지션 청산</h3>
            <div className="space-y-4">
              <input
                type="date"
                className="w-full border rounded px-3 py-2"
                value={exitForm.exit_date}
                onChange={(e) => setExitForm({...exitForm, exit_date: e.target.value})}
              />
              <input
                type="number"
                className="w-full border rounded px-3 py-2"
                placeholder="청산가"
                value={exitForm.exit_price}
                onChange={(e) => setExitForm({...exitForm, exit_price: e.target.value})}
              />
            </div>
            <div className="mt-6 flex gap-2">
              <button
                className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
                onClick={() => handleExitPosition(editingPosition)}
                disabled={loading}
              >
                청산 처리
              </button>
              <button
                className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
                onClick={() => {
                  setEditingPosition(null);
                  setExitForm({ exit_date: new Date().toISOString().split('T')[0], exit_price: '' });
                }}
              >
                취소
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
