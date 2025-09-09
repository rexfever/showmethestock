# 카카오 알림톡 템플릿: 스캔 결과 알림

## 📱 알림톡 템플릿 설계

### 기본 정보
- **템플릿명**: 스톡인사이트 일일 스캔 결과 알림
- **카테고리**: 금융/투자
- **승인 상태**: 승인 대기
- **발송 시간**: 매일 오후 6시 (장 마감 후)

## 🎯 알림톡 메시지 템플릿

### 템플릿 1: 기본 알림 (간단형)
```
📊 스톡인사이트 일일 스캔 결과

안녕하세요! 오늘의 주식 스캔 결과를 알려드립니다.

🎯 매칭 종목: {matched_count}개
📈 강한 매수 신호 종목들이 발견되었습니다!

상세 정보는 아래 링크에서 확인하세요:
🔗 https://sohntech.ai.kr/customer-scanner

스톡인사이트
```

### 템플릿 2: 상세 알림 (확장형)
```
📊 스톡인사이트 일일 스캔 결과

안녕하세요! 오늘의 주식 스캔 결과를 알려드립니다.

📅 스캔 일시: {scan_date}
🎯 매칭 종목: {matched_count}개
📈 강한 매수 신호 종목들이 발견되었습니다!

💡 주요 특징:
• 골든크로스 형성 종목
• 모멘텀 양전환 종목  
• 거래량 확대 종목

상세 정보는 아래 링크에서 확인하세요:
🔗 https://sohntech.ai.kr/customer-scanner

스톡인사이트
```

### 템플릿 3: 개인화 알림 (프리미엄)
```
📊 스톡인사이트 개인 맞춤 알림

{user_name}님, 오늘의 투자 기회를 확인하세요!

🎯 매칭 종목: {matched_count}개
📈 강한 매수 신호 종목들이 발견되었습니다!

💡 오늘의 하이라이트:
• 최고 점수: {top_score}점
• 추천 종목: {top_stock_name}

상세 분석은 아래 링크에서 확인하세요:
🔗 https://sohntech.ai.kr/customer-scanner

스톡인사이트
```

## 🔧 백엔드 구현 코드

### 1. 알림톡 메시지 포맷팅 함수 수정

```python
def format_scan_alert_message(matched_count: int, scan_date: str = None, user_name: str = None) -> str:
    """스캔 결과 알림톡 메시지 포맷팅"""
    if scan_date is None:
        scan_date = datetime.now().strftime("%Y년 %m월 %d일")
    
    # 기본 템플릿 사용
    message = f"""📊 스톡인사이트 일일 스캔 결과

안녕하세요! 오늘의 주식 스캔 결과를 알려드립니다.

🎯 매칭 종목: {matched_count}개
📈 강한 매수 신호 종목들이 발견되었습니다!

상세 정보는 아래 링크에서 확인하세요:
🔗 https://sohntech.ai.kr/customer-scanner

스톡인사이트"""
    
    return message
```

### 2. API 엔드포인트 수정

```python
@app.post('/send_scan_result')
def send_scan_result(to: str, top_n: int = 5):
    """현재 /scan 결과 요약을 카카오 알림톡으로 발송"""
    # 최신 스캔 실행
    resp = scan(save_snapshot=True)
    
    # 알림톡 메시지 생성 (링크 포함)
    message = format_scan_alert_message(resp.matched_count)
    
    # 카카오 알림톡 발송
    result = send_alert(to, message)
    
    # 로그 기록
    _log_send(to, resp.matched_count)
    
    return {
        "status": "ok" if result.get('ok') else "fail", 
        "matched_count": resp.matched_count, 
        "sent_to": to, 
        "message_preview": message[:100] + "...",
        "provider": result
    }
```

### 3. 자동 발송 스케줄러 추가

