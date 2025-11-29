import Head from 'next/head';

export default function CustomerScannerSimple({ initialData }) {
  return (
    <>
      <Head>
        <title>스톡인사이트 - 주식 스캐너</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <meta name="format-detection" content="telephone=no" />
      </Head>

      <div style={{ minHeight: '100vh', backgroundColor: '#f9fafb' }}>
        {/* 상단 바 */}
        <div style={{ backgroundColor: 'white', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', padding: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '18px', fontWeight: '600', color: '#1f2937' }}>
              스톡인사이트
            </span>
            <button 
              onClick={() => window.location.reload()}
              style={{ padding: '8px', color: '#6b7280' }}
            >
              🔄
            </button>
          </div>
        </div>

        {/* 정보 배너 */}
        <div style={{ 
          background: 'linear-gradient(to right, #3b82f6, #8b5cf6)', 
          color: 'white', 
          padding: '16px' 
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <h2 style={{ fontSize: '18px', fontWeight: '600', margin: '0 0 4px 0' }}>
                시장의 주도주 정보
              </h2>
              <p style={{ fontSize: '14px', opacity: 0.9, margin: 0 }}>
                프리미어 클럽에서 확인!
              </p>
            </div>
            <div style={{
              width: '64px',
              height: '64px',
              backgroundColor: 'rgba(255,255,255,0.2)',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <div style={{
                width: '48px',
                height: '48px',
                backgroundColor: 'white',
                borderRadius: '50%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <div style={{ 
                  fontSize: '24px', 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'center',
                  position: 'relative'
                }}>
                  <span style={{ fontSize: '28px' }}>🔮</span>
                  <span style={{ 
                    fontSize: '16px', 
                    position: 'absolute', 
                    top: '2px', 
                    left: '8px',
                    color: '#10b981'
                  }}>📈</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 시장 선택 탭 */}
        <div style={{ backgroundColor: 'white', borderBottom: '1px solid #e5e7eb' }}>
          <div style={{ display: 'flex' }}>
            {['전체', '코스피', '코스닥'].map((market) => (
              <button
                key={market}
                style={{
                  flex: 1,
                  padding: '12px 16px',
                  textAlign: 'center',
                  fontWeight: '500',
                  backgroundColor: market === '전체' ? '#3b82f6' : 'white',
                  color: market === '전체' ? 'white' : '#6b7280',
                  border: 'none',
                  cursor: 'pointer'
                }}
              >
                {market}
              </button>
            ))}
          </div>
        </div>

        {/* 스캔 결과 목록 */}
        <div style={{ padding: '16px' }}>
          {initialData && initialData.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {initialData.slice(0, 10).map((item, index) => (
                <div 
                  key={item.ticker || index} 
                  style={{
                    backgroundColor: 'white',
                    borderRadius: '8px',
                    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
                    border: '1px solid #e5e7eb',
                    padding: '16px'
                  }}
                >
                  {/* 종목 정보 */}
                  <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '12px' }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                        <h3 style={{ fontWeight: '600', color: '#1f2937', margin: 0, fontSize: '16px' }}>
                          {item.name || 'N/A'}
                        </h3>
                        <span style={{ fontSize: '12px', color: '#6b7280' }}>
                          ({item.ticker || 'N/A'})
                        </span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                        {Array.from({ length: 5 }, (_, i) => (
                          <span 
                            key={i} 
                            style={{ 
                              fontSize: '16px', 
                              color: i < Math.min(5, Math.max(1, Math.floor((item.score || 0) / 2))) ? '#fbbf24' : '#d1d5db' 
                            }}
                          >
                            ★
                          </span>
                        ))}
                      </div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#1f2937' }}>
                        {item.score || '-'}
                      </div>
                      <div style={{ fontSize: '14px', color: '#6b7280' }}>
                        {item.score_label || '-'}
                      </div>
                    </div>
                  </div>

                  {/* 스캔 정보 */}
                  <div style={{ 
                    display: 'grid', 
                    gridTemplateColumns: '1fr 1fr', 
                    gap: '16px', 
                    marginBottom: '12px', 
                    fontSize: '14px' 
                  }}>
                    <div>
                      <span style={{ color: '#6b7280' }}>종목코드:</span>
                      <span style={{ marginLeft: '8px', color: '#1f2937' }}>{item.ticker || '-'}</span>
                    </div>
                    <div>
                      <span style={{ color: '#6b7280' }}>평가:</span>
                      <span style={{ marginLeft: '8px', color: '#1f2937' }}>{item.score_label || '-'}</span>
                    </div>
                    <div>
                      <span style={{ color: '#6b7280' }}>점수:</span>
                      <span style={{ marginLeft: '8px', color: '#1f2937' }}>{item.score || '-'}</span>
                    </div>
                    <div>
                      <span style={{ color: '#6b7280' }}>시장:</span>
                      <span style={{ marginLeft: '8px', color: '#1f2937' }}>{item.ticker && item.ticker.length === 6 ? (item.ticker.startsWith('0') ? '코스닥' : '코스피') : '-'}</span>
                    </div>
                  </div>

                  {/* 액션 버튼 */}
                  <div style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    justifyContent: 'space-between', 
                    paddingTop: '12px', 
                    borderTop: '1px solid #e5e7eb' 
                  }}>
                    <div style={{ display: 'flex', gap: '16px', fontSize: '14px' }}>
                      <button style={{ color: '#3b82f6', background: 'none', border: 'none', cursor: 'pointer' }}>
                        투자등록
                      </button>
                      <button style={{ color: '#3b82f6', background: 'none', border: 'none', cursor: 'pointer' }}>
                        차트
                      </button>
                      <button style={{ color: '#3b82f6', background: 'none', border: 'none', cursor: 'pointer' }}>
                        기업정보
                      </button>
                    </div>
                    <button 
                      style={{
                        padding: '8px 16px',
                        backgroundColor: '#ef4444',
                        color: 'white',
                        borderRadius: '8px',
                        fontSize: '14px',
                        fontWeight: '500',
                        border: 'none',
                        cursor: 'pointer'
                      }}
                    >
                      매수
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '32px 0' }}>
              <p style={{ color: '#6b7280', margin: '0 0 16px 0' }}>
                스캔 결과가 없습니다.
              </p>
              <button 
                onClick={() => window.location.reload()}
                style={{
                  padding: '8px 16px',
                  backgroundColor: '#3b82f6',
                  color: 'white',
                  borderRadius: '4px',
                  border: 'none',
                  cursor: 'pointer'
                }}
              >
                새로고침
              </button>
            </div>
          )}
        </div>

        {/* 하단 네비게이션 */}
        <div style={{
          position: 'fixed',
          bottom: 0,
          left: 0,
          right: 0,
          backgroundColor: 'black',
          color: 'white'
        }}>
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'space-around', 
            padding: '8px 0' 
          }}>
            {['메뉴', '홈', '통합검색', '관심종목', '주식현재가', '주식주문'].map((item) => (
              <button 
                key={item}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  padding: '8px 0',
                  background: 'none',
                  border: 'none',
                  color: 'white',
                  cursor: 'pointer'
                }}
              >
                <span style={{ fontSize: '12px' }}>{item}</span>
              </button>
            ))}
          </div>
        </div>

        {/* 하단 네비게이션 공간 확보 */}
        <div style={{ height: '80px' }}></div>
      </div>
    </>
  );
}

export async function getServerSideProps() {
  try {
    const base = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
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
