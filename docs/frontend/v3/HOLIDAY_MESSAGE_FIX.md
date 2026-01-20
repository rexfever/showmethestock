# 휴장일 메시지 Override 버그 수정 보고서

## 문제 원인

**기존 문제**: 휴장일(주말/공휴일)에 추천 시점 메시지가 override되어 사라지는 UX 버그
- 금요일(2025-12-26)에 추천된 종목 카드가 있음
- 사용자가 주말(일요일)에 12/26 섹션으로 들어가 "추천 당시 메시지"를 확인하고 싶음
- 휴장일 컨텍스트를 이유로 카드 본문 문구를 override하면, 추천 시점 메시지를 확인할 수 없게 됨

## 수정 내용

### 1. 수정 대상 컴포넌트

#### `frontend/components/v3/StockCardV3.js`
- **추가**: `isMarketClosed()` 함수 - 휴장일(토/일) 판단
- **추가**: `MarketContextNotice` 컴포넌트 - 휴장일 안내 배너
- **변경**: 추천 메시지 렌더링 부분에 휴장일 배너 추가 (메시지는 절대 변경하지 않음)

#### `frontend/components/v3/V3DateSection.js`
- **추가**: `isMarketClosed()` 함수 - 휴장일(토/일) 판단
- **추가**: `MarketContextNotice` 컴포넌트 - 휴장일 안내 배너
- **변경**: 추천 종목 리스트 상단에 휴장일 배너 추가

### 2. 구현 코드

#### 휴장일 판단 로직 (`isMarketClosed`)

```javascript
/**
 * 휴장일 판단 함수
 * @returns {boolean} 현재가 휴장일(토/일)이면 true
 */
function isMarketClosed() {
  const today = new Date();
  const dayOfWeek = today.getDay(); // 0 = 일요일, 6 = 토요일
  return dayOfWeek === 0 || dayOfWeek === 6;
}
```

#### 시장 컨텍스트 안내 배너 (`MarketContextNotice`)

```javascript
/**
 * 시장 컨텍스트 안내 배너 컴포넌트
 * 휴장일 안내를 별도 배너로 표시 (추천 메시지는 건드리지 않음)
 */
function MarketContextNotice() {
  if (!isMarketClosed()) {
    return null; // 평일에는 표시하지 않음
  }

  return (
    <div className="bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 mb-3">
      <div className="flex items-center space-x-2">
        <span className="text-gray-500 text-sm">⏸️</span>
        <span className="text-sm text-gray-600 font-medium">
          현재 휴장 중 · 다음 거래일에 확인하세요
        </span>
      </div>
    </div>
  );
}
```

#### StockCardV3 렌더링 구조 (2개 레이어 분리)

```javascript
return (
  <>
    <div className={`bg-white rounded-lg shadow-sm border-2 ${messages.colorClass} p-5 space-y-4`}>
      {/* A) MarketContextNotice (현재 컨텍스트 안내) - 휴장일일 때만 표시 */}
      <MarketContextNotice />
      
      {/* B) RecommendationCopy (추천 시점 고정 본문 카피) - 절대 변경하지 않음 */}
      {/* 종목 헤더 */}
      <div className="flex items-start justify-between">
        {/* ... */}
      </div>
      
      {/* 상태 헤더 (추천 시점 메시지) */}
      <div className={`pt-3 border-t ${messages.colorClass.replace('bg-', 'border-').replace('-50', '-200')}`}>
        <div className={`text-base font-bold ${messages.statusColorClass} mb-2`}>
          {messages.status} {/* 추천 시점 title - 절대 변경하지 않음 */}
        </div>
      </div>
      
      {/* 행동 가이드 (추천 시점 action) */}
      <div className={`text-sm ${messages.actionColorClass} font-medium`}>
        {messages.action} {/* 추천 시점 action - 절대 변경하지 않음 */}
      </div>
      
      {/* 보조 설명 (추천 시점 desc) */}
      {messages.description && (
        <div className="text-xs text-gray-600">
          {messages.description} {/* 추천 시점 desc - 절대 변경하지 않음 */}
        </div>
      )}
      
      {/* ... */}
    </div>
  </>
);
```

### 3. 레이어 분리 구조

#### A) RecommendationCopy (추천 시점 고정 본문 카피)
- **위치**: `STATUS_MESSAGES[status]` 기반 렌더링
- **내용**: `title`, `action`, `description` (추천 시점 기준)
- **특징**: 절대 변경하지 않음, 휴장일에도 그대로 유지

#### B) MarketContextNotice (현재 컨텍스트 안내)
- **위치**: 카드 상단 (종목 헤더 위)
- **내용**: "현재 휴장 중 · 다음 거래일에 확인하세요"
- **특징**: 휴장일(토/일)에만 표시, 평일에는 숨김

## 검증 시나리오

### 1. 12/26 추천된 섹션을 12/28(일) 열었을 때
- ✅ 카드 본문: 12/26 기준 추천 메시지가 그대로 보임
- ✅ 추가로: "현재 휴장 중" 안내 배너가 표시됨

### 2. 장중(평일)에는 휴장 배너가 보이지 않음
- ✅ 평일(월~금): `isMarketClosed()`가 `false` 반환
- ✅ `MarketContextNotice`가 `null` 반환하여 배너 미표시

### 3. 추천 시점 메시지가 어떤 상태였든 휴장일에도 그대로 유지
- ✅ `STATUS_MESSAGES[status]` 기반 메시지는 절대 변경하지 않음
- ✅ 휴장일 배너는 별도 레이어로 추가만 함

## 왜 이 수정으로 추천 시점 메시지 확인이 항상 가능한가?

**추천 시점 메시지(`STATUS_MESSAGES[status]`)는 휴장일 여부와 무관하게 항상 그대로 렌더링되며, 휴장일 안내는 별도의 `MarketContextNotice` 배너로만 추가되므로, 사용자가 과거 날짜 섹션을 열람할 때도 추천 시점의 원본 메시지(title/action/desc)를 항상 확인할 수 있습니다.**

