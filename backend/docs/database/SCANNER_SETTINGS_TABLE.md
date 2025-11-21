# scanner_settings 테이블 문서

## 개요

`scanner_settings` 테이블은 스캐너 버전 및 V2 활성화 여부를 DB에서 관리하기 위한 테이블입니다.

## 테이블 스키마

```sql
CREATE TABLE IF NOT EXISTS scanner_settings(
    id SERIAL PRIMARY KEY,
    setting_key TEXT NOT NULL UNIQUE,
    setting_value TEXT NOT NULL,
    description TEXT,
    updated_by TEXT,
    updated_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);
```

## 컬럼 설명

| 컬럼 | 타입 | 제약조건 | 설명 |
|------|------|----------|------|
| `id` | SERIAL | PRIMARY KEY | 자동 증가 ID |
| `setting_key` | TEXT | NOT NULL, UNIQUE | 설정 키 (예: scanner_version, scanner_v2_enabled) |
| `setting_value` | TEXT | NOT NULL | 설정 값 (예: v1, v2, true, false) |
| `description` | TEXT | NULL | 설정 설명 |
| `updated_by` | TEXT | NULL | 최종 수정자 이메일 |
| `updated_at` | TIMESTAMP | DEFAULT NOW() | 최종 수정 시간 |
| `created_at` | TIMESTAMP | DEFAULT NOW() | 생성 시간 |

## 인덱스

```sql
CREATE INDEX IF NOT EXISTS idx_scanner_settings_key ON scanner_settings(setting_key);
```

## 기본값

테이블 생성 시 자동으로 다음 기본값이 설정됩니다:

```sql
INSERT INTO scanner_settings (setting_key, setting_value, description)
VALUES 
    ('scanner_version', 'v1', '스캐너 버전 (v1 또는 v2)'),
    ('scanner_v2_enabled', 'false', '스캐너 V2 활성화 여부 (true 또는 false)')
ON CONFLICT (setting_key) DO NOTHING;
```

## 관리 방법

### 1. 자동 생성

테이블은 `scanner_settings_manager.py`의 `create_scanner_settings_table()` 함수가 자동으로 생성합니다.

- 첫 번째 조회/저장 시 자동 생성
- `CREATE TABLE IF NOT EXISTS` 사용으로 안전
- 기본값 자동 설정

### 2. API를 통한 관리

**조회:**
```bash
GET /admin/scanner-settings
```

**업데이트:**
```bash
POST /admin/scanner-settings
Content-Type: application/json

{
  "scanner_version": "v2",
  "scanner_v2_enabled": true
}
```

### 3. 직접 SQL 실행

```sql
-- 설정 조회
SELECT * FROM scanner_settings;

-- 설정 업데이트
UPDATE scanner_settings 
SET setting_value = 'v2', updated_at = NOW() 
WHERE setting_key = 'scanner_version';

-- 새 설정 추가
INSERT INTO scanner_settings (setting_key, setting_value, description)
VALUES ('custom_setting', 'value', '설명')
ON CONFLICT (setting_key) DO UPDATE SET 
    setting_value = EXCLUDED.setting_value,
    updated_at = NOW();
```

## 설정 키 목록

### scanner_version
- **설명**: 현재 활성화된 스캐너 버전
- **가능한 값**: `v1`, `v2`
- **기본값**: `v1`

### scanner_v2_enabled
- **설명**: 스캐너 V2 활성화 여부
- **가능한 값**: `true`, `false`
- **기본값**: `false`

## 사용 패턴

### 설정 읽기 우선순위

1. **DB 우선**: `scanner_settings` 테이블에서 조회
2. **.env Fallback**: DB에 없으면 환경 변수에서 읽기
3. **기본값**: 둘 다 없으면 기본값 사용

```python
# config.py
@property
def scanner_version(self) -> str:
    try:
        from scanner_settings_manager import get_scanner_version
        return get_scanner_version()  # DB 우선
    except Exception:
        return os.getenv("SCANNER_VERSION", "v1")  # .env fallback
```

## 변경 이력 관리

- `updated_at`: 자동으로 현재 시간으로 업데이트
- `updated_by`: API를 통한 변경 시 관리자 이메일 저장
- 변경 이력 조회:

```sql
SELECT 
    setting_key,
    setting_value,
    updated_by,
    updated_at
FROM scanner_settings
ORDER BY updated_at DESC;
```

## 마이그레이션

### 기존 서버에 적용

1. **SQL 파일 실행** (선택사항):
   ```bash
   psql -U postgres -d stock_finder -f backend/sql/add_scanner_settings.sql
   ```

2. **자동 생성** (권장):
   - 코드 배포 후 첫 번째 API 호출 시 자동 생성
   - 별도 마이그레이션 스크립트 불필요

### 롤백

테이블 삭제 (필요한 경우만):
```sql
DROP TABLE IF EXISTS scanner_settings;
```

## 주의사항

1. **자동 생성**: 테이블은 자동으로 생성되므로 수동 생성 불필요
2. **기본값**: 첫 생성 시 기본값이 자동 설정됨
3. **UNIQUE 제약**: `setting_key`는 UNIQUE이므로 중복 불가
4. **타입**: 모든 값은 TEXT로 저장 (boolean도 'true'/'false' 문자열)

## 관련 파일

- `backend/scanner_settings_manager.py`: 테이블 생성 및 CRUD 함수
- `backend/config.py`: 설정 읽기 (DB 우선)
- `backend/main.py`: API 엔드포인트
- `backend/sql/add_scanner_settings.sql`: 마이그레이션 SQL (참고용)

