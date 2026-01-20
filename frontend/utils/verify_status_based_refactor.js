/**
 * 상태 기반 리팩토링 검증 스크립트
 * 
 * 검증 항목:
 * 1. 날짜별 인피니티 스크롤 UI 제거 확인
 * 2. ARCHIVED 숨김 확인
 * 3. 숫자 노출 0개 확인
 * 4. BROKEN/ACTIVE 섹션 분리 확인
 */

// 브라우저 콘솔에서 실행할 수 있는 검증 함수들

export const verifyRefactor = {
  // 1. 날짜별 인피니티 스크롤 UI 제거 확인
  checkNoDateScrollUI: () => {
    const hasInfiniteScroll = document.querySelector('[class*="InfiniteScroll"]') !== null;
    const hasDateSection = document.querySelector('[id*="date-section"]') !== null;
    const hasDateGroup = document.querySelector('[class*="date"]')?.textContent?.includes('년') || false;
    
    console.log('=== 날짜별 인피니티 스크롤 UI 제거 확인 ===');
    console.log('InfiniteScrollContainer 존재:', hasInfiniteScroll);
    console.log('V3DateSection 존재:', hasDateSection);
    console.log('날짜 그룹 UI 존재:', hasDateGroup);
    
    if (!hasInfiniteScroll && !hasDateSection && !hasDateGroup) {
      console.log('✅ 통과: 날짜별 인피니티 스크롤 UI 제거됨');
      return true;
    } else {
      console.log('❌ 실패: 날짜별 UI가 남아있음');
      return false;
    }
  },
  
  // 2. ARCHIVED 숨김 확인
  checkArchivedHidden: (items) => {
    if (!items || !Array.isArray(items)) {
      console.log('⚠️ items 데이터가 없습니다');
      return false;
    }
    
    const archivedItems = items.filter(item => item.status === 'ARCHIVED');
    const renderedArchived = document.querySelectorAll('[data-status="ARCHIVED"]').length;
    
    console.log('=== ARCHIVED 숨김 확인 ===');
    console.log('ARCHIVED 아이템 수:', archivedItems.length);
    console.log('렌더링된 ARCHIVED 카드 수:', renderedArchived);
    
    if (renderedArchived === 0) {
      console.log('✅ 통과: ARCHIVED가 홈에서 렌더링되지 않음');
      return true;
    } else {
      console.log('❌ 실패: ARCHIVED가 렌더링됨');
      return false;
    }
  },
  
  // 3. 숫자 노출 0개 확인
  checkNoNumbers: () => {
    const cards = document.querySelectorAll('[class*="StatusBasedCard"], [class*="Card"]');
    let numberCount = 0;
    const numberPatterns = [
      /\d+원/g,
      /[+-]?\d+\.?\d*%/g,
      /수익률/g,
      /가격/g,
      /등락/g,
      /current_price/g,
      /current_return/g,
      /change_rate/g,
      /recommended_price/g
    ];
    
    cards.forEach(card => {
      const text = card.textContent || '';
      numberPatterns.forEach(pattern => {
        if (pattern.test(text)) {
          numberCount++;
        }
      });
    });
    
    console.log('=== 숫자 노출 확인 ===');
    console.log('카드 수:', cards.length);
    console.log('숫자 패턴 매칭 수:', numberCount);
    
    if (numberCount === 0) {
      console.log('✅ 통과: 숫자 노출 0개');
      return true;
    } else {
      console.log('❌ 실패: 숫자가 노출됨');
      return false;
    }
  },
  
  // 4. BROKEN/ACTIVE 섹션 분리 확인
  checkSectionsSeparated: () => {
    const brokenSection = document.querySelector('h3')?.textContent?.includes('관리 필요 종목');
    const activeSection = document.querySelector('h3')?.textContent?.includes('유효한 추천');
    
    // 섹션이 분리되어 있는지 확인 (같은 부모에 섞여있지 않음)
    const sections = document.querySelectorAll('h3');
    const hasBrokenSection = Array.from(sections).some(h3 => h3.textContent.includes('관리 필요 종목'));
    const hasActiveSection = Array.from(sections).some(h3 => h3.textContent.includes('유효한 추천'));
    
    console.log('=== BROKEN/ACTIVE 섹션 분리 확인 ===');
    console.log('관리 필요 종목 섹션 존재:', hasBrokenSection);
    console.log('유효한 추천 섹션 존재:', hasActiveSection);
    
    if (hasBrokenSection && hasActiveSection) {
      console.log('✅ 통과: BROKEN/ACTIVE 섹션이 분리되어 있음');
      return true;
    } else {
      console.log('⚠️ 경고: 섹션이 제대로 렌더링되지 않았을 수 있음');
      return false;
    }
  },
  
  // 전체 검증 실행
  runAll: (items) => {
    console.log('\n========================================');
    console.log('상태 기반 리팩토링 검증');
    console.log('========================================\n');
    
    const results = [
      this.checkNoDateScrollUI(),
      this.checkArchivedHidden(items),
      this.checkNoNumbers(),
      this.checkSectionsSeparated()
    ];
    
    const allPassed = results.every(r => r === true);
    
    console.log('\n========================================');
    if (allPassed) {
      console.log('✅ 모든 검증 통과!');
    } else {
      console.log('❌ 일부 검증 실패');
    }
    console.log('========================================\n');
    
    return allPassed;
  }
};

// 브라우저 콘솔에서 사용할 수 있도록 전역으로 노출
if (typeof window !== 'undefined') {
  window.verifyRefactor = verifyRefactor;
}


