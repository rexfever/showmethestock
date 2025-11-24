# 팝업 공지 수정 완료

## 문제 원인

1. **날짜 형식 불일치**
   - DB 스키마: `start_date`, `end_date`가 `TIMESTAMP WITH TIME ZONE` 타입
   - 코드 기대값: `YYYYMMDD` 형식의 문자열
   - 실제 DB 값: `2025-11-24 00:00:00+09` (TIMESTAMP 객체)

2. **날짜 파싱 실패**
   - `datetime.strptime(start_date, "%Y%m%d")` 호출 시 ValueError 발생
   - 날짜 범위 확인 실패로 `is_enabled = False`로 설정됨

3. **날짜 비교 오류**
   - timezone-aware와 timezone-naive datetime 비교 시 TypeError 발생

## 수정 내용

### 1. `backend/date_helper.py`
- `normalize_date()` 함수 개선
- TIMESTAMP 형식 (`2025-11-24 00:00:00+09`) 지원 추가
- 날짜 부분만 추출하여 `YYYYMMDD` 형식으로 변환

### 2. `backend/main.py` - `get_popup_notice_status()`
- TIMESTAMP 객체를 문자열로 변환하는 로직 추가
- `datetime.strptime()` 전에 날짜 형식 정규화
- timezone-naive datetime으로 날짜 비교 수행

## 수정 전/후 비교

### 수정 전
```json
{
  "is_enabled": false,
  "title": "",
  "message": "",
  "start_date": "",
  "end_date": ""
}
```

### 수정 후
```json
{
  "is_enabled": true,
  "title": "추천 종목 매매 안내",
  "message": "최근 과거 데이터 기반 백테스트...",
  "start_date": "20251124",
  "end_date": "20251130"
}
```

## 테스트 결과

- ✅ API 엔드포인트 `/popup-notice/status` 정상 동작
- ✅ 날짜 범위 확인 로직 정상 작동
- ✅ 프론트엔드에서 팝업 공지 표시 가능

## 배포 상태

- ✅ 로컬 코드 수정 완료
- ✅ 서버에 파일 복사 완료
- ✅ 서버 백엔드 재시작 완료
- ✅ API 테스트 통과

