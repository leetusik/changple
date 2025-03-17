# (주)창플 AI 챗봇 개발 로드맵

## 프로젝트 개요
- **기간**: 2025년 3월 13일 - 4월 11일
  - **개발 기간**: 2025년 3월 13일 - 3월 23일
  - **QA 및 추가 기능 기간**: 2025년 3월 24일 - 4월 11일
- **목표**: AI 기반 챗봇 시스템 개발
- **주요 기능**: 네이버 카페 데이터 크롤링, 벡터 DB 저장, 챗봇 엔진 구현, 웹 인터페이스 개발
- **타겟 사이트**: 네이버 카페(https://cafe.naver.com/cjdckddus)

## 기술 스택
- **백엔드**: Python, Django, Django REST framework, Langchain
- **크롤링**: Playwright (로그인 기능 포함)
- **벡터 DB**: Pinecone
- **프론트엔드**: HTML, CSS, JavaScript
- **스케줄링**: RQ (Redis Queue)
- **캐싱 & 메시지 큐**: Redis
- **데이터베이스**: PostgreSQL
- **AI 통합**: OpenAI API (GPT-4o-mini)
- **배포**: Docker, Nginx
- **호스팅 옵션**: AWS, Google Cloud, Naver Cloud, Oracle Cloud (선택 예정)
- **인증**: Naver 로그인, Google 로그인
- **결제**: Toss Payment

## 개발 로드맵

### Phase 1: 개발 환경 설정 및 기초 작업 (3월 13일)
- **환경 설정**
  - Git 리포지토리 설정
  - 개발/스테이징/프로덕션 환경 구성
  - 팀원 권한 설정 및 작업 분배
  - Docker 컨테이너 설정
- **기술 스택 설정**
  - Django 프로젝트 초기화
  - Django REST framework 설치 및 설정
  - 프론트엔드 기본 디렉토리 구조 설정 (HTML, CSS, JavaScript)
  - PostgreSQL 데이터베이스 설정
  - Redis 설정
  - Python 가상 환경 및 패키지 설정
  - Nginx 설정
- **아키텍처 설계**
  - 시스템 아키텍처 다이어그램 작성
  - REST API 엔드포인트 정의 및 문서화
  - 데이터 모델 설계
  - Docker 컴포즈 파일 구성

### Phase 2: 크롤링 시스템 개발 (3월 14일 - 3월 16일)
- **3월 14일: 크롤링 기본 구조 개발**
  - Playwright 설정 및 기본 크롤링 기능 구현
  - 네이버 카페 로그인 메커니즘 구현
  - 카페 구조 분석 및 크롤링 전략 수립
  - HTML 파싱 로직 구현
  - 기본 데이터 추출 파이프라인 구축
  
- **3월 15일: 데이터 처리 및 저장**
  - HTML to CSV/JSON 변환 기능 구현
  - 카테고리별 데이터 수집 로직 구현
  - 데이터 전처리 파이프라인 구축
  - Pinecone 벡터 DB 연결 및 초기 설정
  - 데이터 임베딩 및 저장 로직 구현
  
- **3월 16일: 스케줄링 및 24시간 크롤링 시스템 완성**
  - RQ 작업 스케줄러 설정
  - Redis 연동 및 작업 큐 설정
  - 24시간 주기 크롤링 서비스 구현
  - 에러 처리 및 리트라이 메커니즘 구현
  - 크롤링 대시보드 개발
  - 선택된 클라우드 서비스에 배포 준비

### Phase 3: AI 챗봇 백엔드 개발 (3월 17일 - 3월 19일)
- **3월 17일: 기본 백엔드 구조**
  - Django 백엔드 API 구현
  - Django REST framework 시리얼라이저 및 뷰셋 구현
  - PostgreSQL 데이터 모델 구현
  - 사용자 인증 시스템 구현 (JWT 기반)
  - REST API 엔드포인트 개발 및 문서화
  
- **3월 18일: Langchain & OpenAI 통합**
  - Langchain 프레임워크 설정
  - GPT-4o-mini 모델 연동
  - 컨텍스트 관리 시스템 구현
  - 프롬프트 엔지니어링 및 최적화
  
- **3월 19일: 고급 챗봇 기능**
  - Pinecone 벡터 검색 연동
  - 관련 콘텐츠 검색 알고리즘 구현
  - 사용자별 채팅 제한 기능 구현
  - 컨텍스트 기반 응답 생성 시스템 구현

### Phase 4: 프론트엔드 개발 (3월 20일 - 3월 21일)
- **3월 20일: 기본 UI 개발**
  - HTML 템플릿 구조 설계
  - 기본 페이지 레이아웃 구현
  - CSS를 활용한 반응형 디자인 적용
  - 챗봇 인터페이스 디자인
  
- **3월 21일: 고급 기능 및 통합**
  - JavaScript를 활용한 실시간 채팅 인터페이스 구현
  - 사용자 프로필 및 설정 페이지
  - API 연동 및 상태 관리 구현
  - 에러 처리 및 로딩 상태 UI 구현

### Phase 5: 시스템 통합 및 초기 테스트 (3월 22일 - 3월 23일)
- **3월 22일: 통합 및 테스트**
  - 백엔드-프론트엔드 통합
  - 전체 시스템 테스트
  - 성능 최적화
  - 버그 수정 및 안정화
  
- **3월 23일: 1차 배포 준비**
  - 최종 테스트 및 QA
  - Docker 이미지 빌드 및 배포
  - Nginx 설정 확인
  - 클라이언트 1차 시연 준비
  - 개발 단계 마무리

### Phase 6: QA 및 추가 기능 개발 (3월 24일 - 4월 11일)
- **3월 24일 - 3월 31일: 심화 QA 및 버그 수정**
  - 사용자 테스트 및 피드백 수집
  - 성능 모니터링 및 최적화
  - 발견된 버그 수정
  - 보안 취약점 점검 및 보완

- **4월 1일 - 4월 8일: 추가 기능 개발**
  - 소셜 로그인 통합
    - 네이버 로그인 연동 구현
    - 구글 로그인 연동 구현
    - 사용자 인증 흐름 개선
    - 소셜 프로필 정보 연동
  - 결제 시스템 구현
    - Toss Payment 연동
    - 결제 프로세스 구축
    - 구독 모델 구현 (필요시)
    - 결제 내역 관리 기능
  - 무료 기능 추가 (회사 평판 향상용)
  - 사용자 피드백 기반 기능 개선
  - UX 개선 사항 반영
  - 데이터 품질 향상 작업

- **4월 9일 - 4월 11일: 최종 릴리즈 준비**
  - 최종 통합 테스트
  - 문서화 완료
  - 최종 클라이언트 시연
  - 프로젝트 인도 및 배포

## 주요 마일스톤
1. **3월 16일**: 크롤링 시스템 완성 (24시간 업데이트 포함)
2. **3월 19일**: AI 챗봇 백엔드 완성
3. **3월 21일**: 프론트엔드 개발 완성
4. **3월 23일**: 개발 완료 및 1차 배포
5. **4월 8일**: 추가 기능 개발 완료
6. **4월 11일**: 최종 프로젝트 인도

## 기술적 구현 세부사항

### 크롤링 시스템
- Playwright를 사용한 헤드리스 브라우저 자동화
- 네이버 카페 로그인 처리 및 세션 관리
- 특정 카테고리 및 페이지 타겟팅
- HTML 파싱 및 데이터 정제
- 메타데이터 추출 및 처리
- RQ 및 Redis를 활용한 주기적 작업 스케줄링
- 캡챠 대응 전략 구현 (필요시)

### 데이터 저장 및 처리
- 데이터 임베딩 생성 (텍스트 → 벡터)
- Pinecone 벡터 DB에 저장
- PostgreSQL에 메타데이터 및 사용자 데이터 저장
- Redis를 활용한 캐싱 및 성능 최적화
- 증분 업데이트 및 변경 감지 시스템

### AI 챗봇 엔진
- Langchain을 활용한 챗봇 파이프라인 구축
- GPT-4o-mini 모델 활용
- 컨텍스트 기반 질의응답 시스템
- 벡터 검색을 통한 관련 데이터 조회
- 프롬프트 엔지니어링 및 최적화
- 사용자별 일일 채팅 제한 관리
- 토큰 사용량 최적화 전략
- REST API를 통한 챗봇 엔진 접근 제어

### 웹 인터페이스
- HTML, CSS, JavaScript 기반 구현
- 모던 UI/UX 디자인
- 반응형 웹 디자인
- 실시간 채팅 인터페이스
- 사용자 인증 및 프로필 관리
- REST API와의 효율적인 통신

### 배포 및 인프라
- Docker 컨테이너화
- Nginx 웹 서버 설정
- 클라우드 서비스 배포 (AWS/Google/Naver/Oracle 중 선택)
- 멀티 컨테이너 구성 (웹서버, 백엔드, 크롤러, DB 등)

### API 및 백엔드 시스템
- Django REST framework를 활용한 RESTful API 구현
- API 버전 관리 및 문서화 (Swagger/OpenAPI)
- 시리얼라이저를 통한 데이터 검증 및 변환
- 뷰셋 및 라우터를 활용한 CRUD 엔드포인트 자동화
- 권한 및 인증 시스템 (JWT 기반)
- API 성능 최적화 (페이지네이션, 필터링, 캐싱)
- API 테스트 자동화

### 사용자 인증 시스템
- 자체 계정 시스템 구현
- 네이버 소셜 로그인 통합
  - OAuth 2.0 인증 흐름
  - 사용자 프로필 정보 활용
- 구글 소셜 로그인 통합
  - OAuth 2.0 인증 흐름
  - 사용자 프로필 정보 활용
- 세션 관리 및 보안
- JWT 기반 인증 시스템 구현
- REST framework 권한 클래스 활용

### 결제 시스템
- Toss Payment API 연동
- 결제 프로세스 구현
- 결제 내역 관리 및 조회
- 구독 모델 관리 (필요시)
- 결제 관련 알림 시스템

## 고려사항 및 리스크
- 네이버 카페 로그인 및 크롤링 정책 변경 가능성
- 캡챠 우회 전략 필요성
- API 할당량 및 사용량 관리 (특히 GPT-4o-mini)
- 데이터 품질 및 일관성 유지
- 성능 최적화 (벡터 검색 및 API 응답 시간)
- 보안 및 개인정보 관리
- 소셜 로그인 API 정책 변경 가능성
- 결제 시스템 보안 및 규제 준수

## 무료 기능 고려사항 (평판 향상용)
- 기본 일일 쿼리 제한 외 추가 무료 쿼리 제공
- 고급 검색 기능 무료 제공
- 기본 분석 대시보드 제공
- 공개 데이터 공유 기능

## 추가 질문사항
1. 네이버 카페 크롤링을 위한 계정 정보는 언제 공유 가능한지?
2. 챗봇의 페르소나 및 톤앤매너에 대한 구체적인 요구사항이 있는지?
3. 무료 기능으로 추가할 만한 좋은 아이디어가 있는지?
4. 최종적으로 어떤 클라우드 서비스를 선택할 계획인지?
5. 프로젝트 완료 후 유지보수 계획이 있는지?

---

이 로드맵은 초안이며, 논의 후 상세화될 예정입니다.


## expected file tree
.
├── README.md
├── config
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── docker-compose.yml
├── Dockerfile
├── manage.py
├── requirements.txt
├── nginx
│   ├── Dockerfile
│   └── nginx.conf
├── scraper
│   ├── __init__.py
│   ├── admin.py
│   ├── api
│   │   ├── __init__.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   └── views.py
│   ├── apps.py
│   ├── management
│   │   ├── __init__.py
│   │   └── commands
│   │       ├── __init__.py
│   │       ├── load_categories.py
│   │       ├── run_crawler.py
│   │       └── schedule_crawler.py
│   ├── migrations
│   ├── models.py
│   ├── services
│   │   ├── __init__.py
│   │   ├── crawler.py
│   │   └── scheduler.py
│   ├── tasks.py
│   └── tests.py
├── chatbot
│   ├── __init__.py
│   ├── admin.py
│   ├── api
│   │   ├── __init__.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   └── views.py
│   ├── apps.py
│   ├── migrations
│   ├── models.py
│   ├── services
│   │   ├── __init__.py
│   │   ├── langchain_service.py
│   │   ├── openai_service.py
│   │   └── pinecone_service.py
│   ├── tasks.py
│   └── tests.py
├── users
│   ├── __init__.py
│   ├── admin.py
│   ├── api
│   │   ├── __init__.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   └── views.py
│   ├── apps.py
│   ├── migrations
│   ├── models.py
│   ├── services
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   └── social_auth_service.py
│   └── tests.py
├── payments
│   ├── __init__.py
│   ├── admin.py
│   ├── api
│   │   ├── __init__.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   └── views.py
│   ├── apps.py
│   ├── migrations
│   ├── models.py
│   ├── services
│   │   ├── __init__.py
│   │   └── toss_payment_service.py
│   └── tests.py
├── static
│   ├── css
│   │   ├── main.css
│   │   ├── auth.css
│   │   ├── chat.css
│   │   └── payment.css
│   ├── img
│   │   ├── logo.png
│   │   └── icons
│   │       ├── user.png
│   │       └── chat.png
│   └── js
│       ├── main.js
│       ├── auth
│       │   ├── login.js
│       │   ├── register.js
│       │   ├── social-login.js
│       │   └── profile.js
│       ├── chat
│       │   ├── chat-interface.js
│       │   └── chat-input.js
│       ├── common
│       │   ├── header.js
│       │   └── sidebar.js
│       ├── payment
│       │   ├── payment-form.js
│       │   └── payment-history.js
│       └── services
│           ├── api.js
│           ├── auth.js
│           ├── chat.js
│           └── payment.js
├── templates
│   ├── base.html
│   ├── index.html
│   ├── auth
│   │   ├── login.html
│   │   ├── register.html
│   │   └── profile.html
│   ├── chat
│   │   └── chat.html
│   └── payment
│       ├── payment.html
│       └── history.html
├── logs
│   ├── naver_cafe_scraper.log
│   ├── scheduled_scraper.log
│   └── error.log
└── z_docs
    ├── (주)창플_견적서.png
    ├── (주)창플 AI 챗봇 개발 계약서.pdf
    ├── api_docs.md
    ├── git_guide.md
    ├── hello.md
    ├── roadmap.md
    └── deployment_guide.md