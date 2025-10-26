import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useAuth } from '../contexts/AuthContext';
import Head from 'next/head';
import { fetchPortfolio } from '../services/portfolioService';
import { calculateHoldingPeriod, formatDate, formatCurrency, formatPercentage } from '../utils/portfolioUtils';
import { handleError } from '../utils/errorHandler';
import Header from '../components/Header';

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
      // 카카오 로그인으로 직접 리다이렉트
      router.push('/login?auto_kakao=true');
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
                </div>
              ))}
            </div>
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
          
          {/* 매매 내역 섹션 */}
          {tradingHistory.length > 0 && (
            <div className="mt-8">
              <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
                📋 매매 내역
                <span className="ml-2 text-sm text-gray-500">({tradingHistory.length}건)</span>
              </h3>
              
              {/* 매매 내역 요약 */}
              <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-4 mb-4">
                <div className="grid grid-cols-3 gap-4 text-center">
                  <div>
                    <div className="text-sm text-gray-600">총 매수금액</div>
                    <div className="text-lg font-semibold text-green-600">
                      {formatCurrency(tradingHistory.reduce((sum, trade) => 
                        trade.trade_type === 'buy' ? sum + (trade.price * trade.quantity) : sum, 0
                      ))}원
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-600">총 매도금액</div>
                    <div className="text-lg font-semibold text-red-600">
                      {formatCurrency(tradingHistory.reduce((sum, trade) => 
                        trade.trade_type === 'sell' ? sum + (trade.price * trade.quantity) : sum, 0
                      ))}원
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-600">실현손익</div>
                    <div className={`text-lg font-semibold ${
                      (() => {
                        // FIFO 방식으로 실현손익 계산
                        const buyTrades = tradingHistory.filter(t => t.trade_type === 'buy').sort((a, b) => new Date(a.trade_date) - new Date(b.trade_date));
                        const sellTrades = tradingHistory.filter(t => t.trade_type === 'sell').sort((a, b) => new Date(a.trade_date) - new Date(b.trade_date));
                        
                        let realizedProfit = 0;
                        let buyIndex = 0;
                        
                        for (const sellTrade of sellTrades) {
                          let remainingSellQty = sellTrade.quantity;
                          
                          while (remainingSellQty > 0 && buyIndex < buyTrades.length) {
                            const buyTrade = buyTrades[buyIndex];
                            const availableQty = buyTrade.quantity;
                            
                            if (availableQty <= remainingSellQty) {
                              // 전체 매수분 매도
                              realizedProfit += (sellTrade.price - buyTrade.price) * availableQty;
                              remainingSellQty -= availableQty;
                              buyIndex++;
                            } else {
                              // 일부 매수분 매도
                              realizedProfit += (sellTrade.price - buyTrade.price) * remainingSellQty;
                              buyTrades[buyIndex].quantity -= remainingSellQty;
                              remainingSellQty = 0;
                            }
                          }
                        }
                        
                        return realizedProfit >= 0 ? 'text-green-600' : 'text-red-600';
                      })()
                    }`}>
                      {formatCurrency(
                        (() => {
                          // FIFO 방식으로 실현손익 계산
                          const buyTrades = tradingHistory.filter(t => t.trade_type === 'buy').sort((a, b) => new Date(a.trade_date) - new Date(b.trade_date));
                          const sellTrades = tradingHistory.filter(t => t.trade_type === 'sell').sort((a, b) => new Date(a.trade_date) - new Date(b.trade_date));
                          
                          let realizedProfit = 0;
                          let buyIndex = 0;
                          
                          for (const sellTrade of sellTrades) {
                            let remainingSellQty = sellTrade.quantity;
                            
                            while (remainingSellQty > 0 && buyIndex < buyTrades.length) {
                              const buyTrade = buyTrades[buyIndex];
                              const availableQty = buyTrade.quantity;
                              
                              if (availableQty <= remainingSellQty) {
                                // 전체 매수분 매도
                                realizedProfit += (sellTrade.price - buyTrade.price) * availableQty;
                                remainingSellQty -= availableQty;
                                buyIndex++;
                              } else {
                                // 일부 매수분 매도
                                realizedProfit += (sellTrade.price - buyTrade.price) * remainingSellQty;
                                buyTrades[buyIndex].quantity -= remainingSellQty;
                                remainingSellQty = 0;
                              }
                            }
                          }
                          
                          return realizedProfit;
                        })()
                      )}원
                    </div>
                  </div>
                </div>
              </div>
              
              <div className="space-y-3">
                {tradingHistory.map((trade) => (
                  <div key={trade.id} className="bg-white rounded-lg shadow-sm border p-4">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center space-x-2">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                          trade.trade_type === 'buy' 
                            ? 'bg-green-100 text-green-800' 
                            : 'bg-red-100 text-red-800'
                        }`}>
                          {trade.trade_type === 'buy' ? '📈 매수' : '📉 매도'}
                        </span>
                        <span className="font-semibold text-gray-800">{trade.name}</span>
                        <span className="text-xs text-gray-500">({trade.ticker})</span>
                      </div>
                      <button
                        onClick={() => deleteTradingHistory(trade.id)}
                        className="text-gray-400 hover:text-red-500 text-sm"
                      >
                        🗑️
                      </button>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-3 text-sm">
                      <div>
                        <span className="text-gray-500">수량:</span>
                        <span className="ml-2 text-gray-800">{trade.quantity}주</span>
                      </div>
                      <div>
                        <span className="text-gray-500">가격:</span>
                        <span className="ml-2 text-gray-800">{formatCurrency(trade.price)}원</span>
                      </div>
                      <div>
                        <span className="text-gray-500">거래일:</span>
                        <span className="ml-2 text-gray-800">{formatDate(trade.trade_date)}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">금액:</span>
                        <span className="ml-2 text-gray-800 font-medium">
                          {formatCurrency(trade.price * trade.quantity)}원
                        </span>
                      </div>
                    </div>
                    
                    {trade.notes && (
                      <div className="mt-2 pt-2 border-t border-gray-100">
                        <span className="text-xs text-gray-500">메모:</span>
                        <span className="ml-2 text-xs text-gray-700">{trade.notes}</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
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
        <div className="fixed bottom-0 left-0 right-0 bg-black text-white">
          <div className="flex justify-around items-center py-2">
            <button 
              className="flex flex-col items-center py-2 hover:bg-gray-800"
              onClick={() => router.push('/customer-scanner')}
            >
              <svg className="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
              </svg>
              <span className="text-xs">추천종목</span>
            </button>
            <button 
              className="flex flex-col items-center py-2 hover:bg-gray-800"
              onClick={() => router.push('/stock-analysis')}
            >
              <svg className="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              <span className="text-xs">종목분석</span>
            </button>
            <button 
              className="flex flex-col items-center py-2 bg-gray-700"
              onClick={() => router.push('/portfolio')}
            >
              <svg className="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
              </svg>
              <span className="text-xs">나의투자종목</span>
            </button>
            {user?.is_admin && (
              <button 
                className="flex flex-col items-center py-2 hover:bg-gray-800"
                onClick={() => router.push('/admin')}
              >
                <svg className="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
                <span className="text-xs">관리자</span>
              </button>
            )}
            <button 
              className="flex flex-col items-center py-2 hover:bg-gray-800"
              onClick={() => router.push('/more')}
            >
              <svg className="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
              </svg>
              <span className="text-xs">더보기</span>
            </button>
          </div>
        </div>

        {/* 하단 네비게이션 공간 확보 */}
        <div className="h-20"></div>
      </div>
    </>
  );
}