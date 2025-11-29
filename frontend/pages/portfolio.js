import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useAuth } from '../contexts/AuthContext';
import Head from 'next/head';
import { fetchPortfolio } from '../services/portfolioService';
import { calculateHoldingPeriod, formatDate, formatCurrency, formatPercentage } from '../utils/portfolioUtils';
import { handleError } from '../utils/errorHandler';
import Header from '../components/v2/Header';
import BottomNavigation from '../components/v2/BottomNavigation';

// 백엔드 URL 설정
const getConfig = () => ({
  backendUrl: process.env.NODE_ENV === 'production' 
    ? 'https://sohntech.ai.kr/api' 
    : 'http://localhost:8000'
});

export default function Portfolio() {
  const router = useRouter();
  const { isAuthenticated, user, loading: authLoading, authChecked, logout } = useAuth();
  const [portfolio, setPortfolio] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // 매매 내역 관련 상태
  const [tradingHistory, setTradingHistory] = useState([]);
  const [showTradingModal, setShowTradingModal] = useState(false);
  const [selectedStock, setSelectedStock] = useState(null);
  const [tradingLoading, setTradingLoading] = useState(false);
  const [tradingForm, setTradingForm] = useState({
    trade_type: 'buy',
    quantity: '',
    price: '',
    trade_date: new Date().toISOString().split('T')[0],
    notes: ''
  });

  useEffect(() => {
    if (!authChecked || authLoading) {
      return;
    }
    
    if (!isAuthenticated()) {
      // 로그인 페이지로 이동 (자동 로그인 없이)
      router.push('/login');
      return;
    }
    
    loadPortfolio();
    loadTradingHistory();
  }, [authChecked, authLoading, isAuthenticated, router]);

  const loadPortfolio = async () => {
    try {
      setLoading(true);
      const data = await fetchPortfolio();
      setPortfolio(data);
    } catch (error) {
      handleError(error, '포트폴리오 로드');
      setPortfolio([]);
    } finally {
      setLoading(false);
    }
  };

  // 매매 내역 관련 함수들
  const loadTradingHistory = async () => {
    try {
      const config = getConfig();
      const base = config.backendUrl;
      const token = localStorage.getItem('token');
      
      const response = await fetch(`${base}/trading-history`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        setTradingHistory(data.items || []);
      }
    } catch (error) {
      console.error('매매 내역 로드 실패:', error);
    }
  };

  const openTradingModal = (stock) => {
    setSelectedStock(stock);
    setTradingForm({
      trade_type: stock.trade_type || 'buy',
      quantity: '',
      price: '',
      trade_date: new Date().toISOString().split('T')[0],
      notes: ''
    });
    setShowTradingModal(true);
  };

  const closeTradingModal = () => {
    setShowTradingModal(false);
    setSelectedStock(null);
  };

  const handleTradingSubmit = async (e) => {
    e.preventDefault();
    if (!selectedStock) return;

    setTradingLoading(true);
    try {
      const config = getConfig();
      const base = config.backendUrl;
      const token = localStorage.getItem('token');

      const response = await fetch(`${base}/trading-history`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ticker: selectedStock.ticker,
          name: selectedStock.name,
          trade_type: tradingForm.trade_type,
          quantity: parseInt(tradingForm.quantity),
          price: parseFloat(tradingForm.price),
          trade_date: tradingForm.trade_date,
          notes: tradingForm.notes
        })
      });

      if (response.ok) {
        alert('매매 내역이 추가되었습니다.');
        closeTradingModal();
        loadPortfolio(); // 포트폴리오 재로드
        loadTradingHistory(); // 매매 내역 재로드
      } else {
        const errorData = await response.json();
        alert(errorData.detail || '매매 내역 추가에 실패했습니다.');
      }
    } catch (error) {
      console.error('매매 내역 추가 실패:', error);
      alert('매매 내역 추가 중 오류가 발생했습니다.');
    } finally {
      setTradingLoading(false);
    }
  };

  const deleteTradingHistory = async (tradingId) => {
    if (!confirm('이 매매 내역을 삭제하시겠습니까?')) return;

    try {
      const config = getConfig();
      const base = config.backendUrl;
      const token = localStorage.getItem('token');

      const response = await fetch(`${base}/trading-history/${tradingId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        alert('매매 내역이 삭제되었습니다.');
        loadPortfolio(); // 포트폴리오 재로드
        loadTradingHistory(); // 매매 내역 재로드
      } else {
        alert('매매 내역 삭제에 실패했습니다.');
      }
    } catch (error) {
      console.error('매매 내역 삭제 실패:', error);
      alert('매매 내역 삭제 중 오류가 발생했습니다.');
    }
  };

  if (!authChecked || authLoading) {
    return (
      <>
        <Head>
          <title>나의투자종목 - Stock Insight</title>
        </Head>
        <div className="min-h-screen bg-gray-50 flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
            <p className="text-gray-600">로딩 중...</p>
          </div>
        </div>
      </>
    );
  }


  return (
    <>
      <Head>
        <title>나의투자종목 - Stock Insight</title>
      </Head>
      
      <div className="min-h-screen bg-gray-50">
        {/* 상단 헤더 */}
        <Header title="Stock Insight" />

        {/* 정보 배너 */}
        <div className="bg-gradient-to-r from-blue-500 to-purple-600 text-white p-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold">나의 투자 종목</h2>
              <p className="text-sm opacity-90">관심 종목의 투자 현황과 수익률을 확인하세요</p>
            </div>
            <div className="w-16 h-16 bg-white bg-opacity-20 rounded-full flex items-center justify-center">
              <span className="text-2xl">📊</span>
            </div>
          </div>
        </div>

        {/* 메인 콘텐츠 */}
        <div className="p-4">
          {loading ? (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
              <p className="text-gray-600">포트폴리오를 불러오는 중...</p>
            </div>
          ) : portfolio.length > 0 ? (
            <>
              {/* 포트폴리오 요약 통계 */}
              <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg p-4 mb-6">
                <h3 className="text-sm font-medium text-gray-600 mb-3">📊 포트폴리오 요약</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-white rounded-lg p-3 shadow-sm">
                    <div className="text-xs text-gray-500 mb-1">총 투자금액</div>
                    <div className="text-lg font-bold text-gray-800">
                      {formatCurrency(
                        (() => {
                          // 매매 내역에서 총 투자금액 계산 (매수만)
                          const buyAmount = tradingHistory.reduce((sum, trade) => 
                            trade.trade_type === 'buy' ? sum + (trade.price * trade.quantity) : sum, 0
                          );
                          
                          // 매매 내역이 없으면 0 반환 (포트폴리오는 매매 내역 기준으로만 계산)
                          return buyAmount;
                        })()
                      )}원
                    </div>
                  </div>
                  <div className="bg-white rounded-lg p-3 shadow-sm">
                    <div className="text-xs text-gray-500 mb-1">평가금액</div>
                    <div className="text-lg font-bold text-gray-800">
                      {formatCurrency(
                        portfolio.reduce((sum, item) => sum + (item.current_price * (item.quantity || 0)), 0)
                      )}원
                    </div>
                  </div>
                  <div className="bg-white rounded-lg p-3 shadow-sm">
                    <div className="text-xs text-gray-500 mb-1">총 손익</div>
                    <div className={`text-lg font-bold ${
                      portfolio.reduce((sum, item) => sum + (item.profit_loss || 0), 0) >= 0 
                        ? 'text-red-600' 
                        : 'text-blue-600'
                    }`}>
                      {formatCurrency(portfolio.reduce((sum, item) => sum + (item.profit_loss || 0), 0))}원
                    </div>
                  </div>
                  <div className="bg-white rounded-lg p-3 shadow-sm">
                    <div className="text-xs text-gray-500 mb-1">총 수익률</div>
                    <div className={`text-lg font-bold ${
                      (() => {
                        // 매매 내역 기반 계산
                        const buyAmount = tradingHistory.reduce((sum, trade) => 
                          trade.trade_type === 'buy' ? sum + (trade.price * trade.quantity) : sum, 0
                        );
                        const totalProfit = portfolio.reduce((sum, item) => sum + (item.profit_loss || 0), 0);
                        const totalReturn = buyAmount > 0 ? (totalProfit / buyAmount * 100) : 0;
                        return totalReturn >= 0 ? 'text-red-600' : 'text-blue-600';
                      })()
                    }`}>
                      {formatPercentage(
                        (() => {
                          const buyAmount = tradingHistory.reduce((sum, trade) => 
                            trade.trade_type === 'buy' ? sum + (trade.price * trade.quantity) : sum, 0
                          );
                          const totalProfit = portfolio.reduce((sum, item) => sum + (item.profit_loss || 0), 0);
                          return buyAmount > 0 ? (totalProfit / buyAmount * 100) : 0;
                        })()
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* 종목 목록 */}
            <div className="space-y-4">
              {portfolio.map((item) => (
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
                  </div>
                  
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <span className="text-gray-500">매수가:</span>
                      <span className="ml-2 text-gray-800">{formatCurrency(item.entry_price)}원</span>
                    </div>
                    <div>
                      <span className="text-gray-500">수량:</span>
                      <span className="ml-2 text-gray-800">{item.quantity || '-'}주</span>
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
                  </div>
                  
                  <div className="mt-3 pt-3 border-t border-gray-200">
                    <div className="grid grid-cols-2 gap-3 text-sm mb-3">
                      <div>
                        <span className="text-gray-500">매수일:</span>
                        <span className="ml-2 text-gray-800">{formatDate(item.entry_date)}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">보유기간:</span>
                        <span className="ml-2 text-gray-800 font-medium">{calculateHoldingPeriod(item.entry_date)}</span>
                      </div>
                    </div>
                    
                    {/* 매매 내역 관리 버튼들 */}
                    <div className="flex space-x-2">
                      <button
                        onClick={() => openTradingModal({...item, trade_type: 'buy'})}
                        className="flex-1 bg-green-500 hover:bg-green-600 text-white text-xs py-2 px-3 rounded-md transition-colors"
                      >
                        📈 추가매수
                      </button>
                      <button
                        onClick={() => openTradingModal({...item, trade_type: 'sell'})}
                        className="flex-1 bg-red-500 hover:bg-red-600 text-white text-xs py-2 px-3 rounded-md transition-colors"
                      >
                        📉 매도
                      </button>
                    </div>
                  </div>

                  {/* 종목별 매매 내역 표시 */}
                  <div className="mt-4 pt-4 border-t border-gray-200">
                    <h4 className="text-sm font-medium text-gray-700 mb-2">📋 매매 내역</h4>
                    {(() => {
                      const itemHistory = tradingHistory.filter(t => t.ticker === item.ticker);
                      if (itemHistory.length === 0) {
                        return (
                          <p className="text-xs text-gray-400 text-center py-2">매매 내역이 없습니다</p>
                        );
                      }
                      
                      return (
                        <div className="space-y-2">
                          {itemHistory.map((trade) => (
                            <div key={trade.id} className="bg-gray-50 rounded p-2 text-xs">
                              <div className="flex items-center justify-between mb-1">
                                <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                                  trade.trade_type === 'buy' 
                                    ? 'bg-green-100 text-green-800' 
                                    : 'bg-red-100 text-red-800'
                                }`}>
                                  {trade.trade_type === 'buy' ? '📈 매수' : '📉 매도'}
                                </span>
                                <span className="text-gray-500">{formatDate(trade.trade_date)}</span>
                              </div>
                              <div className="flex justify-between text-gray-700">
                                <span>{trade.quantity}주 × {formatCurrency(trade.price)}원</span>
                                <span className="font-medium">{formatCurrency(trade.price * trade.quantity)}원</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      );
                    })()}
                  </div>
                </div>
              ))}
            </div>
            </>
          ) : (
            <div className="text-center py-12">
              <div className="text-gray-400 text-6xl mb-4">📊</div>
              <h3 className="text-lg font-medium text-gray-800 mb-2">나의투자종목이 비어있습니다</h3>
              <p className="text-gray-600 mb-6">스캐너에서 관심있는 종목을 투자등록해보세요.</p>
              <a 
                href="/customer-scanner" 
                className="bg-blue-500 text-white px-6 py-2 rounded-lg hover:bg-blue-600"
              >
                스캐너에서 종목 찾기
              </a>
            </div>
          )}

          
          {/* 매매 내역은 각 종목 하위에 표시됨 */}
        </div>

        {/* 매매 내역 모달 */}
        {showTradingModal && selectedStock && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg w-full max-w-md">
              <div className="p-6">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-lg font-semibold text-gray-800">
                    {tradingForm.trade_type === 'buy' ? '📈 추가매수' : '📉 매도'} - {selectedStock.name}
                  </h3>
                  <button
                    onClick={closeTradingModal}
                    className="text-gray-500 hover:text-gray-700"
                  >
                    ✕
                  </button>
                </div>
                
                <form onSubmit={handleTradingSubmit} className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      거래 유형
                    </label>
                    <select
                      value={tradingForm.trade_type}
                      onChange={(e) => setTradingForm({...tradingForm, trade_type: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="buy">매수</option>
                      <option value="sell">매도</option>
                    </select>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      수량 (주)
                    </label>
                    <input
                      type="number"
                      value={tradingForm.quantity}
                      onChange={(e) => setTradingForm({...tradingForm, quantity: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="수량을 입력하세요"
                      required
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      가격 (원)
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      value={tradingForm.price}
                      onChange={(e) => setTradingForm({...tradingForm, price: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="가격을 입력하세요"
                      required
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      거래일
                    </label>
                    <input
                      type="date"
                      value={tradingForm.trade_date}
                      onChange={(e) => setTradingForm({...tradingForm, trade_date: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      required
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      메모 (선택사항)
                    </label>
                    <textarea
                      value={tradingForm.notes}
                      onChange={(e) => setTradingForm({...tradingForm, notes: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      rows={3}
                      placeholder="메모를 입력하세요"
                    />
                  </div>
                  
                  <div className="flex space-x-3 pt-4">
                    <button
                      type="button"
                      onClick={closeTradingModal}
                      className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
                    >
                      취소
                    </button>
                    <button
                      type="submit"
                      disabled={tradingLoading}
                      className={`flex-1 px-4 py-2 rounded-md text-white ${
                        tradingForm.trade_type === 'buy' 
                          ? 'bg-green-500 hover:bg-green-600' 
                          : 'bg-red-500 hover:bg-red-600'
                      } disabled:opacity-50`}
                    >
                      {tradingLoading ? '처리 중...' : '등록'}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </div>
        )}

        {/* 하단 네비게이션 */}
        <BottomNavigation />
      </div>
    </>
  );
}