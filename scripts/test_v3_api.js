#!/usr/bin/env node
/**
 * V3 API 브라우저 테스트용 검증 스크립트
 * 
 * 사용법:
 *   node scripts/test_v3_api.js
 */

const http = require('http');

const BASE_URL = process.env.BACKEND_URL || 'http://localhost:8010';

function makeRequest(path) {
  return new Promise((resolve, reject) => {
    const url = new URL(path, BASE_URL);
    
    http.get(url, (res) => {
      let data = '';
      
      res.on('data', (chunk) => {
        data += chunk;
      });
      
      res.on('end', () => {
        try {
          const json = JSON.parse(data);
          resolve({ status: res.statusCode, data: json });
        } catch (e) {
          reject(new Error(`JSON 파싱 오류: ${e.message}`));
        }
      });
    }).on('error', (err) => {
      reject(err);
    });
  });
}

async function testV3APIs() {
  console.log('🧪 V3 API 테스트 시작...\n');
  console.log(`📍 Base URL: ${BASE_URL}\n`);

  const tests = [
    {
      name: 'ACTIVE 추천 조회',
      path: '/api/v3/recommendations/active',
      checks: [
        (data) => data.ok === true,
        (data) => Array.isArray(data.data?.items),
        (data) => typeof data.data?.count === 'number',
        (data) => data.daily_digest !== undefined,
        (data) => typeof data.daily_digest?.window === 'string',
        (data) => typeof data.daily_digest?.has_changes === 'boolean',
        (data) => typeof data.daily_digest?.new_recommendations === 'number',
        (data) => typeof data.daily_digest?.new_broken === 'number',
        (data) => typeof data.daily_digest?.new_archived === 'number',
      ]
    },
    {
      name: 'Needs Attention 추천 조회',
      path: '/api/v3/recommendations/needs-attention',
      checks: [
        (data) => data.ok === true,
        (data) => Array.isArray(data.data?.items),
        (data) => typeof data.data?.count === 'number',
      ]
    },
    {
      name: 'ARCHIVED 추천 조회',
      path: '/api/v3/recommendations/archived',
      checks: [
        (data) => data.ok === true,
        (data) => Array.isArray(data.data?.items),
        (data) => typeof data.data?.count === 'number',
      ]
    }
  ];

  let passed = 0;
  let failed = 0;

  for (const test of tests) {
    console.log(`\n📋 테스트: ${test.name}`);
    console.log(`   경로: ${test.path}`);
    
    try {
      const result = await makeRequest(test.path);
      
      if (result.status !== 200) {
        console.log(`   ❌ HTTP 상태 코드: ${result.status}`);
        failed++;
        continue;
      }

      console.log(`   ✅ HTTP 상태 코드: ${result.status}`);
      
      // daily_digest 검증 (ACTIVE API만)
      if (test.path.includes('/active') && result.data.daily_digest) {
        const digest = result.data.daily_digest;
        console.log(`   📊 daily_digest:`);
        console.log(`      - window: ${digest.window}`);
        console.log(`      - has_changes: ${digest.has_changes}`);
        console.log(`      - new_recommendations: ${digest.new_recommendations}`);
        console.log(`      - new_broken: ${digest.new_broken}`);
        console.log(`      - new_archived: ${digest.new_archived}`);
      }

      // 체크 실행
      let allPassed = true;
      for (let i = 0; i < test.checks.length; i++) {
        const check = test.checks[i];
        const checkResult = check(result.data);
        
        if (!checkResult) {
          console.log(`   ❌ 체크 ${i + 1} 실패`);
          allPassed = false;
        }
      }

      if (allPassed) {
        console.log(`   ✅ 모든 체크 통과`);
        passed++;
      } else {
        console.log(`   ❌ 일부 체크 실패`);
        failed++;
      }

      // 아이템 샘플 출력
      if (result.data.data?.items?.length > 0) {
        const sample = result.data.data.items[0];
        console.log(`   📦 샘플 아이템:`);
        console.log(`      - ticker: ${sample.ticker}`);
        console.log(`      - name: ${sample.name || '(없음)'}`);
        console.log(`      - status: ${sample.status}`);
        if (sample.archive_return_pct !== undefined) {
          console.log(`      - archive_return_pct: ${sample.archive_return_pct}`);
        }
      }

    } catch (error) {
      console.log(`   ❌ 오류: ${error.message}`);
      failed++;
    }
  }

  console.log(`\n\n📊 테스트 결과:`);
  console.log(`   ✅ 통과: ${passed}`);
  console.log(`   ❌ 실패: ${failed}`);
  console.log(`   총계: ${passed + failed}`);

  if (failed === 0) {
    console.log(`\n🎉 모든 테스트 통과!`);
    process.exit(0);
  } else {
    console.log(`\n⚠️  일부 테스트 실패`);
    process.exit(1);
  }
}

// 실행
testV3APIs().catch((error) => {
  console.error('❌ 테스트 실행 오류:', error);
  process.exit(1);
});


