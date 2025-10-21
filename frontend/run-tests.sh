#!/bin/bash

# 테스트 실행 스크립트

echo "🧪 테스트 환경 설정 중..."

# 의존성 설치
echo "📦 테스트 의존성 설치 중..."
npm install

echo "🔧 Jest 설정 확인 중..."

# 테스트 실행
echo "🚀 테스트 실행 중..."
echo ""

echo "📋 유틸리티 함수 테스트"
npm test -- __tests__/utils/ --verbose

echo ""
echo "🔧 서비스 함수 테스트"
npm test -- __tests__/services/ --verbose

echo ""
echo "🎨 컴포넌트 테스트"
npm test -- __tests__/components/ --verbose

echo ""
echo "🔄 통합 테스트"
npm test -- __tests__/integration/ --verbose

echo ""
echo "📊 전체 테스트 커버리지"
npm run test:coverage

echo ""
echo "✅ 테스트 완료!"












