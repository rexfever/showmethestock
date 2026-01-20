import { useEffect, useMemo, useState } from 'react';
import Head from 'next/head';
import Layout from '../../layouts/v2/Layout';

const getConfig = () => {
  if (typeof window !== 'undefined') {
    const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    const backendUrl = isLocal
      ? 'http://localhost:8010'
      : (process.env.NEXT_PUBLIC_BACKEND_URL || (process.env.NODE_ENV === 'production' ? 'https://sohntech.ai.kr/api' : 'http://localhost:8010'));
    return { backendUrl };
  }
  const backendUrl = process.env.BACKEND_URL || 'http://localhost:8010';
  return { backendUrl };
};

const TABS = [
  { key: 'new', label: '신규 추천' },
  { key: 'archived', label: '종료' },
  { key: 'repeat', label: '재추천' }
];

const formatWeekRange = (weekStart, weekEnd) => {
  if (!weekStart || !weekEnd) return '';
  const format = (dateStr) => {
    const base = String(dateStr).split('T')[0];
    const parts = base.split('-');
    if (parts.length < 3) return '';
    const month = Number(parts[1]);
    const day = Number(parts[2]);
    if (!month || !day) return '';
    return `${month}/${day}`;
  };
  const startLabel = format(weekStart);
  const endLabel = format(weekEnd);
  if (!startLabel || !endLabel) return '';
  return `${startLabel}–${endLabel}`;
};

const formatDate = (dateStr) => {
  if (!dateStr) return '';
  const base = String(dateStr).split('T')[0];
  return base;
};

export default function WeeklySummary() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);
  const [activeTab, setActiveTab] = useState('new');
  
  useEffect(() => {
    let isMounted = true;
    const fetchDetail = async () => {
      setLoading(true);
      setError(null);
      try {
        const config = getConfig();
        const base = config?.backendUrl || 'http://localhost:8010';
        const response = await fetch(`${base}/api/v3/recommendations/weekly-detail`, {
          method: 'GET',
          headers: { 'Accept': 'application/json' }
        });
        if (!response.ok) {
          throw new Error(`HTTP error: ${response.status}`);
        }
        const payload = await response.json();
        if (payload.ok && isMounted) {
          setData(payload.data);
        } else if (isMounted) {
          setError(payload.error || payload.message || '주간 데이터 조회 실패');
        }
      } catch (fetchError) {
        if (isMounted) {
          setError(fetchError.message || '주간 데이터 조회 실패');
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };
    fetchDetail();
    return () => { isMounted = false; };
  }, []);
  
  const items = useMemo(() => {
    if (!data) return [];
    if (activeTab === 'new') return data.new_items || [];
    if (activeTab === 'archived') return data.archived_items || [];
    if (activeTab === 'repeat') return data.repeat_items || [];
    return [];
  }, [data, activeTab]);
  
  return (
    <>
      <Head>
        <title>주간 추천 현황</title>
      </Head>
      <Layout headerTitle="주간 추천 현황">
        <div className="px-4 py-4">
          <div className="bg-white border border-gray-200 rounded-[14px] p-5 shadow-sm">
            <div className="flex items-baseline justify-between">
              <div className="text-lg text-[#111827]">주간 추천 현황</div>
              <div className="text-xs text-[#6B7280]">
                {data ? formatWeekRange(data.week_start, data.week_end) : ''}
              </div>
            </div>
            <div className="text-xs text-[#6B7280] mt-1">월–금 기준 유니크 종목 리스트</div>
          </div>
        </div>
        
        <div className="px-4">
          <div className="flex gap-2">
            {TABS.map((tab) => (
              <button
                key={tab.key}
                type="button"
                onClick={() => setActiveTab(tab.key)}
                className={`px-3 py-2 rounded-full text-sm ${
                  activeTab === tab.key
                    ? 'bg-indigo-600 text-white'
                    : 'bg-gray-100 text-gray-700'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
        
        {loading && (
          <div className="px-4 py-6 text-center text-sm text-gray-500">
            불러오는 중...
          </div>
        )}
        
        {error && !loading && (
          <div className="mx-4 mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-600 text-sm">{error}</p>
          </div>
        )}
        
        {!loading && !error && (
          <div className="px-4 py-4">
            {items.length > 0 ? (
              <div className="space-y-2">
                {items.map((item) => (
                  <div
                    key={`${item.recommendation_id}-${item.ticker}`}
                    className="bg-white border border-gray-200 rounded-[12px] px-4 py-3"
                  >
                    <div className="flex items-center justify-between">
                      <div className="text-sm font-medium text-[#111827]">
                        {item.name || item.ticker}
                      </div>
                      <div className="text-xs text-[#6B7280]">
                        {formatDate(item.occurred_at)}
                      </div>
                    </div>
                    <div className="text-xs text-[#6B7280] mt-1">
                      추천일: {formatDate(item.anchor_date)}
                      {item.reason_code ? ` · 사유: ${item.reason_code}` : ''}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center text-sm text-gray-500 py-6">
                이번 주 항목이 없습니다
              </div>
            )}
          </div>
        )}
      </Layout>
    </>
  );
}
