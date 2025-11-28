import Header from '../components/Header';
import BottomNavigation from '../components/BottomNavigation';
import PopupNotice from '../components/PopupNotice';

/**
 * 공통 레이아웃 컴포넌트
 * 모든 페이지에서 Header와 BottomNavigation을 자동으로 제공합니다.
 * 
 * @param {Object} props
 * @param {React.ReactNode} props.children - 페이지 컨텐츠
 * @param {string} props.headerTitle - Header에 표시할 제목 (기본값: "스톡인사이트")
 * @param {boolean} props.showHeader - Header 표시 여부 (기본값: true)
 * @param {boolean} props.showBottomNav - BottomNavigation 표시 여부 (기본값: true)
 * @param {boolean} props.showPopupNotice - PopupNotice 표시 여부 (기본값: true)
 */
export default function Layout({ 
  children, 
  headerTitle = "스톡인사이트",
  showHeader = true,
  showBottomNav = true,
  showPopupNotice = true
}) {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* 팝업 공지 */}
      {showPopupNotice && <PopupNotice />}
      
      {/* 상단 헤더 */}
      {showHeader && <Header title={headerTitle} />}
      
      {/* 페이지 컨텐츠 */}
      <main className={showBottomNav ? "pb-20" : ""}>
        {children}
      </main>
      
      {/* 하단 네비게이션 */}
      {showBottomNav && <BottomNavigation />}
    </div>
  );
}

