/**
 * v3 종목 상세 화면 컴포넌트
 * 
 * 기능:
 * - 추천 기준 종가(기준점) 표시
 * - 개인 매수가 입력/수정/삭제
 */

import { useState, useEffect, useRef } from 'react';
import { getPersonalBuyPrice, savePersonalBuyPrice, deletePersonalBuyPrice } from '../../services/positionService';
import { ackRecommendation } from '../../services/ackService';

export default function StockDetailV3({ item, analysisResult, onAckComplete }) {
  const [personalBuyPrice, setPersonalBuyPrice] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  
  // ack 호출 추적 (1회만 호출)
  const ackCalledRef = useRef(false);

  // anchor 정보 추출 (analysisResult 우선, 없으면 item)
  const anchorDate = analysisResult?.anchor_date || item?.anchor_date || null;
  const anchorClose = analysisResult?.anchor_close || item?.anchor_close || null;
  const ticker = analysisResult?.ticker || item?.ticker || null;
  const market = analysisResult?.market || item?.market || 'KRX'; // 기본값: 한국
  
  // 추천 인스턴스 정보 추출 (ack용)
  // query parameter에서 우선, 없으면 analysisResult/item에서 추출
  const recDate = (typeof window !== 'undefined' && new URLSearchParams(window.location.search).get('rec_date')) 
    || analysisResult?.recommended_date 
    || item?.recommended_date 
    || item?.date 
    || null;
  const recCode = ticker;
  const status = analysisResult?.status || item?.status || null;
  const scannerVersion = (typeof window !== 'undefined' && new URLSearchParams(window.location.search).get('rec_version'))
    || analysisResult?.scanner_version 
    || item?.scanner_version 
    || 'v3';

  // BROKEN 상세 진입 시 자동 ack 호출 (1회만)
  useEffect(() => {
    if (status === 'BROKEN' && recDate && recCode && !ackCalledRef.current) {
      ackCalledRef.current = true;
      
      // 비동기로 ack 호출 (UX를 막지 않음)
      ackRecommendation(recDate, recCode, scannerVersion, 'BROKEN_VIEWED')
        .then(result => {
          if (result.success) {
            console.log('[StockDetailV3] ack 성공:', { recDate, recCode });
            if (onAckComplete) {
              onAckComplete();
            }
          } else {
            console.warn('[StockDetailV3] ack 실패:', result.error);
            // 실패해도 UX를 막지 않음, 다음 방문 시 다시 시도
            ackCalledRef.current = false; // 재시도 가능하도록
          }
        })
        .catch(err => {
          console.error('[StockDetailV3] ack 오류:', err);
          ackCalledRef.current = false; // 재시도 가능하도록
        });
    }
  }, [status, recDate, recCode, scannerVersion]);

  // 개인 매수가 조회
  useEffect(() => {
    if (ticker) {
      loadPersonalBuyPrice();
    }
  }, [ticker]);

  const loadPersonalBuyPrice = async () => {
    if (!ticker) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      const result = await getPersonalBuyPrice(ticker);
      setPersonalBuyPrice(result.avg_buy_price);
    } catch (err) {
      console.error('[StockDetailV3] loadPersonalBuyPrice error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  // 수정 모드 시작
  const handleEdit = () => {
    setIsEditing(true);
    setEditValue(personalBuyPrice ? String(personalBuyPrice) : '');
    setError(null);
    setSuccessMessage(null);
  };

  // 저장
  const handleSave = async () => {
    if (!ticker) return;
    
    const price = parseFloat(editValue);
    if (isNaN(price) || price <= 0) {
      setError('올바른 가격을 입력해주세요.');
      return;
    }

    setIsLoading(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const result = await savePersonalBuyPrice(ticker, price);
      if (result.success) {
        setPersonalBuyPrice(price);
        setIsEditing(false);
        setEditValue('');
        setSuccessMessage('저장되었습니다.');
        setTimeout(() => setSuccessMessage(null), 3000);
      } else {
        setError(result.error || '저장에 실패했습니다.');
      }
    } catch (err) {
      console.error('[StockDetailV3] savePersonalBuyPrice error:', err);
      setError('저장 중 오류가 발생했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  // 삭제
  const handleDelete = async () => {
    if (!ticker) return;
    
    if (!confirm('개인 매수가를 삭제하시겠습니까?')) {
      return;
    }

    setIsLoading(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const result = await deletePersonalBuyPrice(ticker);
      if (result.success) {
        setPersonalBuyPrice(null);
        setIsEditing(false);
        setEditValue('');
        setSuccessMessage('삭제되었습니다.');
        setTimeout(() => setSuccessMessage(null), 3000);
      } else {
        setError(result.error || '삭제에 실패했습니다.');
      }
    } catch (err) {
      console.error('[StockDetailV3] deletePersonalBuyPrice error:', err);
      setError('삭제 중 오류가 발생했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  // 취소
  const handleCancel = () => {
    setIsEditing(false);
    setEditValue('');
    setError(null);
    setSuccessMessage(null);
  };

  // 통화 포맷
  const formatCurrency = (price) => {
    if (!price || isNaN(price)) return '';
    const currency = market === 'US' ? 'USD' : '원';
    if (currency === 'USD') {
      return `$${price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    }
    return `${price.toLocaleString('ko-KR')}${currency}`;
  };

  // 날짜 포맷
  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    // YYYYMMDD 또는 YYYY-MM-DD 형식 처리
    const normalized = String(dateStr).replace(/-/g, '');
    if (normalized.length === 8) {
      const year = normalized.slice(0, 4);
      const month = normalized.slice(4, 6);
      const day = normalized.slice(6, 8);
      return `${year}-${month}-${day}`;
    }
    return dateStr;
  };

  return (
    <div className="space-y-6">
      {/* 추천 기준 종가(기준점) 섹션 */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">추천 기준 종가(기준점)</h3>
        {anchorDate && anchorClose ? (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">기준일</span>
              <span className="text-base font-medium text-gray-900">{formatDate(anchorDate)}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">기준가</span>
              <span className="text-base font-medium text-gray-900">{formatCurrency(anchorClose)}</span>
            </div>
          </div>
        ) : (
          <p className="text-sm text-gray-500">기준점 정보가 없습니다</p>
        )}
      </div>

      {/* 개인 매수가 섹션 */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">내 매수가(개인 참고)</h3>
        
        {!isEditing ? (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-base text-gray-700">
                {personalBuyPrice ? formatCurrency(personalBuyPrice) : '미입력'}
              </span>
              <div className="flex space-x-2">
                {personalBuyPrice ? (
                  <>
                    <button
                      onClick={handleEdit}
                      disabled={isLoading}
                      className="px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100 disabled:opacity-50"
                    >
                      수정
                    </button>
                    <button
                      onClick={handleDelete}
                      disabled={isLoading}
                      className="px-4 py-2 text-sm font-medium text-red-600 bg-red-50 rounded-lg hover:bg-red-100 disabled:opacity-50"
                    >
                      삭제
                    </button>
                  </>
                ) : (
                  <button
                    onClick={handleEdit}
                    disabled={isLoading}
                    className="px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100 disabled:opacity-50"
                  >
                    입력
                  </button>
                )}
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div>
              <input
                type="number"
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                placeholder="매수가를 입력하세요"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                step="0.01"
                min="0"
              />
            </div>
            <div className="flex space-x-2">
              <button
                onClick={handleSave}
                disabled={isLoading || !editValue}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                저장
              </button>
              <button
                onClick={handleCancel}
                disabled={isLoading}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 disabled:opacity-50"
              >
                취소
              </button>
            </div>
          </div>
        )}

        {/* 고정 문구 */}
        <div className="mt-4 pt-4 border-t border-gray-200">
          <p className="text-xs text-gray-500">
            개인 참고용이며 추천 판단과 무관합니다
          </p>
        </div>

        {/* 에러/성공 메시지 */}
        {error && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}
        {successMessage && (
          <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-md">
            <p className="text-sm text-green-600">{successMessage}</p>
          </div>
        )}
      </div>
    </div>
  );
}

