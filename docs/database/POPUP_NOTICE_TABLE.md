# popup_notice 테이블 문서

## 개요

`popup_notice` 테이블은 관리자가 설정한 팝업 공지를 저장하는 테이블입니다. 사용자에게 중요한 공지사항을 팝업으로 표시할 수 있습니다.

## 테이블 스키마

```sql
CREATE TABLE IF NOT EXISTS popup_notice (
    id          BIGSERIAL PRIMARY KEY,
    is_enabled  BOOLEAN NOT NULL DEFAULT FALSE,
    title       TEXT NOT NULL,
    message     TEXT NOT NULL,
    start_date  TIMESTAMP WITH TIME ZONE NOT NULL,
    end_date    TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

## 컬럼 설명

| 컬럼 | 타입 | 제약조건 | 설명 |
|------|------|----------|------|
| `id` | BIGSERIAL | PRIMARY KEY | 자동 증가 ID |
| `is_enabled` | BOOLEAN | NOT NULL, DEFAULT FALSE | 팝업 공지 활성화 여부 |
| `title` | TEXT | NOT NULL | 팝업 제목 |
| `message` | TEXT | NOT NULL | 팝업 내용 |
| `start_date` | TIMESTAMP WITH TIME ZONE | NOT NULL | 표시 시작 날짜/시간 |
| `end_date` | TIMESTAMP WITH TIME ZONE | NOT NULL | 표시 종료 날짜/시간 |
| `created_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW() | 생성 시간 |
| `updated_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW() | 최종 수정 시간 |

## 관리 방법

### 1. 자동 생성

테이블은 `main.py`의 `create_popup_notice_table()` 함수가 자동으로 생성합니다.

- 첫 번째 조회/저장 시 자동 생성
- `CREATE TABLE IF NOT EXISTS` 사용으로 안전

### 2. API를 통한 관리

**조회 (관리자 전용):**
```bash
GET /admin/popup-notice
Authorization: Bearer <admin_token>
```

**업데이트 (관리자 전용):**
```bash
POST /admin/popup-notice
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "is_enabled": true,
  "title": "공지 제목",
  "message": "공지 내용",
  "start_date": "20251124",
  "end_date": "20251130"
}
```

**공개 조회 (사용자용):**
```bash
GET /popup-notice/status
```

이 API는 다음을 반환합니다:
- `is_enabled`: 활성화 여부
- `title`: 제목
- `message`: 내용
- `start_date`: 시작일 (YYYYMMDD 형식)
- `end_date`: 종료일 (YYYYMMDD 형식)

날짜 범위 확인:
- 현재 날짜가 `start_date`와 `end_date` 사이에 있어야 표시
- 범위를 벗어나면 `is_enabled`가 `false`로 반환됨

### 3. 직접 SQL 실행

```sql
-- 공지 조회
SELECT * FROM popup_notice ORDER BY id DESC LIMIT 1;

-- 공지 업데이트
UPDATE popup_notice 
SET is_enabled = true,
    title = '새 공지',
    message = '공지 내용',
    start_date = '2025-11-24 00:00:00+09',
    end_date = '2025-11-30 23:59:59+09',
    updated_at = NOW()
WHERE id = 1;

-- 공지 삭제 (기존 공지 삭제 후 새로 추가하는 방식)
DELETE FROM popup_notice;
INSERT INTO popup_notice (is_enabled, title, message, start_date, end_date)
VALUES (true, '새 공지', '공지 내용', '2025-11-24 00:00:00+09', '2025-11-30 23:59:59+09');
```

## 날짜 형식 처리

### 저장 형식
- DB에는 `TIMESTAMP WITH TIME ZONE` 형식으로 저장
- 예: `2025-11-24 00:00:00+09`

### API 입력 형식
- 관리자 API: `YYYYMMDD` 형식 (예: `20251124`)
- 자동으로 `TIMESTAMP WITH TIME ZONE`으로 변환

### API 출력 형식
- 공개 API (`/popup-notice/status`): `YYYYMMDD` 형식으로 반환
- 관리자 API (`/admin/popup-notice`): ISO 형식으로 반환

## 날짜 범위 확인 로직

```python
# 현재 날짜가 범위 내에 있는지 확인
if is_enabled and start_date and end_date:
    now = get_kst_now()
    now_date = datetime(now.year, now.month, now.day)
    
    if now_date < start_dt or now_date > end_dt:
        is_enabled = False  # 범위를 벗어나면 비활성화
```

## 프론트엔드 연동

프론트엔드의 `PopupNotice` 컴포넌트가 `/popup-notice/status` API를 호출하여 팝업을 표시합니다.

**표시 조건:**
1. `is_enabled = true`
2. `title`과 `message`가 존재
3. 현재 날짜가 `start_date`와 `end_date` 사이
4. 사용자가 "다시 보지 않기"를 선택하지 않음 (localStorage)

## 주의사항

1. **단일 공지**: 한 번에 하나의 공지만 활성화 가능 (최신 공지만 유지)
2. **날짜 형식**: 입력은 `YYYYMMDD`, 저장은 `TIMESTAMP WITH TIME ZONE`
3. **자동 비활성화**: 날짜 범위를 벗어나면 자동으로 `is_enabled = false`로 처리
4. **타임존**: KST (Asia/Seoul) 기준으로 처리

## 관련 파일

- `backend/main.py`: 테이블 생성 및 API 엔드포인트
- `backend/models.py`: `PopupNoticeRequest` 모델
- `frontend/components/PopupNotice.js`: 프론트엔드 컴포넌트
- `frontend/pages/admin.js`: 관리자 UI

