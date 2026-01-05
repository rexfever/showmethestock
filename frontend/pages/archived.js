// ARCHIVED 추천 전용 화면
import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Head from 'next/head';
import Layout from '../layouts/v2/Layout';
import ArchivedCardV3 from '../components/v3/ArchivedCardV3';

// config는 동적 import로 처리
const getConfig = () => {
  if (typeof window !== 'undefined') {
    // 클라이언트 사이드 - 개발 환경에서는 항상 로컬 백엔드 사용
    const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    const backendUrl = isLocal 
      ? 'http://localhost:8010'
      : (process.env.NEXT_PUBLIC_BACKEND_URL || (process.env.NODE_ENV === 'production' ? 'https://sohntech.ai.kr/api' : 'http://localhost:8010'));
    return { backendUrl };
  } else {
    // 서버 사이드
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8010';
    return { backendUrl };
  }
};

export default function Archived({ initialData }) {
  const router = useRouter();
  const [items, setItems] = useState(initialData || []);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [mounted, setMounted] = useState(false);

  // ARCHIVED 추천 목록 가져오기
  const fetchArchived = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const config = getConfig();
      const base = config?.backendUrl || 'http://localhost:8010';
      
      // 인증 토큰 가져오기
      const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
      const headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
      
      const response = await fetch(`${base}/api/v3/recommendations/archived`, {
        method: 'GET',
        headers: headers,
        mode: 'cors',
        cache: 'no-cache',
        credentials: 'include',
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data.ok && data.data) {
        const archivedItems = data.data.items || [];
        
        // id를 recommendation_id로 정규화
        const normalizedItems = archivedItems.map(item => {
          if (item.id && !item.recommendation_id) {
            item.recommendation_id = item.id;
          }
          return item;
        });
        
        // archive_at desc 정렬 (이미 백엔드에서 정렬되어 있지만, 안전을 위해)
        normalizedItems.sort((a, b) => {
          const dateA = a.archived_at || a.updated_at || a.created_at || '';
          const dateB = b.archived_at || b.updated_at || b.created_at || '';
          return dateB.localeCompare(dateA);
        });
        
        setItems(normalizedItems);
        setError(null);
      } else {
        setError(data.error || 'ARCHIVED 추천 조회 실패');
      }
    } catch (error) {
      console.error('[fetchArchived] 에러:', error);
      setError(`데이터 불러오는 중 오류가 발생했습니다: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setMounted(true);
  }, []);

  // 초기 데이터가 없으면 fetch
  useEffect(() => {
    if (mounted && (!initialData || initialData.length === 0)) {
      fetchArchived();
    }
  }, [mounted, initialData]);

  return (
    <>
      <Head>
        <title>종료된 추천 - Stock Insight</title>
        <meta name="description" content="종료된 추천 목록" />
      </Head>
      <Layout headerTitle="스톡인사이트">
        {/* 정보 배너 */}
        <div className="bg-gradient-to-r from-purple-500 to-pink-600 text-white p-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold">
                종료된 추천
              </h2>
              <p className="text-sm opacity-90">
                종료된 추천 종목의 기록을 확인하세요
              </p>
            </div>
          </div>
        </div>

        {/* 에러 표시 */}
        {error && (
          <div className="mx-4 mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-600 text-sm">{error}</p>
            <button
              onClick={fetchArchived}
              className="mt-2 px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 text-sm"
            >
              다시 시도
            </button>
          </div>
        )}

        {/* 초기 로딩 */}
        {loading && items.length === 0 && (
          <div className="p-4 text-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500 mx-auto"></div>
            <p className="text-gray-500 mt-2">데이터를 불러오는 중...</p>
          </div>
        )}

        {/* ARCHIVED 목록 */}
        {!loading && items.length > 0 && (
          <div className="px-4 py-3 space-y-3">
            {items.map((item) => (
              <ArchivedCardV3 
                key={`${item.ticker}-${item.recommendation_id || item.id || item.anchor_date || ''}`} 
                item={item}
              />
            ))}
          </div>
        )}

        {/* 데이터가 없는 경우 */}
        {!loading && items.length === 0 && !error && (
          <div className="p-4 text-center py-8">
            <p className="text-gray-500 text-lg mb-2">종료된 추천이 없습니다.</p>
          </div>
        )}
      </Layout>
    </>
  );
}

export async function getServerSideProps() {
  try {
    // 서버 사이드에서는 환경 변수 직접 사용
    const base = process.env.BACKEND_URL || (process.env.NODE_ENV === 'production' 
      ? 'https://sohntech.ai.kr/api' 
      : 'http://localhost:8010');
    
    // 타임아웃 설정 (30초)
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000);
    
    const response = await fetch(`${base}/api/v3/recommendations/archived`, {
      headers: { 'Accept': 'application/json' },
      signal: controller.signal
    });
    
    clearTimeout(timeoutId);

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    
    if (data.ok && data.data) {
      const items = data.data.items || [];
      
      // id를 recommendation_id로 정규화
      items.forEach(item => {
        if (item.id && !item.recommendation_id) {
          item.recommendation_id = item.id;
        }
      });
      
      // archive_at desc 정렬
      items.sort((a, b) => {
        const dateA = a.archived_at || a.updated_at || a.created_at || '';
        const dateB = b.archived_at || b.updated_at || b.created_at || '';
        return dateB.localeCompare(dateA);
      });

      return {
        props: {
          initialData: items,
        },
      };
    } else {
      return {
        props: {
          initialData: [],
        },
      };
    }
  } catch (error) {
    console.error('[SSR] 오류:', {
      name: error.name,
      message: error.message
    });
    return {
      props: {
        initialData: [],
      },
    };
  }
}

