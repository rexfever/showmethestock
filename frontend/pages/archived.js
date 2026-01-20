// ARCHIVED 추천 전용 화면
import { useState, useEffect, useMemo } from 'react';
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
  const [allItems, setAllItems] = useState(initialData || []); // 전체 데이터 (검색용)
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [mounted, setMounted] = useState(false);
  const [searchQuery, setSearchQuery] = useState(''); // 검색어
  const [sortType, setSortType] = useState('date_desc'); // 정렬 타입: 'date_desc' | 'date_asc' | 'name_asc' | 'name_desc'
  const [isSearchConfirmed, setIsSearchConfirmed] = useState(false); // 검색 확정 여부

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
        
        setAllItems(normalizedItems);
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

  // 기본 리스트: 모든 ARCHIVED 데이터 표시 및 정렬
  const defaultItems = useMemo(() => {
    if (!allItems || allItems.length === 0) return [];
    
    // 1개월 필터링 제거: 모든 ARCHIVED 항목 표시
    const filtered = allItems.filter(item => {
      // archived_at이 없는 항목은 제외
      const archivedDate = item.archived_at || item.updated_at || item.created_at;
      return !!archivedDate;
    });
    
    // 정렬 적용
    return filtered.sort((a, b) => {
      if (sortType === 'date_desc' || sortType === 'date_asc') {
        // 종료일 기준 정렬
        const dateA = a.archived_at || a.updated_at || a.created_at || '';
        const dateB = b.archived_at || b.updated_at || b.created_at || '';
        if (sortType === 'date_desc') {
          return dateB.localeCompare(dateA); // 최신 종료일 순
        } else {
          return dateA.localeCompare(dateB); // 오래된 종료일 순
        }
      } else {
        // 종목명 기준 정렬
        const nameA = (a.name || '').toLowerCase();
        const nameB = (b.name || '').toLowerCase();
        if (sortType === 'name_asc') {
          return nameA.localeCompare(nameB); // 종목명 오름차순
        } else {
          return nameB.localeCompare(nameA); // 종목명 내림차순
        }
      }
    });
  }, [allItems, sortType]);

  // 검색 결과: 입력 중에는 모든 매칭 결과, 확정 시에는 가장 최근 1건만
  const searchResult = useMemo(() => {
    if (!searchQuery || !searchQuery.trim()) return null;
    
    const query = searchQuery.trim().toLowerCase();
    if (!query) return null;
    
    // 종목명 기준 부분 일치 검색 (대소문자 구분 없음)
    const matched = allItems.filter(item => {
      const name = (item.name || '').toLowerCase();
      const ticker = (item.ticker || '').toLowerCase();
      return name.includes(query) || ticker.includes(query);
    });
    
    if (matched.length === 0) return null;
    
    // 시간 역순 정렬
    matched.sort((a, b) => {
      const dateA = a.archived_at || a.updated_at || a.created_at || '';
      const dateB = b.archived_at || b.updated_at || b.created_at || '';
      return dateB.localeCompare(dateA);
    });
    
    // 검색 확정 시에는 가장 최근 1건만 반환, 입력 중에는 모든 매칭 결과 반환
    if (isSearchConfirmed) {
      return matched[0];
    } else {
      return matched; // 배열 전체 반환
    }
  }, [searchQuery, allItems, isSearchConfirmed]);

  // 표시할 아이템 결정: 검색 중이면 검색 결과, 아니면 기본 리스트
  const displayItems = useMemo(() => {
    if (searchQuery && searchQuery.trim()) {
      if (!searchResult) return [];
      // 검색 확정 시에는 배열이 아닌 단일 객체, 입력 중에는 배열
      return Array.isArray(searchResult) ? searchResult : [searchResult];
    }
    return defaultItems;
  }, [searchQuery, searchResult, defaultItems]);

  // 검색어 변경 시 검색 확정 상태 초기화
  useEffect(() => {
    setIsSearchConfirmed(false);
  }, [searchQuery]);

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

        {/* 검색 입력 및 정렬 */}
        <div className="bg-white border-b border-gray-200">
          <div className="px-4 py-3">
            <input
              type="text"
              placeholder="종목명으로 검색"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  setIsSearchConfirmed(true);
                  e.currentTarget.blur();
                }
              }}
              onBlur={() => {
                if (searchQuery && searchQuery.trim()) {
                  setIsSearchConfirmed(true);
                }
              }}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            />
          </div>
          
          {/* 정렬 UI (검색 중이 아닐 때만 표시) */}
          {!searchQuery || !searchQuery.trim() ? (
            <div className="px-4 pb-3">
              <div className="flex items-center space-x-2">
                <span className="text-sm text-gray-600">정렬:</span>
                <select
                  value={sortType}
                  onChange={(e) => setSortType(e.target.value)}
                  className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent bg-white"
                >
                  <option value="date_desc">날짜순 (최신)</option>
                  <option value="date_asc">날짜순 (오래된)</option>
                  <option value="name_asc">종목명순 (가나다)</option>
                  <option value="name_desc">종목명순 (역순)</option>
                </select>
              </div>
            </div>
          ) : null}
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
        {loading && allItems.length === 0 && (
          <div className="p-4 text-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500 mx-auto"></div>
            <p className="text-gray-500 mt-2">데이터를 불러오는 중...</p>
          </div>
        )}

        {/* 검색 결과 없음 */}
        {!loading && searchQuery && searchQuery.trim() && (!searchResult || (Array.isArray(searchResult) && searchResult.length === 0)) && (
          <div className="p-4 text-center py-8">
            <p className="text-gray-500 text-lg mb-2">검색 결과가 없습니다.</p>
          </div>
        )}

        {/* ARCHIVED 목록 */}
        {!loading && displayItems.length > 0 && (
          <div className="px-4 py-3 space-y-3">
            {displayItems.map((item) => (
              <ArchivedCardV3 
                key={`${item.ticker}-${item.recommendation_id || item.id || item.anchor_date || ''}`} 
                item={item}
              />
            ))}
          </div>
        )}

        {/* 데이터가 없는 경우 (검색 중이 아닐 때만) */}
        {!loading && displayItems.length === 0 && !error && !searchQuery && (
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

