// Scanner V3 전용 화면 - 상태 기반 섹션 버전
import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useRouter } from 'next/router';
import Head from 'next/head';
// config는 동적 import로 처리
const getConfig = () => {
  if (typeof window !== 'undefined') {
    // 클라이언트 사이드 - 개발 환경에서는 항상 로컬 백엔드 사용
    // window.location.hostname으로 로컬 환경 감지
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
import Layout from '../../layouts/v2/Layout';
import ActiveRecommendationCard from '../../components/v3/ActiveRecommendationCard';
import WeakRecommendationCard from '../../components/v3/WeakRecommendationCard';
import BrokenRecommendationCard from '../../components/v3/BrokenRecommendationCard';
import StatusSectionHeader from '../../components/v3/StatusSectionHeader';
import NoRecommendationsCard from '../../components/v3/NoRecommendationsCard';
import MarketHolidayBanner from '../../components/v3/MarketHolidayBanner';
import { BACKEND_STATUS, getSectionType, shouldRenderStatus } from '../../utils/v3StatusMapping';
import { isMarketHolidayToday } from '../../utils/marketUtils';
import { isToday, isBeforeRecommendationTime, isTimestampToday } from '../../utils/dayStatusUtils';

// 상수 정의
const ACTIVE_COLLAPSE_THRESHOLD = 6;
const ACTIVE_DISPLAY_LIMIT = 12; // 기본 표시 개수 (접힘 상태)

// 유틸 함수: 오늘 날짜 키 (Asia/Seoul)
const getTodayKey = () => {
  const now = new Date();
  // Asia/Seoul 타임존 (UTC+9)
  const seoulTime = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Seoul' }));
  const year = seoulTime.getFullYear();
  const month = String(seoulTime.getMonth() + 1).padStart(2, '0');
  const day = String(seoulTime.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

// localStorage 키
const STORAGE_KEYS = {
  BROKEN_COLLAPSED: 'v3.section.broken.collapsed',
  ACTIVE_COLLAPSED: 'v3.section.active.collapsed',
  AUTO_EXPAND_BROKEN_LAST_DATE: 'v3.autoExpand.broken.lastDate',
  AUTO_EXPAND_ACTIVE_LAST_DATE: 'v3.autoExpand.active.lastDate'
};

export default function ScannerV3({ initialData, initialScanDate, initialMarketCondition, initialV3CaseInfo, initialDailyDigest, initialArchivedCount }) {
  const router = useRouter();
  
  // 상태 기반 데이터 구조: items 배열을 상태별로 분류
  const [items, setItems] = useState(() => {
    // 초기 데이터에서 REPLACED만 제외 (ARCHIVED는 별도 섹션으로 표시)
    if (initialData && Array.isArray(initialData)) {
      return initialData.filter(item => {
        // NORESULT 제외
        if (!item || item.ticker === 'NORESULT') return false;
        // REPLACED 제외 (내부 상태, UX에 노출하지 않음)
        if (item.status === 'REPLACED') return false;
        // status가 없으면 경고 (개발 환경)
        if (!item.status && process.env.NODE_ENV === 'development') {
          console.warn('[ScannerV3] status 필드가 없는 아이템:', item);
        }
        return true;
      });
    }
    return [];
  });
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [mounted, setMounted] = useState(false);
  const [dailyDigest, setDailyDigest] = useState(initialDailyDigest || null);
  
  // 자동 펼침이 이미 실행되었는지 추적 (무한 루프 방지)
  const autoExpandExecuted = useRef({ broken: false, active: false });
  // 초기 fetch가 실행되었는지 추적
  const initialFetchExecuted = useRef(false);
  
  // 접힘/펼침 상태 (서버/클라이언트 일치를 위해 초기값은 항상 동일하게)
  const [brokenCollapsed, setBrokenCollapsed] = useState(true); // 기본값: 접힘
  const [activeCollapsed, setActiveCollapsed] = useState(true); // 기본값: 접힘 (요구사항 변경)
  const [activeExpanded, setActiveExpanded] = useState(false); // 전체 펼침 상태 (더보기 버튼용)
  const [archivedCount, setArchivedCount] = useState(initialArchivedCount || 0); // ARCHIVED 개수만 저장
  
  // 클라이언트에서만 localStorage에서 읽어서 상태 업데이트
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const savedBroken = localStorage.getItem(STORAGE_KEYS.BROKEN_COLLAPSED);
      if (savedBroken !== null) {
        setBrokenCollapsed(savedBroken === 'true');
      }
      
      const savedActive = localStorage.getItem(STORAGE_KEYS.ACTIVE_COLLAPSED);
      if (savedActive !== null) {
        setActiveCollapsed(savedActive === 'true');
      }
      
    }
  }, []); // 마운트 시 한 번만 실행
  
  // 상태별로 아이템 분류 및 정렬
  const { brokenItems, activeItems, activeItemsWithNewFlag, limitedActiveItems, todayRecommendations, hasMoreActiveItems, totalActiveCount, summaryNewItems, summaryChangedItems } = useMemo(() => {
    const broken = [];
    const activeMap = new Map(); // ticker 중복 제거용
    const todayKey = getTodayKey();
    const todayRecommendationsList = []; // 오늘 생성된 추천 이벤트 (anchor_date가 오늘)
    const ACTIVE_DISPLAY_LIMIT = 20; // 표시 상한
    
    // 신규 뱃지 표시 여부 결정: 15:35 이전이고 오늘 생성된 추천만
    const isBefore1535 = isBeforeRecommendationTime();
    
    // 요약 영역용: 신규 추천 및 변화된 추천 (배열로 변경)
    const summaryNewItems = []; // 오늘 새로 추가된 추천 (anchor_date가 오늘인 ACTIVE/WEAK_WARNING)
    const summaryChangedItems = []; // 오늘 변화 발생한 항목 (status_changed_at이 오늘인 BROKEN/WEAK_WARNING)
    
    // 디버깅: items 배열 확인
    if (process.env.NODE_ENV === 'development') {
      const brokenInItems = items.filter(item => item && item.status === BACKEND_STATUS.BROKEN);
      if (brokenInItems.length > 0) {
        console.log('[ScannerV3] useMemo - items 배열에 BROKEN 항목:', {
          totalItems: items.length,
          brokenInItems: brokenInItems.length,
          brokenItems: brokenInItems.map(item => ({
            ticker: item.ticker,
            status: item.status,
            statusType: typeof item.status
          }))
        });
      } else {
        console.warn('[ScannerV3] useMemo - items 배열에 BROKEN 항목이 없습니다:', {
          totalItems: items.length,
          itemsStatuses: items.map(item => item?.status).filter(Boolean)
        });
      }
    }
    
    items.forEach(item => {
      if (!item || item.ticker === 'NORESULT') return;
      
      const status = item.status;
      
      // ARCHIVED는 메인 화면에서 제외 (개수만 사용)
      if (status === BACKEND_STATUS.ARCHIVED) {
        return;
      }
      
      // 방어적 status 필터: ACTIVE, WEAK_WARNING만 허용
      if (status !== BACKEND_STATUS.ACTIVE && status !== BACKEND_STATUS.WEAK_WARNING && status !== BACKEND_STATUS.BROKEN) {
        return;
      }
      
      const sectionType = getSectionType(status);
      
      // 섹션 타입별로 분류
      if (sectionType === 'needs-attention') {
        // BROKEN 상태만 관리 필요 섹션에 표시
        if (status === BACKEND_STATUS.BROKEN) {
          broken.push(item);
          // 디버깅: BROKEN 항목 추가 확인
          if (process.env.NODE_ENV === 'development') {
            console.log('[ScannerV3] BROKEN 항목 추가:', {
              ticker: item.ticker,
              name: item.name,
              status: item.status,
              sectionType: sectionType
            });
          }
        }
      } else if (sectionType === 'active') {
        // ACTIVE, WEAK_WARNING은 메인 추천 영역에 표시
        // ticker 중복 제거: 같은 ticker가 이미 있으면 최신 것만 유지
        const ticker = item.ticker;
        if (ticker) {
          const existing = activeMap.get(ticker);
          if (!existing) {
            activeMap.set(ticker, item);
          } else {
            // 기존 항목과 비교하여 최신 것만 유지 (anchor_date 기준)
            const itemDate = item.anchor_date || '';
            const existingDate = existing.anchor_date || '';
            if (itemDate && existingDate) {
              if (itemDate > existingDate) {
                activeMap.set(ticker, item);
              }
            } else if (itemDate && !existingDate) {
              // anchor_date가 있는 것이 우선
              activeMap.set(ticker, item);
            }
          }
        }
      }
    });
    
    // Map을 배열로 변환
    const active = Array.from(activeMap.values());
    
    // 정렬: BROKEN은 broken_at 내림차순 (없으면 updated_at, 없으면 created_at)
    broken.sort((a, b) => {
      const getDate = (item) => {
        return item.broken_at || item.updated_at || item.created_at || '';
      };
      const dateA = getDate(a);
      const dateB = getDate(b);
      const normalizedA = String(dateA).replace(/-/g, '').slice(0, 8);
      const normalizedB = String(dateB).replace(/-/g, '').slice(0, 8);
      return normalizedB.localeCompare(normalizedA);
    });
    
    // 정렬: ACTIVE, WEAK_WARNING - anchor_date 내림차순 (추천일 기준)
    active.sort((a, b) => {
      const dateA = a.anchor_date || '';
      const dateB = b.anchor_date || '';
      
      if (dateA && dateB) {
        const normalizedA = String(dateA).replace(/-/g, '').slice(0, 8);
        const normalizedB = String(dateB).replace(/-/g, '').slice(0, 8);
        const dateCompare = normalizedB.localeCompare(normalizedA);
        if (dateCompare !== 0) {
          return dateCompare; // 내림차순
        }
      } else if (dateA && !dateB) {
        return -1; // dateA가 있으면 우선
      } else if (!dateA && dateB) {
        return 1; // dateB가 있으면 우선
      }
      
      // 안정 정렬: ticker 오름차순
      const tickerA = a.ticker || '';
      const tickerB = b.ticker || '';
      return tickerA.localeCompare(tickerB);
    });
    
    // 오늘 생성된 추천 이벤트 확인 (anchor_date가 오늘)
    active.forEach(item => {
      if (item.anchor_date && isToday(item.anchor_date)) {
        todayRecommendationsList.push(item);
        // 요약 영역용: 신규 추천 종목 (모든 항목 추가)
        if (item.status === BACKEND_STATUS.ACTIVE || item.status === BACKEND_STATUS.WEAK_WARNING) {
          summaryNewItems.push(item);
        }
      }
    });
    
    // 요약 영역용: 변화된 추천 확인 (status_changed_at이 오늘인 BROKEN/WEAK_WARNING)
    const allItems = [...broken, ...active];
    for (const item of allItems) {
      if (item.status_changed_at && isTimestampToday(item.status_changed_at)) {
        if (item.status === BACKEND_STATUS.BROKEN || item.status === BACKEND_STATUS.WEAK_WARNING) {
          summaryChangedItems.push(item);
        }
      }
    }
    
    // 신규 뱃지 판정: 15:35 이전이고 오늘 생성된 추천만
    // anchor_date가 오늘이어야 신규 (created_at은 백필 시 모두 오늘로 설정될 수 있음)
    const activeItemsWithNewFlag = active.map(item => {
      let isNew = false;
      
      // 15:35 이전이고, ACTIVE/WEAK_WARNING만 신규 뱃지 표시
      if (isBefore1535 && (item.status === BACKEND_STATUS.ACTIVE || item.status === BACKEND_STATUS.WEAK_WARNING)) {
        // anchor_date가 오늘인지 확인 (anchor_date가 추천 기준일이므로 더 정확함)
        if (item.anchor_date && isToday(item.anchor_date)) {
          isNew = true;
        }
      }
      
      return { item, isNew };
    });
    
    // BROKEN 카드 개수 제한 (최대 5개)
    const limitedBrokenItems = broken.slice(0, 5);
    
    // 디버깅: BROKEN 항목 확인
    if (process.env.NODE_ENV === 'development' && broken.length > 0) {
      console.log('[ScannerV3] BROKEN 항목 발견:', {
        totalBroken: broken.length,
        limitedBroken: limitedBrokenItems.length,
        brokenItems: broken.map(item => ({
          ticker: item.ticker,
          name: item.name,
          status: item.status,
          reason: item.reason
        }))
      });
    }
    
    // ACTIVE 표시 제한: 기본 12개만 표시 (접힘 상태)
    const hasMoreActiveItems = activeItemsWithNewFlag.length > ACTIVE_DISPLAY_LIMIT;
    const limitedActiveItems = activeExpanded 
      ? activeItemsWithNewFlag 
      : activeItemsWithNewFlag.slice(0, ACTIVE_DISPLAY_LIMIT);
    
    return { 
      brokenItems: limitedBrokenItems, 
      activeItems: activeItemsWithNewFlag.map(({ item }) => item), // 신규 플래그 제거한 순수 아이템 배열
      activeItemsWithNewFlag: activeItemsWithNewFlag, // 신규 플래그 포함 배열 (모든 아이템)
      limitedActiveItems: limitedActiveItems, // 제한된 아이템 (접힘/펼침 상태에 따라)
      hasMoreActiveItems: hasMoreActiveItems, // 더보기 버튼 표시 여부
      todayRecommendations: todayRecommendationsList,
      totalActiveCount: active.length,
      summaryNewItems: summaryNewItems, // 요약: 신규 추천 종목 리스트
      summaryChangedItems: summaryChangedItems // 요약: 변화된 추천 종목 리스트
    };
  }, [items, activeExpanded]);
  
  // ACTIVE 기본 접힘 상태 결정 (항상 접힘으로 시작)
  // 초기 렌더링 시에만 실행 (localStorage에 값이 없을 때만)
  useEffect(() => {
    if (typeof window === 'undefined') return;
    
    const saved = localStorage.getItem(STORAGE_KEYS.ACTIVE_COLLAPSED);
    // localStorage에 값이 없을 때만 기본값 설정 (항상 접힘)
    if (saved === null) {
      setActiveCollapsed(true); // 기본값: 접힘
    }
  }, []);
  
  // 신규 발생 시 당일 1회 자동 펼침 제거 (신규 카운트 제거로 인해 불필요)
  
  // 토글 핸들러
  const handleBrokenToggle = useCallback(() => {
    const newValue = !brokenCollapsed;
    setBrokenCollapsed(newValue);
    if (typeof window !== 'undefined') {
      localStorage.setItem(STORAGE_KEYS.BROKEN_COLLAPSED, String(newValue));
    }
  }, [brokenCollapsed]);
  
  const handleActiveToggle = useCallback(() => {
    const newValue = !activeCollapsed;
    setActiveCollapsed(newValue);
    if (typeof window !== 'undefined') {
      localStorage.setItem(STORAGE_KEYS.ACTIVE_COLLAPSED, String(newValue));
    }
  }, [activeCollapsed]);
  
  const handleActiveExpand = useCallback(() => {
    setActiveExpanded(true);
  }, []);
  
  const handleActiveCollapse = useCallback(() => {
    setActiveExpanded(false);
  }, []);
  

  // recommendations API에서 추천 데이터 가져오기
  // scan_results는 사용하지 않음
  const fetchRecommendations = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const config = getConfig();
      const base = config?.backendUrl || 'http://localhost:8010';
      
      // V3 전용 API 호출
      const controller = new AbortController();
      let timeoutId = null;
      
      // 인증 토큰 가져오기 (ack 필터링용)
      const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
      const headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
      
      // console.log 제거 (성능 개선)
      
      // 타임아웃 설정 (60초)
      timeoutId = setTimeout(() => {
        console.warn('[fetchRecommendations] 타임아웃 발생 (60초 초과), abort 호출');
        controller.abort();
      }, 60000);
      
      const fetchStartTime = Date.now();
      
      // 3개 API를 병렬로 호출 (성능 개선)
      let activeResponse;
      let needsAttentionResponse;
      let archivedCountResponse;
      
      try {
        // Promise.all로 병렬 호출 (ARCHIVED는 count만 조회하여 성능 최적화)
        [activeResponse, needsAttentionResponse, archivedCountResponse] = await Promise.all([
          fetch(`${base}/api/v3/recommendations/active`, {
            method: 'GET',
            headers: headers,
            mode: 'cors',
            cache: 'no-cache',
            credentials: 'include',
            signal: controller.signal
          }),
          fetch(`${base}/api/v3/recommendations/needs-attention`, {
            method: 'GET',
            headers: headers,
            mode: 'cors',
            cache: 'no-cache',
            credentials: 'include',
            signal: controller.signal
          }),
          fetch(`${base}/api/v3/recommendations/archived/count`, {
            method: 'GET',
            headers: headers,
            mode: 'cors',
            cache: 'no-cache',
            credentials: 'include',
            signal: controller.signal
          }).catch(() => ({ ok: false, json: async () => ({ ok: false, data: { count: 0 } }) })) // ARCHIVED 실패 시 0으로 처리
        ]);
        
        const fetchElapsed = Date.now() - fetchStartTime;
        if (timeoutId) {
          clearTimeout(timeoutId);
        }
        
        if (process.env.NODE_ENV === 'development') {
          console.log('[fetchRecommendations] fetch 완료:', {
            elapsed: `${fetchElapsed}ms`,
            activeStatus: activeResponse.status,
            needsAttentionStatus: needsAttentionResponse.status
          });
        }
      } catch (fetchError) {
        if (timeoutId) {
          clearTimeout(timeoutId);
        }
        throw fetchError;
      }
      
      // ACTIVE 응답 처리
      if (!activeResponse.ok) {
        const errorText = await activeResponse.text();
        console.error('[fetchRecommendations] ACTIVE API 오류:', {
          status: activeResponse.status,
          body: errorText
        });
        throw new Error(`ACTIVE API error! status: ${activeResponse.status}`);
      }
      
      // needs-attention 응답 처리
      if (!needsAttentionResponse.ok) {
        const errorText = await needsAttentionResponse.text();
        console.error('[fetchRecommendations] needs-attention API 오류:', {
          status: needsAttentionResponse.status,
          body: errorText
        });
        throw new Error(`needs-attention API error! status: ${needsAttentionResponse.status}`);
      }
      
      // ARCHIVED 응답 처리 (개수만 사용)
      let archivedCount = 0;
      if (archivedCountResponse && archivedCountResponse.ok) {
        const archivedCountData = await archivedCountResponse.json();
        archivedCount = archivedCountData.data?.count || 0;
      } else if (archivedCountResponse) {
        console.warn('[fetchRecommendations] ARCHIVED count API 오류 (무시):', archivedCountResponse.status);
      }
      
      const activeData = await activeResponse.json();
      const needsAttentionData = await needsAttentionResponse.json();
      
      // daily_digest 추출 (activeData에서)
      if (activeData.daily_digest) {
        setDailyDigest(activeData.daily_digest);
      }
      
      console.log('[fetchRecommendations] API 응답:', {
        activeOk: activeData.ok,
        activeCount: activeData.data?.items?.length || 0,
        needsAttentionOk: needsAttentionData.ok,
        needsAttentionCount: needsAttentionData.data?.items?.length || 0,
        archivedCount: archivedCount,
        dailyDigest: activeData.daily_digest
      });
      
      // API 응답 형식 처리
      if (!activeData.ok) {
        const errorMsg = activeData.error || activeData.message || 'ACTIVE 추천 조회 실패';
        setError(errorMsg);
        console.error('[fetchRecommendations] ACTIVE API 오류 응답:', errorMsg);
        return;
      }
      
      if (!needsAttentionData.ok) {
        const errorMsg = needsAttentionData.error || needsAttentionData.message || 'needs-attention 추천 조회 실패';
        setError(errorMsg);
        console.error('[fetchRecommendations] needs-attention API 오류 응답:', errorMsg);
        return;
      }
      
      // ACTIVE와 needs-attention API 결과만 합치기 (ARCHIVED는 개수만 사용)
      const activeItems = activeData.data?.items || [];
      const needsAttentionItems = needsAttentionData.data?.items || [];
      
      // 백엔드가 반환하는 id 필드를 recommendation_id로 정규화
      const normalizeItem = (item) => {
        if (!item) return item;
        // id 필드가 있으면 recommendation_id로 매핑
        if (item.id && !item.recommendation_id) {
          item.recommendation_id = item.id;
        }
        return item;
      };
      
      const normalizedActiveItems = activeItems.map(normalizeItem);
      const normalizedNeedsAttentionItems = needsAttentionItems.map(normalizeItem);
      const allItems = [...normalizedActiveItems, ...normalizedNeedsAttentionItems];
      
      const brokenItemsRaw = allItems.filter(item => item.status === BACKEND_STATUS.BROKEN);
      console.log('[fetchRecommendations] 아이템 처리 시작:', {
        totalItems: allItems.length,
        activeCount: normalizedActiveItems.length,
        needsAttentionCount: normalizedNeedsAttentionItems.length,
        statusDistribution: {
          ACTIVE: allItems.filter(item => item.status === BACKEND_STATUS.ACTIVE).length,
          WEAK_WARNING: allItems.filter(item => item.status === BACKEND_STATUS.WEAK_WARNING).length,
          BROKEN: brokenItemsRaw.length,
          ARCHIVED: archivedCount,
          REPLACED: allItems.filter(item => item.status === BACKEND_STATUS.REPLACED).length
        },
        brokenItems: brokenItemsRaw.map(item => ({
          ticker: item.ticker,
          name: item.name,
          status: item.status,
          recommendation_id: item.recommendation_id || item.id,
          anchor_date: item.anchor_date
        })),
        needsAttentionItemsRaw: normalizedNeedsAttentionItems.map(item => ({
          ticker: item.ticker,
          name: item.name,
          status: item.status
        }))
      });
      
          // 방어적 status 필터: ACTIVE, WEAK_WARNING, BROKEN만 허용 (ARCHIVED, REPLACED 제외)
          const filteredItems = allItems
            .filter(item => {
              if (!item || item.ticker === 'NORESULT') return false;
              // REPLACED는 절대 노출하지 않음
              if (item.status === BACKEND_STATUS.REPLACED) return false;
              // ARCHIVED는 메인 화면에서 제외
              if (item.status === BACKEND_STATUS.ARCHIVED) return false;
              // 나머지 상태만 허용
              return true;
            })
        // ticker당 ACTIVE/WEAK_WARNING 1개만 유지 (최신 것만) - Map 사용
        .reduce((acc, item) => {
          if (item.status === BACKEND_STATUS.ACTIVE || item.status === BACKEND_STATUS.WEAK_WARNING) {
            // 같은 ticker의 ACTIVE/WEAK_WARNING 기존 항목 찾기
            const existing = acc.find(i => 
              i.ticker === item.ticker && 
              (i.status === BACKEND_STATUS.ACTIVE || i.status === BACKEND_STATUS.WEAK_WARNING)
            );
            if (existing) {
              // 기존 항목과 비교하여 최신 것만 유지 (anchor_date 기준)
              const itemDate = item.anchor_date || '';
              const existingDate = existing.anchor_date || '';
              if (itemDate && existingDate && itemDate > existingDate) {
                // 새 항목이 더 최신이면 교체
                const index = acc.indexOf(existing);
                acc[index] = item;
              } else if (itemDate && !existingDate) {
                // anchor_date가 있는 것이 우선
                const index = acc.indexOf(existing);
                acc[index] = item;
              }
            } else {
              acc.push(item);
            }
          } else {
            // BROKEN은 ticker당 여러 개 가능 (이력 추적)
            acc.push(item);
          }
          return acc;
        }, []);
      
      const filteredBroken = filteredItems.filter(item => item.status === BACKEND_STATUS.BROKEN);
      console.log('[fetchRecommendations] 필터링 완료:', {
        filteredCount: filteredItems.length,
        filteredBrokenCount: filteredBroken.length,
        filteredBroken: filteredBroken.map(item => ({
          ticker: item.ticker,
          name: item.name,
          status: item.status
        })),
        filteredItems: filteredItems.slice(0, 3)
      });
      
      setItems(filteredItems);
      setArchivedCount(archivedCount); // ARCHIVED 개수만 저장
      setError(null);
    } catch (error) {
      console.error('[fetchRecommendations] 에러 발생:', {
        name: error.name,
        message: error.message,
        stack: error.stack,
        errorType: error.constructor.name
      });
      
      if (error.name === 'AbortError' || error.message.includes('aborted')) {
        // 타임아웃 또는 abort 발생
        const errorMsg = '요청 시간이 초과되었습니다 (60초). 백엔드 서버가 응답하지 않습니다. 백엔드 서버가 실행 중인지 확인하거나 잠시 후 다시 시도해주세요.';
        console.error('[fetchRecommendations] 타임아웃/Abort:', errorMsg);
        setError(errorMsg);
      } else if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
        const errorMsg = '네트워크 연결을 확인해주세요. 백엔드 서버가 실행 중인지 확인하세요.';
        console.error('[fetchRecommendations] 네트워크 오류:', errorMsg);
        setError(errorMsg);
      } else {
        const errorMsg = `데이터 불러오는 중 오류가 발생했습니다: ${error.message}`;
        console.error('[fetchRecommendations] 기타 오류:', errorMsg);
        setError(errorMsg);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  // 차트 보기 핸들러 (현재는 사용하지 않지만 호환성을 위해 유지)
  const handleViewChart = useCallback((ticker) => {
    const naverInfoUrl = `https://finance.naver.com/item/main.naver?code=${ticker}`;
    window.open(naverInfoUrl, '_blank');
  }, []);

  useEffect(() => {
    setMounted(true);
  }, []);

  // 초기 데이터가 없으면 최신 스캔 결과 가져오기
  useEffect(() => {
    if (!mounted) {
      console.log('[ScannerV3] 아직 마운트되지 않음');
      return;
    }
    
    // 이미 실행했으면 다시 실행하지 않음
    if (initialFetchExecuted.current) {
      console.log('[ScannerV3] 초기 fetch 이미 실행됨');
      return;
    }
    
    const hasInitialData = initialData && Array.isArray(initialData) && initialData.length > 0;
    
    console.log('[ScannerV3] 초기 데이터 체크:', {
      hasInitialData,
      initialDataLength: initialData?.length || 0,
      itemsLength: items.length,
      loading
    });
    
    // 초기 데이터가 없거나 빈 배열이면 fetch
    if (!hasInitialData && items.length === 0 && !loading) {
      if (process.env.NODE_ENV === 'development') {
        console.log('[ScannerV3] 초기 데이터 없음, fetchRecommendations 호출');
      }
      initialFetchExecuted.current = true;
      fetchRecommendations();
    } else if (hasInitialData) {
      // 초기 데이터가 있으면 SSR 데이터 사용 (불필요한 중복 API 호출 제거)
      // 최신 데이터는 필요 시에만 수동으로 갱신하거나, 일정 시간 후 자동 갱신
      if (process.env.NODE_ENV === 'development') {
        console.log('[ScannerV3] 초기 데이터 사용:', initialData.length, '개 아이템 (SSR)');
      }
      // SSR 데이터 사용, 추가 fetch 제거 (성능 개선)
      initialFetchExecuted.current = true;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mounted]);
  
  // 상세 화면에서 돌아올 때 refetch (ack 후 홈 갱신)
  useEffect(() => {
    if (mounted && router.query.refetch === 'true') {
      // refetch 플래그 제거
      delete router.query.refetch;
      // 홈 데이터 refetch
      fetchRecommendations();
    }
  }, [mounted, router.query.refetch, fetchRecommendations]);
  
  // 디버깅: 상태 로그 (개발 환경에서만)
  useEffect(() => {
    if (process.env.NODE_ENV === 'development') {
      console.log('ScannerV3 상태:', {
        itemsCount: items.length,
        brokenCount: brokenItems.length,
        activeCount: activeItems.length,
        loading
      });
    }
  }, [items.length, brokenItems.length, activeItems.length, loading]);

  return (
    <>
      <Head>
        <title>스톡인사이트</title>
      </Head>
      <Layout headerTitle="스톡인사이트">
        {/* 배너 영역 */}
        <div className="bg-gradient-to-r from-purple-500 to-pink-600 text-white p-4 mb-6 opacity-90">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-[20px] font-bold">
                추천 종목
              </h2>
              <p className="text-[14px] font-normal opacity-90 mt-1.5">
                AI가 추천한 종목을 보여줍니다
              </p>
            </div>
          </div>
        </div>

        {/* 에러 표시 */}
        {error && (
          <div className="mx-4 mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-600 text-sm">{error}</p>
            <button
              onClick={fetchRecommendations}
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
            <p className="text-gray-500 mt-2">스캔 결과를 불러오는 중...</p>
          </div>
        )}

        {/* 상태 기반 섹션 */}
        {!loading && (
          <div className="space-y-0">
            {/* 요약 영역 */}
            <div>
              <div className="px-4">
                {/* 통합 요약 카드 */}
                <div className="bg-blue-50 border border-blue-200 rounded-[14px] p-5 relative overflow-hidden shadow-sm">
                  {/* 상단 톤 바 - 카드 상단의 얇은 색상 바 (시각적 앵커) */}
                  <div className="absolute top-0 left-0 right-0 h-1.5 bg-blue-300 rounded-t-[14px]"></div>
                  
                  {/* 1) 신규 추천 */}
                  <div className="pb-4">
                    <div className="text-lg text-[#111827] mb-2">신규 추천</div>
                    {summaryNewItems.length > 0 ? (
                      <div className="space-y-1.5">
                        {summaryNewItems.map((item) => (
                          <div
                            key={item.ticker || item.recommendation_id || item.id}
                            onClick={(e) => {
                              e.stopPropagation();
                              // 현재 추천 섹션으로 이동
                              setActiveCollapsed(false);
                              setTimeout(() => {
                                const targetCard = document.querySelector(`[data-ticker="${item.ticker}"]`);
                                if (targetCard) {
                                  targetCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                  // 일시적 강조 (0.8~1.0초)
                                  targetCard.classList.add('bg-yellow-50', 'border-yellow-300');
                                  setTimeout(() => {
                                    targetCard.classList.remove('bg-yellow-50', 'border-yellow-300');
                                  }, 900);
                                }
                              }, 100);
                            }}
                            className="text-sm text-[#374151] hover:text-gray-900 cursor-pointer underline transition-colors"
                          >
                            {item.name || item.ticker}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-sm text-[#6B7280]">오늘 새로 추가된 추천은 없습니다</div>
                    )}
                  </div>

                  {/* 구분선 */}
                  <div className="border-t border-blue-200 my-1"></div>

                  {/* 2) 변화된 추천 */}
                  <div>
                    <div className="text-lg text-[#111827] mb-2">변화된 추천</div>
                    {summaryChangedItems.length > 0 ? (
                      <div className="flex flex-wrap -m-1.5">
                        {summaryChangedItems.map((item) => (
                          <div
                            key={item.ticker || item.recommendation_id || item.id}
                            onClick={(e) => {
                              e.stopPropagation();
                              // 상태에 따라 섹션 결정
                              if (item.status === BACKEND_STATUS.BROKEN) {
                                // 추천관리 종료 섹션으로 이동
                                setBrokenCollapsed(false);
                              } else if (item.status === BACKEND_STATUS.WEAK_WARNING) {
                                // 현재 추천 섹션으로 이동
                                setActiveCollapsed(false);
                              }
                              setTimeout(() => {
                                const targetCard = document.querySelector(`[data-ticker="${item.ticker}"]`);
                                if (targetCard) {
                                  targetCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                  // 일시적 강조 (0.8~1.0초)
                                  targetCard.classList.add('bg-yellow-50', 'border-yellow-300');
                                  setTimeout(() => {
                                    targetCard.classList.remove('bg-yellow-50', 'border-yellow-300');
                                  }, 900);
                                }
                              }, 100);
                            }}
                            className="text-[13px] font-medium px-2.5 py-1.5 bg-white text-[#1F2937] rounded-full inline-block cursor-pointer hover:bg-[#F3F6FB] transition-colors m-1.5 border border-[#E2E8F0]"
                          >
                            {item.name || item.ticker}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-sm text-[#6B7280]">변화가 발생한 추천은 없습니다</div>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* 렌더링 우선순위 규칙:
                1) 휴장일이면: 일일 배너 + 기존 추천 카드 유지
                2) 거래일 + 추천 있음: 일일 배너 + 기존 v3 추천 카드 규칙 그대로
                3) 거래일 + 추천 없음: 일일 배너 + "추천 없는 날" 안내 카드
            */}
            
            {/* 거래일 + 추천 없음: "추천 없는 날" 안내 카드 */}
            {!isMarketHolidayToday() && brokenItems.length === 0 && activeItems.length === 0 && !error && (
              <div className="px-4 py-6">
                <NoRecommendationsCard />
              </div>
            )}

            {/* 추천 관리 종료 영역 (BROKEN) - 항상 렌더링 (0개일 때도) */}
            <div className="bg-white border-b border-gray-200">
                <StatusSectionHeader
                  title="추천 관리 종료"
                  count={brokenItems.length}
                  isCollapsed={brokenCollapsed}
                  onToggle={handleBrokenToggle}
                  sectionType="BROKEN"
                />
              {!brokenCollapsed && (
                <div className="px-4 py-3">
                  {brokenItems.length > 0 ? (
                    <div className="space-y-3">
                      {brokenItems.map((item) => {
                        // 섹션 혼입 방지: BROKEN 섹션에 BROKEN만 허용
                        if (process.env.NODE_ENV === 'development' && item.status !== BACKEND_STATUS.BROKEN) {
                          console.error('[ScannerV3] 섹션 혼입 감지: BROKEN 섹션에 status가 BROKEN이 아닌 아이템', item);
                        }
                        // 디버깅: 렌더링 전 확인
                        if (process.env.NODE_ENV === 'development') {
                          console.log('[ScannerV3] BROKEN 카드 렌더링:', {
                            ticker: item.ticker,
                            status: item.status,
                            hasItem: !!item,
                            cardWillRender: item && item.status && item.status === BACKEND_STATUS.BROKEN
                          });
                        }
                        return (
                          <BrokenRecommendationCard 
                            key={`${item.ticker}-${item.recommendation_id || item.id || item.anchor_date || ''}`} 
                            item={item} 
                          />
                        );
                      })}
                    </div>
                  ) : (
                    <div className="py-8 text-center">
                      <p className="text-sm text-gray-500">
                        현재 추천 관리 종료 종목이 없습니다
                      </p>
                      {process.env.NODE_ENV === 'development' && (
                        <p className="text-xs text-gray-400 mt-2">
                          디버깅: brokenItems.length = {brokenItems.length}, brokenCollapsed = {String(brokenCollapsed)}
                        </p>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* ARCHIVED 진입 행 (관리 필요 영역 바로 아래) */}
            {archivedCount > 0 && (
              <div className="bg-white border-b border-gray-200">
                <button
                  type="button"
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    console.log('[ScannerV3] ARCHIVED 진입 행 클릭:', { archivedCount, router: !!router });
                    
                    // window.location.href를 직접 사용 (가장 확실한 방법)
                    const targetUrl = '/archived';
                    console.log('[ScannerV3] 네비게이션 시작:', targetUrl);
                    window.location.href = targetUrl;
                  }}
                  className="w-full px-4 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors cursor-pointer active:bg-gray-100 relative z-10"
                  style={{ pointerEvents: 'auto', position: 'relative' }}
                >
                  <span className="text-sm text-gray-700">
                    종료된 추천 보기 <span className="text-gray-900">({archivedCount})</span>
                  </span>
                  <svg 
                    className="w-5 h-5 text-gray-400" 
                    fill="none" 
                    stroke="currentColor" 
                    viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </button>
              </div>
            )}

            {/* 유효한 추천 섹션 (ACTIVE) */}
            {activeItems.length > 0 && (
              <div className="bg-white border-b border-gray-200 mt-8">
                <StatusSectionHeader
                  title="현재 추천"
                  count={activeItems.length}
                  isCollapsed={activeCollapsed}
                  onToggle={handleActiveToggle}
                  sectionType="ACTIVE"
                />
                {!activeCollapsed && (
                  <div className="px-4 py-3 space-y-3">
                      {limitedActiveItems.map(({ item, isNew }) => {
                        // 섹션 혼입 방지: ACTIVE 섹션에 ACTIVE/WEAK_WARNING만 허용
                        if (process.env.NODE_ENV === 'development') {
                          if (item.status !== BACKEND_STATUS.ACTIVE && item.status !== BACKEND_STATUS.WEAK_WARNING) {
                            console.error('[ScannerV3] 섹션 혼입 감지: ACTIVE 섹션에 허용되지 않은 상태', item);
                          }
                        }
                        
                        // 상태별로 적절한 컴포넌트 렌더링 (물리적 분리)
                        if (item.status === BACKEND_STATUS.ACTIVE) {
                          return (
                            <ActiveRecommendationCard 
                              key={`${item.ticker}-${item.recommendation_id || item.id || item.anchor_date || ''}`} 
                              item={item}
                              isNew={isNew}
                            />
                          );
                        } else if (item.status === BACKEND_STATUS.WEAK_WARNING) {
                          return (
                            <WeakRecommendationCard 
                              key={`${item.ticker}-${item.recommendation_id || item.id || item.anchor_date || ''}`} 
                              item={item}
                              isNew={isNew}
                            />
                          );
                        }
                        
                        // 예외 처리 (개발 환경)
                        if (process.env.NODE_ENV === 'development') {
                          console.warn('[ScannerV3] 예상치 못한 상태:', item.status);
                        }
                        return null;
                      })}
                      
                      {/* 더보기/접기 버튼 (숫자 없음) */}
                      {hasMoreActiveItems && (
                        <div className="text-center py-4 border-t border-gray-200 pt-4">
                          {!activeExpanded ? (
                            <button
                              onClick={handleActiveExpand}
                              className="text-sm text-indigo-600 hover:text-indigo-800 font-medium"
                            >
                              더 보기
                            </button>
                          ) : (
                            <button
                              onClick={handleActiveCollapse}
                              className="text-sm text-gray-600 hover:text-gray-800 font-medium"
                            >
                              접기
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                )}
              </div>
            )}

            {/* 데이터가 없는 경우는 이미 위에서 처리됨 (추천 없는 날 카드 또는 휴장일 안내) */}
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
    
    // V3는 recommendations 테이블에서 데이터를 가져옴 (scan_rank 아님)
    // 타임아웃 설정 (10초로 단축)
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000);
    
    // ACTIVE, needs-attention, ARCHIVED count API를 모두 호출 (ARCHIVED는 개수만)
    const [activeResponse, needsAttentionResponse, archivedCountResponse] = await Promise.all([
      fetch(`${base}/api/v3/recommendations/active`, {
        headers: { 'Accept': 'application/json' },
        signal: controller.signal
      }),
      fetch(`${base}/api/v3/recommendations/needs-attention`, {
        headers: { 'Accept': 'application/json' },
        signal: controller.signal
      }),
      fetch(`${base}/api/v3/recommendations/archived/count`, {
        headers: { 'Accept': 'application/json' },
        signal: controller.signal
      }).catch(() => ({ ok: false, json: async () => ({ ok: false, data: { count: 0 } }) })) // ARCHIVED 실패 시 0으로 처리
    ]);
    
    clearTimeout(timeoutId);

    if (!activeResponse.ok || !needsAttentionResponse.ok) {
      throw new Error(`HTTP error! active: ${activeResponse.status}, needs-attention: ${needsAttentionResponse.status}`);
    }

    const activeData = await activeResponse.json();
    const needsAttentionData = await needsAttentionResponse.json();
    
    // ARCHIVED 응답 처리 (개수만 사용)
    let archivedCount = 0;
    if (archivedCountResponse && archivedCountResponse.ok) {
      const archivedCountData = await archivedCountResponse.json();
      archivedCount = archivedCountData.data?.count || 0;
    }
    
    // daily_digest 추출 (activeData에서)
    const dailyDigest = activeData.daily_digest || null;
    
    console.log('[SSR] API 응답:', {
      activeOk: activeData.ok,
      activeCount: activeData.data?.items?.length || 0,
      needsAttentionOk: needsAttentionData.ok,
      needsAttentionCount: needsAttentionData.data?.items?.length || 0,
      archivedCount: archivedCount,
      dailyDigest: dailyDigest
    });

    if (activeData.ok && needsAttentionData.ok) {
      // ACTIVE와 needs-attention API 결과만 합치기 (ARCHIVED는 개수만 사용)
      const activeItems = activeData.data?.items || [];
      const needsAttentionItems = needsAttentionData.data?.items || [];
      const items = [...activeItems, ...needsAttentionItems];
      
      // id를 recommendation_id로 정규화
      items.forEach(item => {
        if (item.id && !item.recommendation_id) {
          item.recommendation_id = item.id;
        }
      });
      
      console.log('[SSR] 초기 데이터 설정:', {
        itemsCount: items.length,
        activeCount: activeItems.length,
        needsAttentionCount: needsAttentionItems.length,
        archivedCount: archivedCount
      });

      return {
        props: {
          initialData: items,
          initialScanDate: '', // recommendations 테이블에는 scan_date가 없음
          initialMarketCondition: null, // recommendations 테이블에는 market_condition이 없음
          initialV3CaseInfo: null, // recommendations 테이블에는 v3_case_info가 없음
          initialDailyDigest: dailyDigest, // daily_digest 전달
          initialArchivedCount: archivedCount // ARCHIVED 개수 전달
        },
      };
    } else {
      console.warn('[SSR] API 응답 오류:', {
        activeOk: activeData.ok,
        activeError: activeData.error,
        activeMessage: activeData.message,
        needsAttentionOk: needsAttentionData.ok,
        needsAttentionError: needsAttentionData.error,
        needsAttentionMessage: needsAttentionData.message
      });
      return {
        props: {
          initialData: [],
          initialScanDate: '',
          initialMarketCondition: null,
          initialV3CaseInfo: null,
          initialDailyDigest: null,
          initialArchivedCount: 0,
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
        initialScanDate: '',
        initialMarketCondition: null,
        initialV3CaseInfo: null,
        initialDailyDigest: null,
        initialArchivedCount: 0,
      },
    };
  }
}
