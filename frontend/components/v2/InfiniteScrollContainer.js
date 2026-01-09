/**
 * 인피니티 스크롤 컨테이너 컴포넌트
 */
import { useEffect, useRef, useCallback } from 'react';

export default function InfiniteScrollContainer({ 
  children, 
  onLoadMore, 
  hasMore, 
  isLoading,
  loadingComponent 
}) {
  const observerRef = useRef(null);
  const sentinelRef = useRef(null);

  // Intersection Observer 설정
  useEffect(() => {
    if (!hasMore || isLoading) {
      // hasMore가 false이거나 로딩 중이면 Observer 해제
      if (observerRef.current && sentinelRef.current) {
        observerRef.current.unobserve(sentinelRef.current);
      }
      return;
    }

    // 기존 Observer 정리
    if (observerRef.current) {
      observerRef.current.disconnect();
    }

    const options = {
      root: null,
      rootMargin: '100px', // 뷰포트 하단 100px 전에 미리 로드
      threshold: 0.1
    };

    observerRef.current = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting && hasMore && !isLoading) {
          console.log('InfiniteScrollContainer: 센티널 감지, onLoadMore 호출');
          onLoadMore();
        }
      });
    }, options);

    // 센티널 요소가 준비되면 관찰 시작
    if (sentinelRef.current) {
      observerRef.current.observe(sentinelRef.current);
      console.log('InfiniteScrollContainer: Observer 설정 완료', { hasMore, isLoading });
    } else {
      // 센티널이 아직 준비되지 않았으면 약간의 지연 후 재시도
      const timer = setTimeout(() => {
        if (sentinelRef.current && observerRef.current) {
          observerRef.current.observe(sentinelRef.current);
          console.log('InfiniteScrollContainer: Observer 설정 완료 (지연)');
        }
      }, 100);
      return () => {
        clearTimeout(timer);
        if (observerRef.current && sentinelRef.current) {
          observerRef.current.unobserve(sentinelRef.current);
        }
      };
    }

    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect();
      }
    };
  }, [hasMore, isLoading, onLoadMore]);

  return (
    <div>
      {children}
      
      {/* 감지용 센티널 요소 */}
      <div ref={sentinelRef} className="h-4" />
      
      {/* 로딩 인디케이터 */}
      {isLoading && (
        <div className="p-4 text-center">
          {loadingComponent || (
            <>
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500 mx-auto"></div>
              <p className="text-gray-500 text-sm mt-2">더 많은 결과를 불러오는 중...</p>
            </>
          )}
        </div>
      )}
      
      {/* 더 이상 로드할 데이터가 없는 경우 */}
      {!hasMore && !isLoading && (
        <div className="p-4 text-center">
          <p className="text-gray-400 text-sm">모든 결과를 불러왔습니다.</p>
        </div>
      )}
    </div>
  );
}

