# Notifications App

이메일 알림 시스템을 관리하는 Django 앱입니다.

## 기능

- 템플릿 기반 이메일 전송
- Redis Queue(RQ)를 활용한 비동기 이메일 처리
- 이메일 로깅 및 관리
- python-dotenv를 통한 이메일 설정 관리
- REST API 인터페이스

## 설정

### 기본 이메일 설정

`.env` 파일에 이메일 설정 추가:

```
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.googlemail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@example.com
EMAIL_HOST_PASSWORD=your_email_password
DEFAULT_FROM_EMAIL=Your App <noreply@yourapp.com>
```

### Gmail 설정

Gmail을 사용하는 경우 다음과 같이 설정하세요:

```
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-gmail@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=Your App <your-gmail@gmail.com>
```

**주의사항:**
1. Gmail은 보안을 위해 **앱 비밀번호**를 사용해야 합니다. 계정 비밀번호가 아닙니다.
2. 앱 비밀번호 생성 방법:
   - [Google 계정 보안](https://myaccount.google.com/security) 페이지로 이동
   - 2단계 인증이 활성화되어 있는지 확인 (필수)
   - '앱 비밀번호' 섹션에서 새 앱 비밀번호 생성
   - 앱: '기타(직접 입력)' 선택 후 "Django" 또는 원하는 이름 입력
   - 생성된 16자리 비밀번호를 `EMAIL_HOST_PASSWORD`에 입력

3. Gmail 일일 발송 제한: 일반 Gmail 계정은 하루에 약 500통의 이메일로 제한됩니다. 대량 발송이 필요한 경우 Google Workspace 계정 사용을 권장합니다.

### Redis 설정

1. Redis 서버 실행:

```bash
redis-server
```

2. 이메일 작업 처리를 위한 RQ 워커 실행:

```bash
# 기본 큐와 이메일 큐 모두 처리
python manage.py rqworker default emails

# 더 자세한 로그 출력이 필요한 경우
python manage.py rqworker --verbose default emails
```

## 사용 방법

### 이메일 템플릿

이메일 템플릿은 `templates/notifications/email/` 디렉토리에 있습니다:

- `welcome.html`: 가입 환영 이메일
- `notification.html`: 일반 알림 이메일
- `password_reset.html`: 비밀번호 재설정 이메일
- `subscription_confirmation.html`: 구독 확인 이메일

### REST API

#### 이메일 전송 엔드포인트

```
POST /notifications/api/send/
```

요청 형식:
```json
{
  "email": "user@example.com",
  "subject": "알림 제목",
  "message": "알림 내용"
}
```

응답 형식:
```json
{
  "status": "success",
  "message": "이메일이 성공적으로 대기열에 추가되었습니다."
}
```

#### 이메일 템플릿 관리

```
GET /notifications/api/templates/ - 템플릿 목록 조회
POST /notifications/api/templates/ - 새 템플릿 생성
GET /notifications/api/templates/{id}/ - 특정 템플릿 조회
PUT /notifications/api/templates/{id}/ - 템플릿 업데이트
DELETE /notifications/api/templates/{id}/ - 템플릿 삭제
```

#### 이메일 로그 조회

```
GET /notifications/api/logs/ - 로그 목록 조회
GET /notifications/api/logs/{id}/ - 특정 로그 조회
```

쿼리 파라미터:
- `recipient`: 특정 수신자 필터링
- `status`: 상태별 필터링 (sent, failed, queued)

### 코드에서의 이메일 전송 예제

```python
import django_rq
from notifications.tasks import send_notification_email

# 이메일 작업 큐에 추가
django_rq.enqueue(
    send_notification_email,
    user_email='user@example.com',
    subject='알림 제목',
    message='알림 내용'
)
```

## 관리자 페이지

관리자 페이지에서 이메일 템플릿과 이메일 로그를 관리할 수 있습니다:

- 이메일 템플릿 관리: `/admin/notifications/emailtemplate/`
- 이메일 로그 확인: `/admin/notifications/emaillog/`

## 이메일 테스트

API 엔드포인트를 통해 테스트할 수 있습니다:

```bash
# cURL 사용 예시
curl -X POST \
  http://localhost:8000/notifications/api/send/ \
  -H 'Content-Type: application/json' \
  -H 'X-CSRFToken: your-csrf-token' \
  -d '{
    "email": "recipient@example.com",
    "subject": "테스트 이메일",
    "message": "이것은 테스트 이메일입니다."
}'
```

## 문제 해결

### 이메일이 전송되지 않는 경우

1. 워커가 실행 중인지 확인: `python manage.py rqworker default emails`
2. Redis 서버가 실행 중인지 확인
3. 이메일 설정이 올바른지 확인 (특히 Gmail 앱 비밀번호)
4. 로그 확인: `python manage.py rqworker --verbose default emails`로 워커를 실행하여 상세 로그 확인
5. 관리자 페이지에서 EmailLog 테이블 확인하여 오류 메시지 확인 