```python
@app.post('/schedule_daily_alert')
def schedule_daily_alert():
    """매일 오후 6시 자동 발송 스케줄 등록"""
    # 실제 구현에서는 cron job이나 스케줄러 사용
    # 여기서는 수동 실행용 엔드포인트
    pass

@app.post('/send_daily_alert')
def send_daily_alert():
    """일일 알림 발송 (스케줄러에서 호출)"""
    # 구독자 목록 조회 (실제로는 DB에서)
    subscribers = get_subscribers()  # 구현 필요
    
    results = []
    for subscriber in subscribers:
        resp = scan(save_snapshot=True)
        message = format_scan_alert_message(resp.matched_count)
        result = send_alert(subscriber.phone, message)
        results.append({
            "phone": subscriber.phone,
            "status": "ok" if result.get('ok') else "fail"
        })
    
    return {"status": "completed", "results": results}
```

## 📋 카카오 비즈니스 채널 설정

### 1. 채널 정보
- **채널명**: 스톡인사이트
- **채널 ID**: @스톡인사이트
- **채널 설명**: AI 기반 주식 스캐너 서비스
- **프로필 이미지**: 로고 이미지
- **채널 URL**: https://sohntech.ai.kr

### 2. 템플릿 승인 요청서
```
템플릿명: 스톡인사이트 일일 스캔 결과 알림
카테고리: 금융/투자
용도: 일일 주식 스캔 결과 알림
발송 빈도: 1일 1회
예상 발송량: 월 1,000건 이하

템플릿 내용:
- 스캔 결과 요약 (매칭 종목 수)
- 고객용 스캔 화면 링크
- 서비스 브랜딩

변수:
- {matched_count}: 매칭된 종목 수
- {scan_date}: 스캔 실행 일시 (선택사항)
```

## 🎨 UI/UX 고려사항

### 1. 링크 클릭 후 화면
- **고객용 스캐너 페이지**: https://sohntech.ai.kr/customer-scanner
- **표시 내용**: 
  - 오늘의 스캔 결과
  - 종목별 상세 정보
  - 별점 및 점수
  - 필터링 옵션

### 2. 모바일 최적화
- 반응형 디자인
- 터치 친화적 인터페이스
- 빠른 로딩 속도

### 3. 사용자 경험
- 명확한 정보 전달
- 직관적인 네비게이션
- 브랜드 일관성

## 📊 성과 측정 지표

### 1. 알림톡 지표
- **발송 성공률**: 95% 이상
- **링크 클릭률**: 20% 이상
- **사용자 유지율**: 70% 이상

### 2. 웹사이트 지표
- **페이지 방문률**: 알림톡 클릭 후
- **체류 시간**: 평균 2분 이상
- **재방문률**: 30% 이상

## 🔒 보안 및 개인정보 보호

### 1. 개인정보 처리
- **수집 정보**: 휴대폰 번호 (알림 발송용)
- **보관 기간**: 서비스 이용 기간
- **처리 목적**: 스캔 결과 알림 발송

### 2. 보안 조치
- 개인정보 암호화
- 접근 권한 관리
- 로그 기록 및 모니터링

## 📝 구현 체크리스트

### 백엔드 개발
- [ ] 알림톡 메시지 포맷팅 함수 구현
- [ ] API 엔드포인트 수정
- [ ] 자동 발송 스케줄러 구현
- [ ] 구독자 관리 시스템 구현
- [ ] 발송 로그 시스템 구현

### 프론트엔드 개발
- [ ] 고객용 스캐너 페이지 최적화
- [ ] 모바일 반응형 디자인
- [ ] 링크 추적 시스템 구현

### 카카오 비즈니스 채널
- [ ] 채널 생성 및 설정
- [ ] 템플릿 승인 요청
- [ ] API 연동 테스트
- [ ] 발송 테스트

### 운영 및 모니터링
- [ ] 발송 성공률 모니터링
- [ ] 사용자 피드백 수집
- [ ] 성과 분석 및 개선

---

**작성일**: 2025년 9월 9일  
**작성자**: 개발팀  
**버전**: 1.0
