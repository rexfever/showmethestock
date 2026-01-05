# 휴장일 UX 개선 보고서 - 날짜 섹션 단위 표시

## 문제 원인

**기존 문제**: 휴장일에 모든 종목 카드마다 "현재 휴장 중" 배너가 반복 노출
- 추천 섹션 날짜(예: 12/26)와 현재 휴장 상태(12/28)가 섞여 시간축이 꼬여 보임
- 휴장일임에도 카드에 "당일 등락"이 표시되어 UX적으로 모순됨

## 수정 내용

### 수정 대상 컴포넌트

1. **`frontend/components/v3/V3DateSection.js`**
   - 날짜 헤더에 휴장 표시 추가 (오늘 날짜이고 휴장일일 때만)
   - 날짜 헤더 아래 휴장 안내 문구 추가
   - 카드 리스트에서 휴장 배너 제거

2. **`frontend/components/v3/StockCardV3.js`**
   - `MarketContextNotice` 컴포넌트 완전 제거
   - 휴장일에는 "당일 등락" 라벨 숨김

### 구현 코드

#### 1. 날짜 헤더 렌더링 수정 (`V3DateSection.js`)

```javascript
// 날짜 포맷팅 (휴장 표시 포함)
const formatDate = (dateStr, showHoliday = false) => {
  if (!dateStr || dateStr.length !== 8) return dateStr;
  try {
    const year = dateStr.slice(0, 4);
    const month = dateStr.slice(4, 6);
    const day = dateStr.slice(6, 8);
    const dateObj = new Date(`${year}-${month}-${day}`);
    const weekdays = ['일', '월', '화', '수', '목', '금', '토'];
    const weekday = weekdays[dateObj.getDay()];
    const baseDate = `${year}년 ${parseInt(month)}월 ${parseInt(day)}일 (${weekday})`;
    return showHoliday ? `${baseDate} · 휴장` : baseDate;
  } catch (e) {
    return dateStr;
  }
};

// 오늘 날짜인지 확인
const isTodayDate = isToday(date);
// 오늘이 휴장일인지 확인
const isClosedToday = isMarketClosedToday() && isTodayDate;

const formattedDate = formatDate(date, isClosedToday);
```

#### 2. 날짜 헤더 아래 안내 문구 추가

```javascript
{/* 날짜 헤더 */}
<div className="bg-white border-b border-gray-200 px-4 py-3 sticky top-0 z-10">
  <div className="flex items-center justify-between">
    <div className="flex items-center space-x-2">
      <span className="text-xl">📅</span>
      <h2 className="text-lg font-bold text-gray-900">{formattedDate}</h2>
    </div>
    <div className="text-sm text-gray-600">
      추천 종목: <span className="font-semibold text-blue-600">{actualStocks.length}개</span>
    </div>
  </div>
</div>

{/* 휴장일 안내 (오늘 날짜이고 휴장일일 때만 표시) */}
{isClosedToday && (
  <div className="bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 mb-3 mx-4 mt-2">
    <div className="text-sm text-gray-600">
      장이 열리지 않는 날입니다. 다음 거래일에 다시 확인하세요.
    </div>
  </div>
)}
```

#### 3. 카드에서 제거된 휴장 배너 코드

**제거 전** (`StockCardV3.js`):
```javascript
{/* 시장 컨텍스트 안내 배너 (휴장일일 때만 표시) */}
<MarketContextNotice />
```

**제거 후**: 완전히 제거됨

#### 4. 휴장일에는 "당일 등락" 라벨 숨김

```javascript
{(() => {
  // 휴장일에는 "당일 등락" 표시하지 않음
  if (isClosedToday) {
    return null;
  }
  
  // change_rate 처리: 당일 등락률 표시
  // ... 기존 로직
})()}
```

### 3. 휴장일 판단 로직

```javascript
/**
 * 휴장일 판단 함수
 * @returns {boolean} 현재가 휴장일(토/일)이면 true
 */
function isMarketClosedToday() {
  const today = new Date();
  const dayOfWeek = today.getDay(); // 0 = 일요일, 6 = 토요일
  return dayOfWeek === 0 || dayOfWeek === 6;
}

/**
 * 날짜 문자열(YYYYMMDD)이 오늘 날짜인지 확인
 * @param {string} dateStr - YYYYMMDD 형식 날짜 문자열
 * @returns {boolean} 오늘 날짜이면 true
 */
function isToday(dateStr) {
  if (!dateStr || dateStr.length !== 8) return false;
  try {
    const today = new Date();
    const todayStr = `${today.getFullYear()}${String(today.getMonth() + 1).padStart(2, '0')}${String(today.getDate()).padStart(2, '0')}`;
    return dateStr === todayStr;
  } catch (e) {
    return false;
  }
}
```

## 검증 시나리오

### 1. 일요일에 화면 진입
- ✅ 상단 날짜: `2025년 12월 28일 (일) · 휴장`
- ✅ 안내 문구 1회 노출: "장이 열리지 않는 날입니다. 다음 거래일에 다시 확인하세요."
- ✅ 카드에는 휴장 문구 없음
- ✅ 카드에 "당일 등락" 라벨 없음

### 2. 12/26 추천 섹션 진입
- ✅ 12/26 기준 추천 메시지 그대로 노출
- ✅ 휴장 안내 섞이지 않음 (과거 날짜이므로)
- ✅ 날짜 헤더: `2025년 12월 26일 (금)` (휴장 표시 없음)

### 3. 평일 장중
- ✅ '휴장' 라벨 미노출
- ✅ 안내 문구 미노출
- ✅ "당일 등락" 라벨 정상 표시

## 왜 이 구조가 사용자 혼란을 제거하는가?

**휴장 상태는 날짜 섹션 헤더에 단 한 번만 표시되고, 각 종목 카드에서는 완전히 제거되며, 과거 날짜 섹션에는 현재 휴장 여부를 표시하지 않으므로, 사용자가 추천 시점(과거 날짜)의 메시지를 확인할 때 현재 휴장 상태와 혼동되지 않고, 시간축이 명확하게 분리되어 혼란이 제거됩니다.**

