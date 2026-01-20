# 인증 관련 코드 리뷰 결과

**작성일**: 2026-01-08  
**리뷰 범위**: JWT 토큰 인증 및 is_active 확인 로직

---

## 발견된 문제점

### 1. ✅ 수정 완료: get_optional_user의 bare except

**문제**:
- `get_optional_user`에서 `except:` (bare except) 사용
- 모든 예외를 숨겨서 디버깅 어려움

**수정**:
```python
# 수정 전
except:
    pass

# 수정 후
except HTTPException:
    return None
except Exception as e:
    logging.getLogger(__name__).warning(f"get_optional_user에서 예외 발생: {e}")
    return None
```

**위험도**: 🟡 중간

---

### 2. ⚠️ 개선 권장: verify_token에서 is_active 미확인

**문제**:
- `verify_token`에서 이메일로 사용자 조회 시 `is_active`를 확인하지 않음
- 비활성 사용자의 토큰도 유효한 것으로 반환될 수 있음

**현재 동작**:
```python
def verify_token(self, token: str) -> Optional[TokenData]:
    # 이메일로 사용자 조회
    user = self.get_user_by_email(sub_value)
    if user:
        token_data = TokenData(user_id=user.id)  # is_active 확인 안 함
```

**완화 요인**:
- `get_current_user`와 `get_optional_user`에서 `is_active` 확인
- 실제 API 접근은 차단됨

**개선 방안** (선택적):
```python
def verify_token(self, token: str) -> Optional[TokenData]:
    # ...
    user = self.get_user_by_email(sub_value)
    if user and user.is_active:  # is_active 확인 추가
        token_data = TokenData(user_id=user.id)
    else:
        return None
```

**위험도**: 🟢 낮음 (현재 구조에서 완화됨)

---

### 3. ✅ 확인 완료: get_current_user의 is_active 확인

**상태**: 정상 작동
- 비활성 사용자에 대해 403 Forbidden 반환
- 적절한 에러 메시지 제공

---

### 4. ✅ 확인 완료: get_optional_user의 is_active 확인

**상태**: 정상 작동
- 비활성 사용자에 대해 None 반환
- 선택적 인증에서도 보안 유지

---

### 5. ⚠️ 주의: AccessLogMiddleware에서 is_active 미확인

**문제**:
- `AccessLogMiddleware`에서 사용자 조회 시 `is_active` 확인 안 함
- 비활성 사용자도 로그에 기록됨

**현재 코드**:
```python
token_data = auth_service.verify_token(token)
if token_data:
    user = auth_service.get_user_by_id(token_data.user_id)
    if user:  # is_active 확인 안 함
        user_id = user.id
```

**영향**:
- 로깅 목적이므로 보안 문제는 아님
- 하지만 일관성을 위해 확인하는 것이 좋음

**개선 방안** (선택적):
```python
if user and user.is_active:
    user_id = user.id
```

**위험도**: 🟢 낮음 (로깅 목적)

---

## 테스트 결과

### 작성된 테스트
- `test_auth_is_active_check.py`: is_active 확인 로직 테스트

### 테스트 항목
1. ✅ 활성 사용자로 get_current_user 테스트
2. ✅ 비활성 사용자로 get_current_user 테스트 (403 에러)
3. ✅ 활성 사용자로 get_optional_user 테스트
4. ✅ 비활성 사용자로 get_optional_user 테스트 (None 반환)
5. ✅ 존재하지 않는 사용자 테스트
6. ✅ verify_token의 is_active 미확인 문제 확인

---

## 권장 사항

### 즉시 적용 (완료)
1. ✅ `get_optional_user`의 bare except 수정
2. ✅ 예외 처리 로깅 추가

### 중기 개선 (선택적)
1. `verify_token`에서 is_active 확인 추가
   - 이점: 토큰 검증 단계에서 차단
   - 단점: 모든 토큰 검증 시 DB 조회 필요 (성능 영향)
   - 권장: 현재 구조 유지 (get_current_user에서 확인)

2. `AccessLogMiddleware`에서 is_active 확인
   - 이점: 일관성 향상
   - 단점: 미미함 (로깅 목적)
   - 권장: 선택적 개선

---

## 보안 평가

### 현재 상태
- ✅ **보안 수준**: 양호
- ✅ **주요 보호**: get_current_user와 get_optional_user에서 is_active 확인
- ⚠️ **개선 여지**: verify_token 단계에서 확인 (선택적)

### 보안 강점
1. API 접근 시 is_active 확인 (get_current_user)
2. 선택적 인증에서도 is_active 확인 (get_optional_user)
3. 적절한 HTTP 상태 코드 사용 (403 Forbidden)

### 잠재적 위험
1. verify_token 단계에서 미확인 (하지만 완화됨)
2. AccessLogMiddleware에서 미확인 (로깅 목적)

---

## 결론

**현재 구현은 보안상 안전합니다.** 

주요 보호 메커니즘(`get_current_user`, `get_optional_user`)에서 `is_active`를 확인하므로, 비활성 사용자의 API 접근은 차단됩니다.

개선 사항은 선택적이며, 성능과 보안의 균형을 고려하여 결정할 수 있습니다.

---

**최종 업데이트**: 2026-01-08

