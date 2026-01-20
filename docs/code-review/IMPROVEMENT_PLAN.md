# 스캔 로직 개선 계획

## 🎯 목표

1. **Step 0~3까지만 사용**: 품질 저하 방지
2. **Step 7 제거**: 목표 미달 시 빈 리스트 반환
3. **품질 유지**: 평균 수익률 +1% 이상 유지

## 📋 구체적 개선 사항

### 1. Fallback 단계 제한 (Step 0~3까지만)

**현재**: Step 0~6까지 진행, Step 7로 강제 사용
**개선**: Step 0~3까지만 진행, Step 3에서도 목표 미달 시 빈 리스트 반환

### 2. Step 7 제거

**현재**: 모든 단계에서 목표 미달 시 Step 7로 강제 사용
**개선**: 목표 미달 시 빈 리스트 반환

### 3. 코드 수정 위치

- `backend/services/scan_service.py`: `execute_scan_with_fallback` 함수
- Step 3 이후 진행하지 않도록 수정
- Step 7 로직 제거

## 🔧 구현 방법

### 변경 사항

1. **Step 3까지만 순회**
   ```python
   # 현재: config.fallback_presets[2:] 전체 순회
   # 개선: config.fallback_presets[2:4]까지만 순회 (Step 3까지만)
   for step_idx, overrides in enumerate(config.fallback_presets[2:4], start=3):
   ```

2. **Step 7 로직 제거**
   ```python
   # 현재: 목표 미달 시 Step 7로 강제 사용
   # 개선: 목표 미달 시 빈 리스트 반환
   if not final_items:
       print(f"⚠️ 모든 단계에서 목표 미달 - 추천 종목 없음")
       final_items = []
       chosen_step = None
   ```

## 📊 예상 효과

### 개선 전
- Step 0~7까지 진행
- Step 7에서 품질 저하된 종목 추천
- 평균 수익률: 0.80%

### 개선 후
- Step 0~3까지만 진행
- 품질 저하 방지
- 예상 평균 수익률: +1.5% 이상

## ✅ 실행 계획

1. 코드 수정
2. 테스트
3. 배포

