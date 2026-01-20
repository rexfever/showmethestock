# 등락률 표시 문제 수정 완료

## 문제 원인

프론트엔드에서 `item.current_price`와 `item.change_rate`를 사용하지만, `ScanItem` 모델에 해당 필드가 정의되어 있지 않아 null로 반환되었습니다.

### 증상
- API 응답에서 `current_price: null`, `change_rate: null`
- `indicators.change_rate`는 정상적으로 있음 (1.59)
- 프론트엔드에서 등락률이 표시되지 않음

## 수정 내용

### 1. `backend/models.py`
- `ScanItem` 모델에 `current_price`와 `change_rate` 필드 추가
- Optional 필드로 정의하여 기존 코드와 호환성 유지

### 2. `backend/main.py`
- `ScanItem` 생성 시 `current_price`와 `change_rate` 값 설정
- `current_price`: `item["indicators"]["close"]` 사용
- `change_rate`: 키움 API에서 가져온 `change_rate` 사용

## 수정 전/후 비교

### 수정 전
```json
{
  "ticker": "140410",
  "name": "메지온",
  "current_price": null,
  "change_rate": null,
  "indicators": {
    "change_rate": 1.59
  }
}
```

### 수정 후
```json
{
  "ticker": "140410",
  "name": "메지온",
  "current_price": 70400,
  "change_rate": 1.59,
  "indicators": {
    "change_rate": 1.59
  }
}
```

## 테스트 결과

- ✅ API 엔드포인트 `/scan` 정상 동작
- ✅ `current_price` 정상 반환
- ✅ `change_rate` 정상 반환
- ✅ 프론트엔드에서 등락률 표시 가능

## 배포 상태

- ✅ 로컬 코드 수정 완료
- ✅ 서버에 파일 복사 완료
- ✅ 서버 백엔드 재시작 완료
- ✅ API 테스트 통과

