import { useRouter } from 'next/router';
import { useAuth } from '../contexts/AuthContext';

export default function Header({ title = "스톡인사이트" }) {
  const router = useRouter();
  const { user, authLoading, authChecked } = useAuth();

  return (
    <div className="bg-white shadow-sm">
      <div className="flex items-center justify-between p-4">
        <div className="flex items-center space-x-4">
          <button 
            onClick={() => router.push('/')}
            className="text-lg font-semibold text-gray-800 hover:text-blue-600 transition-colors"
          >
            {title}
          </button>
        </div>
        <div className="flex items-center space-x-3">
          {!authLoading && authChecked && user ? (
            <span className="text-sm text-gray-600">
              {user.name}님 ({user.provider})
            </span>
          ) : !authLoading && authChecked ? (
            <span className="text-sm text-gray-500">게스트 사용자</span>
          ) : (
            <span className="text-sm text-gray-400">로딩 중...</span>
          )}
          <button 
            onClick={() => router.push('/subscription')}
            className="px-3 py-1 bg-gradient-to-r from-yellow-400 to-yellow-500 text-gray-800 text-xs font-semibold rounded-full shadow-sm hover:shadow-md transition-all duration-200"
          >
            👑 프리미어
          </button>
        </div>
      </div>
    </div>
  );
}
