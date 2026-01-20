import { useRouter } from 'next/router';
import { useAuth } from '../../contexts/AuthContext';

export default function Header({ title = "스톡인사이트" }) {
  const router = useRouter();
  const { user, authLoading, authChecked } = useAuth();

  // 특별 사용자 확인 함수
  const isSpecialUser = (user) => {
    return user?.email === 'kuksos80215@daum.net';
  };

  return (
    <div className="bg-white shadow-sm">
      <div className="flex items-center justify-between p-4">
        <div className="flex items-center space-x-4">
          <button 
            onClick={() => router.push('/')}
            className="text-[18px] font-bold text-gray-800 hover:text-blue-600 transition-colors pb-3"
          >
            {title}
          </button>
        </div>
        <div className="flex items-center space-x-3">
          {!authLoading && authChecked && user ? (
            isSpecialUser(user) ? (
              <div className="flex items-center space-x-2">
                <span className="special-user-icon text-lg">✨</span>
                <span className="special-user-name text-sm">
                  윤봄님
                </span>
                <span className="special-user-badge px-2 py-0.5 text-xs font-semibold rounded-full text-white">
                  💖 Special
                </span>
                {user.membership_tier === 'vip' ? (
                  <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-purple-100 text-purple-800">
                    👑 VIP
                  </span>
                ) : user.membership_tier === 'premium' ? (
                  <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-blue-100 text-blue-800">
                    👑 프리미엄
                  </span>
                ) : null}
              </div>
            ) : (
              <div className="flex items-center space-x-2">
                <span className="text-sm text-gray-600">
                  {user.name}님
                </span>
                {user.is_admin ? (
                  <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-red-100 text-red-800">
                    🔧 관리자
                  </span>
                ) : user.membership_tier === 'vip' ? (
                  <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-purple-100 text-purple-800">
                    👑 VIP
                  </span>
                ) : user.membership_tier === 'premium' ? (
                  <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-blue-100 text-blue-800">
                    👑 프리미엄
                  </span>
                ) : (
                  <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-gray-100 text-gray-600">
                    일반 회원
                  </span>
                )}
              </div>
            )
          ) : !authLoading && authChecked ? (
            <span className="text-sm text-gray-500">게스트 사용자</span>
          ) : (
            <span className="text-sm text-gray-400">로딩 중...</span>
          )}
          {/* <button 
            onClick={() => router.push('/subscription')}
            className="px-3 py-1 bg-gradient-to-r from-yellow-400 to-yellow-500 text-gray-800 text-xs font-semibold rounded-full shadow-sm hover:shadow-md transition-all duration-200"
          >
            👑 프리미어
          </button> */}
        </div>
      </div>
    </div>
  );
}
