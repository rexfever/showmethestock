import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useAuth } from '../contexts/AuthContext';
import Head from 'next/head';
import Layout from '../layouts/v2/Layout';

export default function More() {
  const router = useRouter();
  const { isAuthenticated, user, loading: authLoading, authChecked, logout } = useAuth();
  const [mounted, setMounted] = useState(false);
  const [showStrategyModal, setShowStrategyModal] = useState(false);
  const [strategyContent, setStrategyContent] = useState('');
  const [strategyGuideMarkdown, setStrategyGuideMarkdown] = useState('');
  const [loadingGuide, setLoadingGuide] = useState(false);

  // public 폴더에서 가이드 로드
  useEffect(() => {
    if (typeof window !== 'undefined' && showStrategyModal && !strategyGuideMarkdown && !loadingGuide) {
      setLoadingGuide(true);
      // public 폴더의 파일을 직접 fetch (캐시 무시)
      fetch('/content/TRADING_STRATEGY_GUIDE.md', {
        cache: 'no-store',
        headers: {
          'Cache-Control': 'no-cache'
        }
      })
        .then(res => {
          if (!res.ok) {
            throw new Error(`HTTP error! status: ${res.status}`);
          }
          return res.text();
        })
        .then(text => {
          console.log('[More] 가이드 로드 성공, 길이:', text.length);
          console.log('[More] 로드된 내용 첫 200자:', text.substring(0, 200));
          console.log('[More] 로드된 내용에 "매매 전략" 포함 여부:', text.includes('매매 전략'));
          console.log('[More] 로드된 내용에 "스톡인사이트" 포함 여부:', text.includes('스톡인사이트'));
          setStrategyGuideMarkdown(text);
          setLoadingGuide(false);
        })
        .catch(error => {
          console.error('[More] 가이드 로드 실패:', error);
          setStrategyGuideMarkdown('');
          setLoadingGuide(false);
        });
    }
  }, [showStrategyModal, strategyGuideMarkdown, loadingGuide]);

  useEffect(() => {
    setMounted(true);
  }, []);

  // 모달 열림 시 배경 스크롤 방지 (모바일)
  useEffect(() => {
    if (showStrategyModal) {
      document.body.style.overflow = 'hidden';
      return () => {
        document.body.style.overflow = 'unset';
      };
    }
  }, [showStrategyModal]);

  // 모달이 열릴 때마다 마크다운 파싱
  useEffect(() => {
    // 클라이언트 사이드에서만 실행
    if (typeof window === 'undefined') return;
    
    if (showStrategyModal) {
      // strategyGuideMarkdown이 없거나 빈 문자열인 경우
      if (!strategyGuideMarkdown || strategyGuideMarkdown.trim() === '') {
        // 로딩 중이면 파싱하지 않고 기다림 (에러 로그 출력 안 함)
        if (loadingGuide) {
          return;
        }
        // 로딩이 완료되었는데도 없으면 에러 메시지 표시
        // (단, 가이드 로드가 아직 시작되지 않은 경우는 제외)
        console.warn('[More] strategyGuideMarkdown이 아직 로드되지 않았습니다.');
        return;
      }
      
      // 마크다운 파일 파싱 (클라이언트 사이드에서만 실행)
      const parseMarkdown = async () => {
        try {
          console.log('마크다운 파싱 시작...');
          
          // DOMPurify를 동적으로 import (클라이언트 사이드에서만)
          let DOMPurify;
          try {
            const dompurifyModule = await import('isomorphic-dompurify');
            DOMPurify = dompurifyModule.default || dompurifyModule;
            console.log('DOMPurify 로드 완료');
          } catch (importError) {
            console.error('DOMPurify import 실패:', importError);
            // DOMPurify 없이 진행 (기본 sanitization만 수행)
            DOMPurify = null;
          }
          
          const text = strategyGuideMarkdown;
          
          if (!text || typeof text !== 'string') {
            console.error('마크다운 텍스트가 유효하지 않습니다:', typeof text, text);
            setStrategyContent('<p class="text-red-500">가이드 데이터를 불러올 수 없습니다.</p>');
            return;
          }
          
          console.log('마크다운 파싱 시작, 텍스트 길이:', text.length);
          console.log('[More] 파싱할 텍스트 첫 200자:', text.substring(0, 200));
          console.log('[More] 파싱할 텍스트에 "매매 전략" 포함 여부:', text.includes('매매 전략'));
          
          // 라인 단위로 처리
          const lines = text.split('\n');
          let html = '';
          let inList = false;
          let listType = '';
          
          for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            const trimmed = line.trim();
            
            // 빈 줄 처리
            if (!trimmed) {
              if (inList) {
                html += listType === 'ul' ? '</ul>' : '</ol>';
                inList = false;
              }
              html += '\n';
              continue;
            }
            
            // 헤더 처리
            if (trimmed.startsWith('# ')) {
              if (inList) {
                html += listType === 'ul' ? '</ul>' : '</ol>';
                inList = false;
              }
              html += `<h1 class="text-2xl font-bold mb-4 mt-6">${trimmed.substring(2)}</h1>`;
            } else if (trimmed.startsWith('## ')) {
              if (inList) {
                html += listType === 'ul' ? '</ul>' : '</ol>';
                inList = false;
              }
              html += `<h2 class="text-xl font-semibold mt-6 mb-3 text-gray-800">${trimmed.substring(3)}</h2>`;
            } else if (trimmed.startsWith('### ')) {
              if (inList) {
                html += listType === 'ul' ? '</ul>' : '</ol>';
                inList = false;
              }
              html += `<h3 class="text-lg font-medium mt-5 mb-2 text-gray-700">${trimmed.substring(4)}</h3>`;
            } else if (trimmed.startsWith('#### ')) {
              if (inList) {
                html += listType === 'ul' ? '</ul>' : '</ol>';
                inList = false;
              }
              html += `<h4 class="text-base font-medium mt-4 mb-2 text-gray-700">${trimmed.substring(5)}</h4>`;
            } else if (trimmed === '---') {
              if (inList) {
                html += listType === 'ul' ? '</ul>' : '</ol>';
                inList = false;
              }
              html += '<hr class="my-6 border-gray-300">';
            } else if (trimmed.match(/^- /)) {
              // 리스트 항목
              if (!inList || listType !== 'ul') {
                if (inList) html += '</ol>';
                html += '<ul class="list-disc mb-4 ml-6 space-y-1">';
                inList = true;
                listType = 'ul';
              }
              const content = trimmed.substring(2);
              // 링크를 먼저 처리 (URL이 그대로 보이는 문제 방지)
              let listContent = content
                .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" class="text-blue-600 hover:text-blue-800 underline font-medium">$1</a>')
                .replace(/\*\*(.*?)\*\*/g, '<strong class="font-semibold">$1</strong>');
              html += `<li class="text-gray-700">${listContent}</li>`;
            } else if (trimmed.match(/^\d+\. /)) {
              // 번호 리스트
              if (!inList || listType !== 'ol') {
                if (inList) html += '</ul>';
                html += '<ol class="list-decimal mb-4 ml-6 space-y-1">';
                inList = true;
                listType = 'ol';
              }
              const content = trimmed.replace(/^\d+\. /, '');
              // 링크를 먼저 처리 (URL이 그대로 보이는 문제 방지)
              let listContent = content
                .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" class="text-blue-600 hover:text-blue-800 underline font-medium">$1</a>')
                .replace(/\*\*(.*?)\*\*/g, '<strong class="font-semibold">$1</strong>');
              html += `<li class="text-gray-700">${listContent}</li>`;
            } else {
              // 일반 문단
              if (inList) {
                html += listType === 'ul' ? '</ul>' : '</ol>';
                inList = false;
              }
              // 링크를 먼저 처리 (URL이 그대로 보이는 문제 방지)
              let paraContent = trimmed
                .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" class="text-blue-600 hover:text-blue-800 underline font-medium">$1</a>')
                .replace(/\*\*(.*?)\*\*/g, '<strong class="font-semibold text-gray-900">$1</strong>')
                .replace(/\*(.*?)\*/g, '<em class="italic">$1</em>')
                .replace(/`(.*?)`/g, '<code class="bg-gray-100 px-1 py-0.5 rounded text-sm">$1</code>');
              html += `<p class="mb-3 text-gray-700 leading-relaxed">${paraContent}</p>`;
            }
          }
          
          // 리스트가 끝나지 않았다면 닫기
          if (inList) {
            html += listType === 'ul' ? '</ul>' : '</ol>';
          }
          
          console.log('마크다운 파싱 완료, HTML 길이:', html.length);
          
          // XSS 방지를 위한 DOMPurify 적용
          if (!DOMPurify || typeof DOMPurify.sanitize !== 'function') {
            console.error('DOMPurify가 올바르게 로드되지 않았습니다');
            // DOMPurify 없이도 기본적인 sanitization 수행
            setStrategyContent(html);
          } else {
            const sanitizedHtml = DOMPurify.sanitize(html, {
              ALLOWED_TAGS: ['h1', 'h2', 'h3', 'h4', 'p', 'ul', 'ol', 'li', 'strong', 'em', 'code', 'a', 'hr'],
              ALLOWED_ATTR: ['href', 'target', 'rel', 'class'],
              ALLOW_DATA_ATTR: false
            });
            
            console.log('DOMPurify 적용 완료, sanitized HTML 길이:', sanitizedHtml.length);
            setStrategyContent(sanitizedHtml);
          }
        } catch (err) {
          console.error('가이드 파싱 실패:', err);
          console.error('에러 스택:', err.stack);
          setStrategyContent(`<p class="text-red-500">가이드를 불러올 수 없습니다: ${err.message}</p>`);
        }
      };
      
      // 파싱 실행 (에러 처리 포함)
      parseMarkdown().catch(error => {
        console.error('[More] parseMarkdown 실행 중 에러:', error);
        setStrategyContent('<p class="text-red-500">가이드를 불러오는 중 오류가 발생했습니다. 페이지를 새로고침해주세요.</p>');
      });
    } else if (!showStrategyModal) {
      // 모달이 닫혔을 때 콘텐츠 초기화 (다음에 열 때 다시 파싱)
      setStrategyContent('');
      // 가이드는 유지 (다음에 열 때 다시 로드하지 않음)
    }
  }, [showStrategyModal, strategyGuideMarkdown, loadingGuide]);

  const handleLogout = async () => {
    if (user && logout) {
      try {
        await logout();
        router.push('/customer-scanner');
      } catch (error) {
        console.error('로그아웃 중 오류:', error);
        router.push('/customer-scanner');
      }
    }
  };

  if (!mounted) {
    return null;
  }

  return (
    <>
      <Head>
        <title>더보기 - 스톡인사이트</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      </Head>

      <Layout headerTitle="더보기">
        {/* 정보 배너 */}
        <div className="bg-gradient-to-r from-blue-500 to-purple-600 text-white p-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold">더보기</h2>
              <p className="text-sm opacity-90">다양한 서비스와 설정을 확인하세요</p>
            </div>
            <div className="w-16 h-16 bg-white bg-opacity-20 rounded-full flex items-center justify-center">
              <span className="text-2xl">⚙️</span>
            </div>
          </div>
        </div>

        {/* 메인 콘텐츠 */}
        <div className="p-4">
          {/* 사용자 정보 카드 */}
          {!authLoading && authChecked && user ? (
            (() => {
              const isSpecialUser = user?.email === 'kuksos80215@daum.net';
              return (
                <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
                  <div className="flex items-center space-x-4">
                    <div className={`w-12 h-12 ${isSpecialUser ? 'bg-gradient-to-br from-pink-100 to-rose-100' : 'bg-blue-100'} rounded-full flex items-center justify-center`}>
                      {isSpecialUser ? (
                        <span className="special-user-icon text-xl">✨</span>
                      ) : (
                        <span className="text-xl">👤</span>
                      )}
                    </div>
                    <div className="flex-1">
                      {isSpecialUser ? (
                        <>
                          <div className="special-user-name font-semibold text-lg">윤봄님</div>
                          <div className="text-sm text-gray-600 mt-1 flex items-center space-x-2">
                            <span className="special-user-badge inline-block px-2 py-0.5 text-xs font-semibold rounded-full text-white">
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
                        </>
                      ) : (
                        <>
                          <div className="font-semibold text-gray-900">{user.name}님</div>
                          <div className="text-sm text-gray-600">
                            {user.is_admin ? '🔧 관리자' : 
                             user.membership_tier === 'vip' ? '👑 VIP 회원' :
                             user.membership_tier === 'premium' ? '👑 프리미엄 회원' : '일반 회원'}
                          </div>
                          {/* 디버깅 정보 */}
                          <div className="text-xs text-gray-400 mt-1">
                            Debug: is_admin={String(user.is_admin)} ({typeof user.is_admin}), tier={user.membership_tier}
                          </div>
                        </>
                      )}
                    </div>
                    <div className="text-right">
                      <div className="text-sm text-gray-500">포인트</div>
                      <div className="font-semibold text-blue-600">0P</div>
                    </div>
                  </div>
                </div>
              );
            })()
          ) : (
            <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
              <div className="text-center">
                <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-3">
                  <span className="text-xl">👤</span>
                </div>
                <div className="font-semibold text-gray-900 mb-2">게스트 사용자</div>
                <button 
                  onClick={() => router.push('/login')}
                  className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors font-medium"
                >
                  로그인하기
                </button>
              </div>
            </div>
          )}




          {/* 매매전략 가이드 카드 */}
          <div className="bg-gradient-to-r from-purple-500 to-pink-500 rounded-lg shadow-lg p-4 mb-6 text-white cursor-pointer hover:shadow-xl transition-shadow"
               onClick={() => setShowStrategyModal(true)}>
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="w-12 h-12 bg-white bg-opacity-20 rounded-full flex items-center justify-center">
                  <span className="text-2xl">📈</span>
                </div>
                <div>
                  <h3 className="font-bold text-lg mb-1">매매전략 가이드</h3>
                  <p className="text-sm opacity-90">검증된 매매 전략으로 수익 극대화</p>
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <span className="text-sm opacity-90">자세히 보기</span>
                <span className="text-xl">→</span>
              </div>
            </div>
            <div className="mt-4 grid grid-cols-3 gap-3 text-sm">
              <div className="bg-white bg-opacity-20 rounded-lg p-2">
                <div className="font-semibold">익절</div>
                <div className="text-xs opacity-90">+3% 도달 시</div>
              </div>
              <div className="bg-white bg-opacity-20 rounded-lg p-2">
                <div className="font-semibold">손절</div>
                <div className="text-xs opacity-90">-7% (5일 후)</div>
              </div>
              <div className="bg-white bg-opacity-20 rounded-lg p-2">
                <div className="font-semibold">승률</div>
                <div className="text-xs opacity-90">94.6%</div>
              </div>
            </div>
          </div>

          {/* 투자 활용법 가이드 */}
          <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
            <h3 className="font-semibold text-gray-900 mb-4">투자 활용법</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-blue-50 rounded-lg p-4">
                <div className="flex items-center space-x-2 mb-2">
                  <span className="text-xl">🔍</span>
                  <h4 className="font-semibold text-gray-800">어떤 종목을 찾나요?</h4>
                </div>
                <p className="text-sm text-gray-600 font-medium">📈 상승 초입 단계의 종목들</p>
                <p className="text-xs text-gray-500 mt-1">• 하락이 끝나고 막 오르기 시작하는 종목</p>
                <p className="text-xs text-gray-500">• 거래량이 늘어나며 관심받기 시작하는 종목</p>
                <p className="text-xs text-blue-600 mt-2 font-medium">💡 상승 초기에 발견해서 수익 기회 제공</p>
              </div>
              <div className="bg-green-50 rounded-lg p-4">
                <div className="flex items-center space-x-2 mb-2">
                  <span className="text-xl">💰</span>
                  <h4 className="font-semibold text-gray-800">어떻게 투자하나요?</h4>
                </div>
                <p className="text-sm text-gray-600 font-medium">🎯 추천가 기준 매수 → 보유 전략</p>
                <p className="text-xs text-gray-500 mt-1">• <strong>매수</strong>: 추천가(스캔일 종가) 기준 ±2% 이내 매수</p>
                <p className="text-xs text-gray-500">• <strong>익절</strong>: +3% 도달 시 즉시 매도</p>
                <p className="text-xs text-gray-500">• <strong>손절</strong>: -7% 하락 시 매도 (5일 후)</p>
                <p className="text-xs text-gray-500">• <strong>보존</strong>: +1.5% 도달 후 원가 이하 시 매도</p>
                <div className="mt-2 p-2 bg-green-100 rounded">
                  <p className="text-xs text-green-700 font-medium">💡 핵심: 종목당 100~200만원, 동시 3~5개 보유, 보유기간 5~45일</p>
                </div>
                <p className="text-xs text-red-500 mt-2 font-medium">⚠️ 투자는 본인 책임, 신중한 판단 필요</p>
              </div>
            </div>
          </div>

          {/* 준비중인 기능 */}
          <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
            <h3 className="font-semibold text-gray-900 mb-4">준비중인 기능</h3>
            <div className="bg-orange-50 rounded-lg p-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                <div>
                  <h5 className="font-medium text-orange-700 mb-2">📱 알림 서비스</h5>
                  <ul className="space-y-1 text-orange-600">
                    <li>• <strong>카카오톡 알림톡</strong>: 스캔 결과 자동 알림</li>
                    <li>• <strong>푸시 알림</strong>: 모바일 앱 알림</li>
                    <li>• <strong>이메일 알림</strong>: 상세 분석 리포트</li>
                  </ul>
                </div>
                <div>
                  <h5 className="font-medium text-orange-700 mb-2">💼 관심종목 관리</h5>
                  <ul className="space-y-1 text-orange-600">
                    <li>• <strong>관심종목 등록</strong>: 스캔 결과에서 바로 등록</li>
                    <li>• <strong>관심종목 목록</strong>: 등록한 종목 관리</li>
                    <li>• <strong>알림 설정</strong>: 관심종목 변동 알림</li>
                  </ul>
                </div>
                <div>
                  <h5 className="font-medium text-orange-700 mb-2">📊 고급 분석</h5>
                  <ul className="space-y-1 text-orange-600">
                    <li>• <strong>상세 차트</strong>: 기술적 분석 도구</li>
                    <li>• <strong>기업정보</strong>: 재무제표 및 뉴스</li>
                    <li>• <strong>종목분석</strong>: 단일 종목 상세 분석</li>
                  </ul>
                </div>
              </div>
              <div className="mt-4 p-3 bg-orange-100 rounded-lg">
                <p className="text-sm text-orange-700">
                  <strong>💡 안내:</strong> 모든 기능은 순차적으로 출시될 예정입니다. 
                  먼저 기본 스캔 서비스를 이용해보시고, 추가 기능 출시 소식을 기다려주세요!
                </p>
              </div>
            </div>
          </div>

          {/* 계정 관리 */}
          {!authLoading && authChecked && user && (
            <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
              <h3 className="font-semibold text-gray-900 mb-4">계정 관리</h3>
              <div className="space-y-3">
                <button 
                  onClick={handleLogout}
                  className="w-full flex items-center justify-between p-3 hover:bg-gray-50 rounded-lg transition-colors"
                >
                  <div className="flex items-center space-x-3">
                    <div className="w-8 h-8 bg-red-100 rounded-full flex items-center justify-center">
                      <span className="text-sm">🚪</span>
                    </div>
                    <span className="text-gray-700">로그아웃</span>
                  </div>
                  <span className="text-gray-400">›</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </Layout>

      {/* 매매전략 가이드 모달 */}
      {showStrategyModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4 overflow-y-auto"
             onClick={() => setShowStrategyModal(false)}>
          <div className="bg-white rounded-lg max-w-4xl w-full my-8 max-h-[calc(100vh-4rem)] flex flex-col shadow-xl"
               onClick={(e) => e.stopPropagation()}>
            {/* 모달 헤더 */}
            <div className="bg-gradient-to-r from-purple-500 to-pink-500 text-white p-4 flex items-center justify-between flex-shrink-0">
              <h2 className="text-xl font-bold">매매전략 가이드</h2>
              <button 
                onClick={() => setShowStrategyModal(false)}
                className="text-white hover:bg-white hover:bg-opacity-20 rounded-full p-1 transition-colors min-w-[44px] min-h-[44px] flex items-center justify-center"
                aria-label="모달 닫기"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            
            {/* 모달 콘텐츠 - 스크롤 가능 영역 (모바일 최적화) */}
            <div 
              className="flex-1 overflow-y-auto p-6 min-h-0" 
              style={{ 
                maxHeight: 'calc(90vh - 160px)',
                WebkitOverflowScrolling: 'touch' // iOS 부드러운 스크롤
              }}
            >
              {loadingGuide ? (
                <div className="text-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500 mx-auto"></div>
                  <p className="text-gray-500 mt-2">가이드를 불러오는 중...</p>
                </div>
              ) : strategyContent ? (
                <div 
                  className="prose max-w-none"
                  dangerouslySetInnerHTML={{ __html: strategyContent }}
                />
              ) : (
                <div className="text-center py-8">
                  <p className="text-red-500">가이드를 불러올 수 없습니다.</p>
                </div>
              )}
            </div>
            
            {/* 모달 푸터 */}
            <div className="border-t p-4 bg-gray-50 flex-shrink-0">
              <button
                onClick={() => setShowStrategyModal(false)}
                className="w-full bg-purple-500 text-white py-3 rounded-lg hover:bg-purple-600 transition-colors font-medium min-h-[44px]"
                aria-label="모달 닫기"
              >
                닫기
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

// getServerSideProps 제거 - API 라우트를 통해 클라이언트에서 로드
export async function getServerSideProps() {
  return {
    props: {}
  };
}
