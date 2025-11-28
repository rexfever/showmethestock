/**
 * 모든 테스트 실행 스크립트
 * 
 * 사용법:
 *   node frontend/__tests__/run-all-tests.js
 * 
 * 또는 Jest로 직접 실행:
 *   npm test
 *   npm test -- --coverage
 */

const { execSync } = require('child_process');
const path = require('path');

console.log('🧪 프론트엔드 테스트 실행 시작...\n');

try {
  // Jest 실행
  const jestCommand = 'npm test -- --coverage --verbose';
  
  console.log('📋 실행 명령:', jestCommand);
  console.log('─'.repeat(50));
  
  execSync(jestCommand, {
    cwd: path.join(__dirname, '..'),
    stdio: 'inherit',
    env: {
      ...process.env,
      NODE_ENV: 'test',
    },
  });
  
  console.log('\n✅ 모든 테스트가 성공적으로 완료되었습니다!');
} catch (error) {
  console.error('\n❌ 테스트 실행 중 오류가 발생했습니다:', error.message);
  process.exit(1);
}


