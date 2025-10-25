import { useState, useEffect, useCallback } from 'react';
import Head from 'next/head';
import { useRouter } from 'next/router';
import { useAuth } from '../contexts/AuthContext';
import getConfig from '../config';
import Header from '../components/Header';
import BottomNavigation from '../components/BottomNavigation';

export default function CustomerScanner({ initialData, initialScanFile, initialScanDate }) {
  const router = useRouter();

  // 공사중 페이지로 리다이렉트
  useEffect(() => {
    let countdown = 3;
    const countdownElement = document.getElementById('countdown');
    
    // 카운트다운 표시
    const countdownInterval = setInterval(() => {
      countdown--;
      if (countdownElement) {
        countdownElement.textContent = countdown;
      }
      if (countdown <= 0) {
        clearInterval(countdownInterval);
        router.push('/');
      }
    }, 1000);
    
    return () => clearInterval(countdownInterval);
  }, [router]);






  return (
    <>
      <Head>
        <title>스톡인사이트 - 서비스 점검 중</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <meta name="format-detection" content="telephone=no" />
        <meta name="mobile-web-app-capable" content="yes" />
      </Head>

      <div className="min-h-screen bg-gradient-to-br from-orange-400 to-red-500 flex items-center justify-center">
        <div className="bg-white rounded-2xl shadow-2xl p-8 mx-4 max-w-md w-full text-center">
          {/* 공사 아이콘 */}
          <div className="text-6xl mb-6">🚧</div>
          
          {/* 제목 */}
          <h1 className="text-2xl font-bold text-gray-800 mb-4">
            서비스 점검 중
          </h1>
          
          {/* 메시지 */}
          <div className="text-gray-600 mb-6 space-y-2">
            <p className="text-lg font-medium">
              서버 이슈로 인해
            </p>
            <p className="text-lg font-bold text-red-600">
              2025년 10월 24일
            </p>
            <p className="text-lg font-medium">
              서비스가 제공되지 않습니다.
            </p>
            <p className="text-sm text-gray-500 mt-4">
              이용에 불편을 드려 죄송합니다.
            </p>
          </div>
          
          {/* 카운트다운 */}
          <div className="bg-gray-100 rounded-lg p-4 mb-6">
            <p className="text-sm text-gray-600 mb-2">잠시 후 메인 페이지로 이동합니다</p>
            <div className="text-2xl font-bold text-blue-600" id="countdown">3</div>
          </div>
          
          {/* 수동 이동 버튼 */}
          <button
            onClick={() => router.push('/')}
            className="w-full bg-blue-500 hover:bg-blue-600 text-white font-bold py-3 px-6 rounded-lg transition-colors duration-200"
          >
            메인 페이지로 이동
          </button>
        </div>
      </div>
    </>
  );
}

export async function getServerSideProps() {
  try {
    // 서버에서 백엔드 API 호출 (DB 직접 조회)
    const config = getConfig();
    const base = config.backendUrl;
    const response = await fetch(`${base}/latest-scan`);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
      const data = await response.json();
      
      if (data.ok && data.data) {
        // items 또는 rank 필드 처리
        const items = data.data.items || data.data.rank || [];
        // 날짜 표시는 스캔 응답의 as_of(YYYY-MM-DD) 우선 사용하되, 표시용으로 YYYYMMDD로 변환
        const rawAsOf = data.data.as_of || '';
        const normalizedScanDate = (data.data.scan_date) || (rawAsOf ? rawAsOf.replace(/-/g, '') : '');
        return {
          props: {
            initialData: items,
            initialScanFile: data.file || '',
            initialScanDate: normalizedScanDate
          }
        };
      }
  } catch (error) {
  }
  
  return {
    props: {
      initialData: [],
      initialScanDate: ''
    }
  };
}
