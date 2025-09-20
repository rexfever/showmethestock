import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';

export default function Portfolio() {
  const { isAuthenticated, getToken } = useAuth();
  const [portfolio, setPortfolio] = useState(null);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedStatus, setSelectedStatus] = useState('all');
  const [editingItem, setEditingItem] = useState(null);
  const [editForm, setEditForm] = useState({
    entry_price: '',
    quantity: '',
    entry_date: '',
    status: 'watching'
  });

  useEffect(() => {
    if (isAuthenticated()) {
      fetchPortfolio();
      fetchSummary();
    }
  }, [isAuthenticated, selectedStatus]);

  const fetchPortfolio = async () => {
    try {
      setLoading(true);
      const token = getToken();
      const statusParam = selectedStatus === 'all' ? '' : `?status=${selectedStatus}`;
      
      const response = await fetch(`http://localhost:8010/portfolio${statusParam}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error('포트폴리오 조회에 실패했습니다');
      }

      const data = await response.json();
      setPortfolio(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchSummary = async () => {
    try {
      const token = getToken();
      const response = await fetch('http://localhost:8010/portfolio/summary', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        setSummary(data);
      }
    } catch (err) {
      console.error('요약 정보 조회 실패:', err);
    }
  };

  const addToPortfolio = async (ticker, name) => {
    try {
      const token = getToken();
      const response = await fetch('http://localhost:8010/portfolio/add', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          ticker,
          name,
          status: 'watching'
        })
      });

      if (response.ok) {
        fetchPortfolio();
        fetchSummary();
        alert('포트폴리오에 추가되었습니다');
      } else {
        throw new Error('포트폴리오 추가에 실패했습니다');
      }
    } catch (err) {
      alert(err.message);
    }
  };

  const updatePortfolio = async (ticker) => {
    try {
      const token = getToken();
      const response = await fetch(`http://localhost:8010/portfolio/${ticker}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(editForm)
      });

      if (response.ok) {
        setEditingItem(null);
        setEditForm({
          entry_price: '',
          quantity: '',
          entry_date: '',
          status: 'watching'
        });
        fetchPortfolio();
        fetchSummary();
        alert('포트폴리오가 업데이트되었습니다');
      } else {
        throw new Error('포트폴리오 업데이트에 실패했습니다');
      }
    } catch (err) {
      alert(err.message);
    }
  };

  const removeFromPortfolio = async (ticker) => {
    if (!confirm('정말로 포트폴리오에서 제거하시겠습니까?')) {
      return;
    }

    try {
      const token = getToken();
      const response = await fetch(`http://localhost:8010/portfolio/${ticker}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        fetchPortfolio();
        fetchSummary();
        alert('포트폴리오에서 제거되었습니다');
      } else {
        throw new Error('포트폴리오 제거에 실패했습니다');
      }
    } catch (err) {
      alert(err.message);
    }
  };

  const startEdit = (item) => {
    setEditingItem(item.ticker);
    setEditForm({
      entry_price: item.entry_price || '',
      quantity: item.quantity || '',
      entry_date: item.entry_date || '',
      status: item.status
    });
  };

  const cancelEdit = () => {
    setEditingItem(null);
    setEditForm({
      entry_price: '',
      quantity: '',
      entry_date: '',
      status: 'watching'
    });
  };

  const formatCurrency = (amount) => {
    if (!amount) return '-';
    return new Intl.NumberFormat('ko-KR').format(Math.round(amount));
  };

  const formatPercentage = (percentage) => {
    if (!percentage) return '-';
    return `${percentage > 0 ? '+' : ''}${percentage.toFixed(2)}%`;
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'watching': return 'bg-blue-100 text-blue-800';
      case 'holding': return 'bg-green-100 text-green-800';
      case 'sold': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusText = (status) => {
    switch (status) {
      case 'watching': return '관심종목';
      case 'holding': return '보유중';
      case 'sold': return '매도완료';
      default: return status;
    }
  };

  if (!isAuthenticated()) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-800 mb-4">로그인이 필요합니다</h2>
          <p className="text-gray-600 mb-6">포트폴리오를 관리하려면 로그인해주세요.</p>
          <a href="/login" className="bg-blue-500 text-white px-6 py-2 rounded-lg hover:bg-blue-600">
            로그인하기
          </a>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600">포트폴리오를 불러오는 중...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-red-600 mb-4">오류가 발생했습니다</h2>
          <p className="text-gray-600 mb-6">{error}</p>
          <button 
            onClick={() => window.location.reload()} 
            className="bg-blue-500 text-white px-6 py-2 rounded-lg hover:bg-blue-600"
          >
            다시 시도
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 헤더 */}
      <div className="bg-white shadow-sm">
        <div className="flex items-center justify-between p-4">
          <div className="flex items-center">
            <span className="text-lg font-semibold text-gray-800">포트폴리오</span>
          </div>
          <div className="flex items-center space-x-3">
            <a href="/customer-scanner" className="text-blue-500 hover:text-blue-700">
              스캐너로 돌아가기
            </a>
          </div>
        </div>
      </div>

      {/* 요약 정보 */}
      {summary && (
        <div className="bg-white border-b p-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">{summary.total_items}</div>
              <div className="text-sm text-gray-600">총 종목</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">{summary.holding_count}</div>
              <div className="text-sm text-gray-600">보유중</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">{summary.watching_count}</div>
              <div className="text-sm text-gray-600">관심종목</div>
            </div>
            <div className="text-center">
              <div className={`text-2xl font-bold ${summary.total_profit_loss_pct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {formatPercentage(summary.total_profit_loss_pct)}
              </div>
              <div className="text-sm text-gray-600">총 수익률</div>
            </div>
          </div>
        </div>
      )}

      {/* 필터 */}
      <div className="bg-white border-b p-4">
        <div className="flex space-x-2">
          <button
            onClick={() => setSelectedStatus('all')}
            className={`px-4 py-2 rounded-lg text-sm font-medium ${
              selectedStatus === 'all' 
                ? 'bg-blue-500 text-white' 
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            전체
          </button>
          <button
            onClick={() => setSelectedStatus('watching')}
            className={`px-4 py-2 rounded-lg text-sm font-medium ${
              selectedStatus === 'watching' 
                ? 'bg-blue-500 text-white' 
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            관심종목
          </button>
          <button
            onClick={() => setSelectedStatus('holding')}
            className={`px-4 py-2 rounded-lg text-sm font-medium ${
              selectedStatus === 'holding' 
                ? 'bg-blue-500 text-white' 
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            보유중
          </button>
          <button
            onClick={() => setSelectedStatus('sold')}
            className={`px-4 py-2 rounded-lg text-sm font-medium ${
              selectedStatus === 'sold' 
                ? 'bg-blue-500 text-white' 
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            매도완료
          </button>
        </div>
      </div>

      {/* 포트폴리오 목록 */}
      <div className="p-4 space-y-4">
        {portfolio && portfolio.items.length > 0 ? (
          portfolio.items.map((item) => (
            <div key={item.id} className="bg-white rounded-lg shadow-sm border p-4">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <div className="font-semibold text-gray-800">
                    {item.name}
                    <span className="text-xs text-gray-500 ml-2">({item.ticker})</span>
                  </div>
                  <div className="text-sm text-gray-600">
                    현재가: {formatCurrency(item.current_price)}원
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(item.status)}`}>
                    {getStatusText(item.status)}
                  </span>
                  <button
                    onClick={() => removeFromPortfolio(item.ticker)}
                    className="text-red-500 hover:text-red-700 text-sm"
                  >
                    삭제
                  </button>
                </div>
              </div>

              {editingItem === item.ticker ? (
                <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 mb-3">
                  <div className="grid grid-cols-2 gap-3 mb-3">
                    <div>
                      <label className="block text-xs text-gray-600 mb-1">매수가</label>
                      <input
                        type="number"
                        value={editForm.entry_price}
                        onChange={(e) => setEditForm({...editForm, entry_price: e.target.value})}
                        className="w-full p-2 border border-gray-300 rounded text-sm"
                        placeholder="매수가 입력"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-gray-600 mb-1">수량</label>
                      <input
                        type="number"
                        value={editForm.quantity}
                        onChange={(e) => setEditForm({...editForm, quantity: e.target.value})}
                        className="w-full p-2 border border-gray-300 rounded text-sm"
                        placeholder="수량 입력"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-gray-600 mb-1">매수일</label>
                      <input
                        type="date"
                        value={editForm.entry_date}
                        onChange={(e) => setEditForm({...editForm, entry_date: e.target.value})}
                        className="w-full p-2 border border-gray-300 rounded text-sm"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-gray-600 mb-1">상태</label>
                      <select
                        value={editForm.status}
                        onChange={(e) => setEditForm({...editForm, status: e.target.value})}
                        className="w-full p-2 border border-gray-300 rounded text-sm"
                      >
                        <option value="watching">관심종목</option>
                        <option value="holding">보유중</option>
                        <option value="sold">매도완료</option>
                      </select>
                    </div>
                  </div>
                  <div className="flex space-x-2">
                    <button
                      onClick={() => updatePortfolio(item.ticker)}
                      className="px-4 py-2 bg-blue-500 text-white rounded text-sm hover:bg-blue-600"
                    >
                      저장
                    </button>
                    <button
                      onClick={cancelEdit}
                      className="px-4 py-2 bg-gray-300 text-gray-700 rounded text-sm hover:bg-gray-400"
                    >
                      취소
                    </button>
                  </div>
                </div>
              ) : (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm mb-3">
                  <div>
                    <span className="text-gray-500">매수가:</span>
                    <span className="ml-2 text-gray-800">{formatCurrency(item.entry_price)}원</span>
                  </div>
                  <div>
                    <span className="text-gray-500">수량:</span>
                    <span className="ml-2 text-gray-800">{item.quantity ? `${item.quantity}주` : '-'}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">총 투자금:</span>
                    <span className="ml-2 text-gray-800">{formatCurrency(item.total_investment)}원</span>
                  </div>
                  <div>
                    <span className="text-gray-500">현재 평가금액:</span>
                    <span className="ml-2 text-gray-800">{formatCurrency(item.current_value)}원</span>
                  </div>
                  <div>
                    <span className="text-gray-500">손익:</span>
                    <span className={`ml-2 ${item.profit_loss >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {formatCurrency(item.profit_loss)}원
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-500">수익률:</span>
                    <span className={`ml-2 ${item.profit_loss_pct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {formatPercentage(item.profit_loss_pct)}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-500">매수일:</span>
                    <span className="ml-2 text-gray-800">{item.entry_date || '-'}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">등록일:</span>
                    <span className="ml-2 text-gray-800">
                      {item.created_at ? new Date(item.created_at).toLocaleDateString() : '-'}
                    </span>
                  </div>
                </div>
              )}

              <div className="flex items-center justify-between pt-3 border-t">
                <div className="flex space-x-4 text-sm">
                  <button className="text-blue-500 hover:text-blue-700">차트</button>
                  <button className="text-blue-500 hover:text-blue-700">기업정보</button>
                </div>
                <button
                  onClick={() => startEdit(item)}
                  className="px-4 py-2 bg-gray-500 text-white rounded-lg text-sm font-medium hover:bg-gray-600"
                >
                  {editingItem === item.ticker ? '편집중' : '편집'}
                </button>
              </div>
            </div>
          ))
        ) : (
          <div className="text-center py-12">
            <div className="text-gray-400 text-6xl mb-4">📊</div>
            <h3 className="text-lg font-medium text-gray-800 mb-2">포트폴리오가 비어있습니다</h3>
            <p className="text-gray-600 mb-6">관심있는 종목을 포트폴리오에 추가해보세요.</p>
            <a 
              href="/customer-scanner" 
              className="bg-blue-500 text-white px-6 py-2 rounded-lg hover:bg-blue-600"
            >
              스캐너에서 종목 찾기
            </a>
          </div>
        )}
      </div>
    </div>
  );
}
