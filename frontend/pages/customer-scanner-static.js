import Head from 'next/head';

export default function CustomerScannerStatic({ initialData }) {
  return (
    <html>
      <Head>
        <title>스톡인사이트 - 주식 스캐너</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <meta name="format-detection" content="telephone=no" />
        <style jsx>{`
          body {
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: #f9fafb;
            min-height: 100vh;
          }
          .container {
            min-height: 100vh;
            background-color: #f9fafb;
          }
          .header {
            background-color: white;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            padding: 16px;
          }
          .header-content {
            display: flex;
            align-items: center;
            justify-content: space-between;
          }
          .title {
            font-size: 18px;
            font-weight: 600;
            color: #1f2937;
          }
          .refresh-btn {
            padding: 8px;
            color: #6b7280;
            background: none;
            border: none;
            cursor: pointer;
            font-size: 16px;
          }
          .banner {
            background: linear-gradient(to right, #3b82f6, #8b5cf6);
            color: white;
            padding: 16px;
          }
          .banner-content {
            display: flex;
            align-items: center;
            justify-content: space-between;
          }
          .banner-text h2 {
            font-size: 18px;
            font-weight: 600;
            margin: 0 0 4px 0;
          }
          .banner-text p {
            font-size: 14px;
            opacity: 0.9;
            margin: 0;
          }
          .banner-icon {
            width: 64px;
            height: 64px;
            background-color: rgba(255,255,255,0.2);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
          }
          .banner-icon-inner {
            width: 48px;
            height: 48px;
            background-color: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
          }
          .finance-icon {
            font-size: 32px;
            display: block;
          }
          .tabs {
            background-color: white;
            border-bottom: 1px solid #e5e7eb;
            display: flex;
          }
          .tab {
            flex: 1;
            padding: 12px 16px;
            text-align: center;
            font-weight: 500;
            border: none;
            cursor: pointer;
          }
          .tab.active {
            background-color: #3b82f6;
            color: white;
          }
          .tab:not(.active) {
            background-color: white;
            color: #6b7280;
          }
          .content {
            padding: 16px;
          }
          .stock-item {
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            border: 1px solid #e5e7eb;
            padding: 16px;
            margin-bottom: 12px;
          }
          .stock-header {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            margin-bottom: 12px;
          }
          .stock-info {
            flex: 1;
          }
          .stock-name {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 4px;
          }
          .stock-name h3 {
            font-weight: 600;
            color: #1f2937;
            margin: 0;
            font-size: 16px;
          }
          .stock-ticker {
            font-size: 12px;
            color: #6b7280;
          }
          .stars {
            display: flex;
            align-items: center;
            gap: 4px;
          }
          .star {
            font-size: 16px;
          }
          .star.active {
            color: #fbbf24;
          }
          .star.inactive {
            color: #d1d5db;
          }
          .stock-score {
            text-align: right;
          }
          .score-value {
            font-size: 18px;
            font-weight: bold;
            color: #1f2937;
          }
          .score-label {
            font-size: 14px;
            color: #6b7280;
          }
          .stock-details {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            margin-bottom: 12px;
            font-size: 14px;
          }
          .detail-item {
            display: flex;
          }
          .detail-label {
            color: #6b7280;
          }
          .detail-value {
            margin-left: 8px;
            color: #1f2937;
          }
          .stock-actions {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding-top: 12px;
            border-top: 1px solid #e5e7eb;
          }
          .action-links {
            display: flex;
            gap: 16px;
            font-size: 14px;
          }
          .action-link {
            color: #3b82f6;
            background: none;
            border: none;
            cursor: pointer;
            text-decoration: none;
          }
          .buy-btn {
            padding: 8px 16px;
            background-color: #ef4444;
            color: white;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            border: none;
            cursor: pointer;
          }
          .empty-state {
            text-align: center;
            padding: 32px 0;
          }
          .empty-text {
            color: #6b7280;
            margin: 0 0 16px 0;
          }
          .reload-btn {
            padding: 8px 16px;
            background-color: #3b82f6;
            color: white;
            border-radius: 4px;
            border: none;
            cursor: pointer;
          }
          .bottom-nav {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background-color: black;
            color: white;
          }
          .bottom-nav-content {
            display: flex;
            align-items: center;
            justify-content: space-around;
            padding: 8px 0;
          }
          .nav-item {
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 8px 0;
            background: none;
            border: none;
            color: white;
            cursor: pointer;
          }
          .nav-text {
            font-size: 12px;
          }
          .bottom-spacer {
            height: 80px;
          }
        `}</style>
      </Head>
      <body>
        <div className="container">
          {/* 상단 바 */}
          <div className="header">
            <div className="header-content">
              <span className="title">스톡인사이트</span>
              <button 
                className="refresh-btn"
                onClick={() => {
                  if (typeof window !== 'undefined') {
                    window.location.reload();
                  }
                }}
              >
                🔄
              </button>
            </div>
          </div>

          {/* 정보 배너 */}
          <div className="banner">
            <div className="banner-content">
              <div className="banner-text">
                <h2>시장의 주도주 정보</h2>
                <p>프리미어 클럽에서 확인!</p>
              </div>
              <div className="banner-icon">
                <div className="banner-icon-inner">
                  <span className="finance-icon">💰</span>
                </div>
              </div>
            </div>
          </div>

          {/* 시장 선택 탭 */}
          <div className="tabs">
            <button className="tab active">전체</button>
            <button className="tab">코스피</button>
            <button className="tab">코스닥</button>
          </div>

          {/* 스캔 결과 목록 */}
          <div className="content">
            {initialData && initialData.length > 0 ? (
              initialData.slice(0, 10).map((item, index) => (
                <div key={item.ticker || index} className="stock-item">
                  {/* 종목 정보 */}
                  <div className="stock-header">
                    <div className="stock-info">
                      <div className="stock-name">
                        <h3>{item.name || 'N/A'}</h3>
                        <span className="stock-ticker">({item.ticker || 'N/A'})</span>
                      </div>
                      <div className="stars">
                        {Array.from({ length: 5 }, (_, i) => {
                          const isActive = i < Math.min(5, Math.max(1, Math.floor((item.score || 0) / 2)));
                          return (
                            <span 
                              key={i} 
                              className={`star ${isActive ? 'active' : 'inactive'}`}
                            >
                              ★
                            </span>
                          );
                        })}
                      </div>
                    </div>
                    <div className="stock-score">
                      <div className="score-value">{item.score || '-'}</div>
                      <div className="score-label">{item.score_label || '-'}</div>
                    </div>
                  </div>

                  {/* 스캔 정보 */}
                  <div className="stock-details">
                    <div className="detail-item">
                      <span className="detail-label">종목코드:</span>
                      <span className="detail-value">{item.ticker || '-'}</span>
                    </div>
                    <div className="detail-item">
                      <span className="detail-label">평가:</span>
                      <span className="detail-value">{item.score_label || '-'}</span>
                    </div>
                    <div className="detail-item">
                      <span className="detail-label">점수:</span>
                      <span className="detail-value">{item.score || '-'}</span>
                    </div>
                    <div className="detail-item">
                      <span className="detail-label">시장:</span>
                      <span className="detail-value">{item.ticker && item.ticker.length === 6 ? (item.ticker.startsWith('0') ? '코스닥' : '코스피') : '-'}</span>
                    </div>
                  </div>

                  {/* 액션 버튼 */}
                  <div className="stock-actions">
                    <div className="action-links">
                      <button className="action-link">관심등록</button>
                      <button className="action-link">차트</button>
                      <button className="action-link">기업정보</button>
                    </div>
                    <button className="buy-btn">매수</button>
                  </div>
                </div>
              ))
            ) : (
              <div className="empty-state">
                <p className="empty-text">스캔 결과가 없습니다.</p>
                <button 
                  className="reload-btn"
                  onClick={() => {
                    if (typeof window !== 'undefined') {
                      window.location.reload();
                    }
                  }}
                >
                  새로고침
                </button>
              </div>
            )}
          </div>

          {/* 하단 네비게이션 */}
          <div className="bottom-nav">
            <div className="bottom-nav-content">
              {['메뉴', '홈', '통합검색', '관심종목', '주식현재가', '주식주문'].map((item) => (
                <button key={item} className="nav-item">
                  <span className="nav-text">{item}</span>
                </button>
              ))}
            </div>
          </div>

          {/* 하단 네비게이션 공간 확보 */}
          <div className="bottom-spacer"></div>
        </div>
      </body>
    </html>
  );
}

export async function getServerSideProps() {
  try {
    const base = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8010';
    const response = await fetch(`${base}/latest-scan`);
    const data = await response.json();
    
    if (data && data.ok && data.data && data.data.rank) {
      return {
        props: {
          initialData: data.data.rank
        }
      };
    }
  } catch (error) {
    console.error('서버에서 스캔 결과 조회 실패:', error);
  }
  
  return {
    props: {
      initialData: []
    }
  };
}
