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
    if (!hasMore || isLoading) return;

    const options = {
      root: null,
      rootMargin: '100px', // 뷰포트 하단 100px 전에 미리 로드
      threshold: 0.1
    };

    observerRef.current = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting && hasMore && !isLoading) {
          onLoadMore();
        }
      });
    }, options);

    if (sentinelRef.current) {
      observerRef.current.observe(sentinelRef.current);
    }

    return () => {
      if (observerRef.current && sentinelRef.current) {
        observerRef.current.unobserve(sentinelRef.current);
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

