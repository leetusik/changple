# 네이버 로그인 연동 가이드

이 문서는 네이버 OAuth를 통한 로그인 연동 방법을 설명합니다.

## 목차

1. 네이버 개발자 센터 설정
2. Django 설정 구성
3. 로그인 플로우
4. 프론트엔드 연동
5. 문제해결 및 팁

## 1. 네이버 개발자 센터 설정

### 1.1 애플리케이션 등록

1. [네이버 개발자 센터](https://developers.naver.com)에 로그인합니다.
2. "Application > 애플리케이션 등록"으로 이동합니다.
3. 다음 정보를 입력합니다:
   - 애플리케이션 이름: (주)창플 AI 챗봇
   - 사용 API: "네이버 로그인" 선택
   - 서비스 환경: "Web 환경"에 체크
   - 서비스 URL: 서비스 URL 입력 (예: https://yourdomain.com)
   - 네이버 로그인 Callback URL: 콜백 URL 입력 (예: https://yourdomain.com/users/api/login/naver/callback/)
4. 이용약관에 동의하고 등록합니다.

### 1.2 필요한 정보 확인

애플리케이션 등록 후, 다음 정보를 기록해 둡니다:
- Client ID
- Client Secret

## 2. Django 설정 구성

### 2.1 settings.py 설정 추가

`settings.py` 파일에 다음 설정을 추가합니다:

```python
# Naver OAuth Settings
NAVER_CLIENT_ID = 'your-client-id'
NAVER_CLIENT_SECRET = 'your-client-secret'
NAVER_REDIRECT_URI = 'http://localhost:8000/users/naver/callback/'

# Frontend URL for redirects after login
FRONTEND_URL = 'http://localhost:3000'
```

실제 값으로 교체하세요. 개발 환경에서는 다음과 같이 설정할 수 있습니다:

```python
NAVER_REDIRECT_URI = 'http://localhost:8000/users/api/login/naver/callback/'
FRONTEND_URL = 'http://localhost:3000'  # React 등의 프론트엔드 서버
```

### 2.2 AUTH_USER_MODEL 설정

`settings.py`에 사용자 모델 설정을 추가합니다:

```python
AUTH_USER_MODEL = 'users.CustomUser'
```

### 2.3 JWT 설정

Simple JWT를 사용하는 경우, 다음 설정을 추가합니다:

```python
INSTALLED_APPS = [
    # ...
    'rest_framework',
    'rest_framework_simplejwt',
    # ...
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
}
```

## 3. 로그인 플로우

### 3.1 로그인 프로세스

네이버 로그인 플로우는 다음과 같이 진행됩니다:

1. 사용자가 "네이버로 로그인" 버튼 클릭
2. `/users/api/login/naver/` 엔드포인트로 리디렉션
3. 네이버 로그인 페이지로 리디렉션 (상태값 포함)
4. 사용자가 네이버에 로그인
5. 네이버가 콜백 URL로 인증 코드와 상태값 전송
6. 인증 코드로 액세스 토큰 획득
7. 액세스 토큰으로 사용자 프로필 정보 획득
8. 사용자 정보로 로그인 또는 회원가입 처리
9. JWT 토큰 생성하여 프론트엔드로 리디렉션

## 4. 프론트엔드 연동

### 4.1 로그인 버튼 추가

로그인 페이지에 네이버 로그인 버튼을 추가합니다:

```html
<a href="/users/api/login/naver/" class="naver-login-btn">
  <img src="https://static.nid.naver.com/oauth/button_g.PNG" width="200">
</a>
```

### 4.2 토큰 처리

로그인 성공 후 리디렉션된 페이지에서 JWT 토큰을 저장합니다:

```javascript
// login/success 페이지에서
const urlParams = new URLSearchParams(window.location.search);
const token = urlParams.get('token');

if (token) {
  // 토큰을 로컬 스토리지에 저장
  localStorage.setItem('access_token', token);
  
  // 메인 페이지로 리디렉션
  window.location.href = '/';
}
```

### 4.3 인증 상태 유지

API 호출 시 토큰을 헤더에 포함합니다:

```javascript
// API 호출 함수
async function fetchUserInfo() {
  const token = localStorage.getItem('access_token');
  
  const response = await fetch('/users/api/me/', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  return await response.json();
}
```

## 5. 문제해결 및 팁

### 5.1 일반적인 문제

- **CORS 에러**: 개발 환경에서 django-cors-headers 패키지를 설치하고 설정합니다.
- **리디렉션 실패**: 네이버 개발자 센터에 등록된 콜백 URL이 정확한지 확인합니다.
- **토큰 만료**: 액세스 토큰 만료 시 재로그인하거나 리프레시 토큰을 사용해 갱신합니다.

### 5.2 보안 팁

- 항상 state 파라미터를 사용해 CSRF 공격을 방지합니다.
- 클라이언트 비밀키는 절대 프론트엔드에 노출시키지 마세요.
- HTTPS를 사용하여 통신 내용을 암호화합니다.

### 5.3 추가 설정 옵션

네이버 로그인 API에서 다양한 사용자 정보를 요청하기 위해 scope 파라미터를 추가할 수 있습니다:

```python
# 추가 정보 요청을 위한 scope 설정
params = {
    'response_type': 'code',
    'client_id': settings.NAVER_CLIENT_ID,
    'redirect_uri': settings.NAVER_REDIRECT_URI,
    'state': state,
    'scope': 'name email profile_image gender age birthday'
}
```

## 참고 자료

- [네이버 로그인 API 문서](https://developers.naver.com/docs/login/api/)
- [Django REST Framework 문서](https://www.django-rest-framework.org/)
- [Simple JWT 문서](https://django-rest-framework-simplejwt.readthedocs.io/) 