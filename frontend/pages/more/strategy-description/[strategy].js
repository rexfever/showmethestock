// 전략 상세 설명 페이지
import { useRouter } from 'next/router';
import Head from 'next/head';
import Layout from '../../../layouts/v2/Layout';

export default function StrategyDetail() {
  const router = useRouter();
  const { strategy } = router.query;

  const getStrategyContent = () => {
    if (strategy === 'midterm') {
      return {
        title: '중기 전략',
        gradient: 'from-indigo-600 via-purple-600 to-pink-600',
        iconGradient: 'from-indigo-500 to-purple-500',
        bgGradient: 'from-indigo-50 to-purple-50',
        icon: (
          <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
        ),
        features: [
          { label: '관찰 기간', value: '25거래일' },
          { label: '목표', value: '중기 추세 수익' },
          { label: '손절 기준', value: '-7.0%' }
        ],
        content: [
          {
            title: '전략 개요',
            text: '중기 추세 지속 및 재개 후보를 찾는 전략입니다.'
          },
          {
            title: '선택 기준',
            text: '이미 추세가 시작되었고, 아직 과열되지 않았으며, 다음 파동이 남아 있는 종목을 선택합니다.'
          },
          {
            title: '평가 지표',
            text: '추세 지표, 모멘텀 지표, 변동성 지표를 종합하여 평가합니다.'
          },
          {
            title: '투자 목표',
            text: '단기 수익률보다는 중기 추세 수익을 목표로 합니다.'
          }
        ]
      };
    } else if (strategy === 'v2') {
      return {
        title: '일일 추천 전략',
        gradient: 'from-blue-600 via-cyan-600 to-teal-600',
        iconGradient: 'from-blue-500 to-cyan-500',
        bgGradient: 'from-blue-50 to-cyan-50',
        icon: (
          <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
        ),
        features: [
          { label: '추천 방식', value: '매 거래일마다' },
          { label: '전략 유형', value: '스윙/포지션/장기' },
          { label: '점수 기준', value: '구성 기반 분류' }
        ],
        content: [
          {
            title: '전략 개요',
            text: '매 거래일마다 추천 종목을 제공하는 일일 추천 방식입니다. 점수 구성(모멘텀 vs 추세)에 따라 스윙, 포지션, 장기 전략으로 자동 분류됩니다.'
          },
          {
            title: '전략 분류',
            paragraphs: [
              '스윙(단기): 골든크로스 + 거래량 + 모멘텀 지표 중심, 목표 +5%, 손절 -5%, 보유 3~10일.',
              '포지션(중기): 골든크로스 + 추세 지표 중심, 목표 +10%, 손절 -7%, 보유 2주~3개월.',
              '장기: 추세 지표 중심, 목표 +15%, 손절 -10%, 보유 3개월 이상.'
            ]
          },
          {
            title: '평가 지표',
            text: '모멘텀 지표(골든크로스, 거래량, MACD, RSI)와 추세 지표(TEMA, OBV, 연속상승, DEMA)를 종합하여 평가합니다. 점수 합계가 아닌 점수 구성에 따라 전략이 결정됩니다.'
          },
          {
            title: '시장 조건',
            paragraphs: [
              '강세장과 중립장에서는 추천 종목을 제공합니다.',
              '약세장에서는 추천을 제공하지 않습니다.',
              '강세장 중 일시적으로 급락한 경우에도 추천을 제공할 수 있습니다.'
            ]
          }
        ]
      };
    } else if (strategy === 'v3') {
      return {
        title: '조건 추천 전략',
        gradient: 'from-blue-600 via-cyan-600 to-teal-600',
        iconGradient: 'from-blue-500 to-cyan-500',
        bgGradient: 'from-blue-50 to-cyan-50',
        icon: (
          <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
        ),
        features: [
          { label: '추천 방식', value: '조건 충족 시' },
          { label: '관리 방식', value: '상태 기반' },
          { label: '전략 유형', value: '중기/단기' }
        ],
        content: [
          {
            title: '전략 개요',
            text: '정해진 조건이 충족되었을 때만 추천 종목을 제공하는 조건 추천 방식입니다. 상태 기반으로 추천을 생성하고 관리합니다.'
          },
          {
            title: '추천 생성',
            text: '특정 조건이 충족되었을 때만 추천 종목을 표시합니다. 조건에 맞았다고 바로 표시하지 않고, 기준이 명확해졌을 때만 추천을 보여줍니다.'
          },
          {
            title: '관리 방식',
            text: '추천 종목은 상태 기반으로 관리됩니다. 상황 변화에 따라 추천이 종료되거나 관리 대상에서 제외될 수 있습니다.'
          },
          {
            title: '전략 구성',
            paragraphs: [
              '중기 전략: 25거래일 관찰 기간, 중기 추세 수익 목표, 손절 기준 -7.0%',
              '단기 전략: 15거래일 관찰 기간, 단기 스윙 목표, 손절 기준 -2.0%'
            ]
          }
        ]
      };
    } else if (strategy === 'v2lite') {
      return {
        title: '단기 전략',
        gradient: 'from-blue-600 via-cyan-600 to-teal-600',
        iconGradient: 'from-blue-500 to-cyan-500',
        bgGradient: 'from-blue-50 to-cyan-50',
        icon: (
          <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        ),
        features: [
          { label: '관찰 기간', value: '15거래일' },
          { label: '목표', value: '단기 스윙' },
          { label: '손절 기준', value: '-2.0%' }
        ],
        content: [
          {
            title: '전략 개요',
            text: '눌림목 전략을 기반으로 한 단순화된 검색기입니다.'
          },
          {
            title: '단순화',
            text: '기존 전략을 단순화하여 필수 지표만 사용합니다.'
          },
          {
            title: '평가 지표',
            text: '추세 지표와 모멘텀 지표를 활용하여 진입 시점을 판단합니다.'
          },
          {
            title: '투자 목표',
            text: '단기 스윙을 목표로 합니다.'
          }
        ]
      };
    }
    return null;
  };

  const strategyData = getStrategyContent();

  if (!strategyData) {
    return (
      <>
        <Head>
          <title>전략 설명 - 스톡인사이트</title>
        </Head>
        <Layout headerTitle="전략 설명">
          <div className="p-4">
            <p className="text-gray-600">전략을 찾을 수 없습니다.</p>
          </div>
        </Layout>
      </>
    );
  }

  return (
    <>
      <Head>
        <title>{strategyData.title} - 스톡인사이트</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      </Head>

      <Layout headerTitle="스톡인사이트">
        {/* 정보 배너 - 개선된 그라데이션 */}
        <div className={`relative bg-gradient-to-br ${strategyData.gradient} text-white overflow-hidden`}>
          {/* 배경 패턴 */}
          <div className="absolute inset-0 opacity-10">
            <div className="absolute inset-0" style={{
              backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
            }}></div>
          </div>
          
          <div className="relative p-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold mb-1">
                  {strategyData.title}
                </h2>
                <p className="text-sm opacity-90">
                  전략 상세 설명 및 특징
                </p>
              </div>
              <div className="hidden sm:block">
                <div className="w-16 h-16 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center">
                  {strategyData.icon}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 메인 컨텐츠 */}
        <div className="bg-gradient-to-b from-gray-50 via-gray-50 to-white min-h-screen">
          <div className="px-4 py-6">
            {/* 뒤로가기 버튼 */}
            <button
              onClick={() => router.back()}
              className="mb-6 flex items-center text-gray-600 hover:text-gray-900 transition-colors group"
            >
              <svg
                className="w-5 h-5 mr-2 transform group-hover:-translate-x-1 transition-transform"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              <span className="text-sm font-medium">뒤로가기</span>
            </button>

            {/* 주요 특징 */}
            <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6 mb-6">
              <h3 className="text-xl font-bold text-gray-900 mb-4">
                주요 특징
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {strategyData.features.map((feature, index) => (
                  <div key={index} className="text-center sm:text-left">
                    <div className="text-sm text-gray-500 mb-1">{feature.label}</div>
                    <div className="text-lg font-semibold text-gray-900">{feature.value}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* 상세 설명 */}
            <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6">
              <h3 className="text-xl font-bold text-gray-900 mb-6">
                상세 설명
              </h3>
              <div className="space-y-6">
                {strategyData.content.map((section, index) => (
                  <div 
                    key={index} 
                    className={`relative bg-gradient-to-br ${strategyData.bgGradient} rounded-xl p-5 border border-gray-100 ${index !== strategyData.content.length - 1 ? 'mb-6' : ''}`}
                  >
                    {/* 번호 배지 */}
                    <div className={`absolute -top-3 -left-3 w-8 h-8 rounded-full bg-gradient-to-br ${strategyData.iconGradient} flex items-center justify-center text-white text-sm font-bold shadow-lg`}>
                      {index + 1}
                    </div>
                    
                    {/* 제목 */}
                    <h4 className="text-gray-900 font-semibold text-lg mb-3 pl-6">
                      {section.title}
                    </h4>
                    
                    {/* 내용 */}
                    {section.paragraphs ? (
                      <div className="space-y-3 pl-6">
                        {section.paragraphs.map((paragraph, pIndex) => {
                          // 전략명 강조 처리 (V2: 스윙, 포지션, 장기 / V3: 중기 전략, 단기 전략)
                          const parts = paragraph.split(/(스윙\(단기\)|포지션\(중기\)|장기|중기 전략|단기 전략)/);
                          return (
                            <div key={pIndex} className="flex items-start">
                              <div className={`flex-shrink-0 w-1.5 h-1.5 rounded-full bg-gradient-to-br ${strategyData.iconGradient} mt-2 mr-3`}></div>
                              <p className="text-gray-700 leading-relaxed text-base flex-1">
                                {parts.map((part, partIndex) => {
                                  if (part === '스윙(단기)' || part === '포지션(중기)' || part === '장기' || part === '중기 전략' || part === '단기 전략') {
                                    return (
                                      <span key={partIndex} className="font-bold text-gray-900">
                                        {part}
                                      </span>
                                    );
                                  }
                                  return <span key={partIndex}>{part}</span>;
                                })}
                              </p>
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      <p className="text-gray-700 leading-relaxed text-base pl-6">
                        {section.text}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
            
            {/* 하단 여백 */}
            <div className="h-8"></div>
          </div>
        </div>
      </Layout>
    </>
  );
}

