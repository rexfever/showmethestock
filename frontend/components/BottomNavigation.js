import { useRouter } from 'next/router';
import { useAuth } from '../contexts/AuthContext';

export default function BottomNavigation() {
  const router = useRouter();
  const { user, logout } = useAuth();

  return (
    <>
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
            className="flex flex-col items-center py-2 hover:bg-gray-800"
            onClick={() => router.push('/portfolio')}
          >
            <svg className="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
            </svg>
            <span className="text-xs">나의투자종목</span>
          </button>
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
    </>
  );
}
