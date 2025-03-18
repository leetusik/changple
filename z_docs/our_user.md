# 창플 (Changple) Users App Documentation

## Overview

The Users app manages user authentication, registration, and profile management for the Changple application. It supports both traditional web-based authentication and API-based authentication, with a focus on social login integration (specifically Naver OAuth).

## Recent Updates

### Restructuring (2024-03-18)

1. **App Structure Reorganization**:
   - Implemented proper directory structure according to the project roadmap
   - Created dedicated API and Services directories
   - Separated business logic into service classes

2. **Template Reorganization**:
   - Moved templates to follow standard pattern: auth/, chat/, payment/
   - Removed debugging templates like auth_logs.html
   - Renamed 'mypage' to 'profile' for consistency

3. **URL Updates**:
   - Changed 'mypage' URL pattern to 'profile'
   - Simplified Naver login URLs
   - Removed debug endpoints

## Directory Structure

```
users/
├── __init__.py
├── admin.py            # Django admin configuration for User model
├── api/                # REST API components
│   ├── __init__.py
│   ├── serializers.py  # User data serializers for API
│   ├── urls.py         # API URL routing
│   └── views.py        # API views and viewsets
├── apps.py             # Django app configuration
├── backends.py         # Custom authentication backends
├── forms.py            # User forms for admin interface
├── middleware.py       # Authentication middleware
├── migrations/         # Database migrations
├── models.py           # User model definition
├── pipeline.py         # Social auth pipeline functions
├── services/           # Business logic services
│   ├── __init__.py
│   ├── auth_service.py         # General auth services
│   └── social_auth_service.py  # Social auth specific services
├── tests.py            # Test files
├── urls.py             # Web URL routing
└── views.py            # Web views for authentication
```

## Template Structure

```
templates/
├── base.html           # Base template with common layout
├── index.html          # Homepage with login options
├── auth/               # Authentication templates
│   ├── login.html      # Login page
│   └── profile.html    # User profile page (previously mypage.html)
├── chat/               # Chat templates
│   └── chat.html       # Chatbot interface
└── payment/            # Payment templates
    ├── payment.html    # Payment options and checkout
    └── history.html    # Payment history
```

## User Model

The app extends Django's AbstractUser to create a custom User model with additional fields for social authentication:

```python
class User(AbstractUser):
    # User type (admin or social)
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default="social")
    
    # Social auth fields
    provider = models.CharField(max_length=30, blank=True)
    social_id = models.CharField(max_length=100, blank=True)
    profile_image = models.URLField(blank=True)
    
    # Profile fields
    name = models.CharField(max_length=255, null=True, blank=True)
    nickname = models.CharField(max_length=100, blank=True)
```

Key features:
- `user_type`: Distinguishes between admin users and social login users
- `provider`: Identifies the social login provider (e.g., "naver")
- `social_id`: Stores the unique ID from the social provider
- `profile_image`: URL to the user's profile image from social provider
- `name`: User's real name (from social provider)
- `nickname`: User's nickname

## Authentication Flows

### 1. Web-based Authentication (Traditional)

Located in `views.py` and `urls.py`, this flow handles browser-based authentication:

- **Social Login Initiation**: `NaverLoginView` redirects to Naver OAuth login page
- **OAuth Callback Processing**: `NaverCallbackView` processes the OAuth callback and authenticates the user
- **Logout**: `logout_view` handles user logout

URL patterns:
```python
path("naver/login/", NaverLoginView.as_view(), name="naver_login"),
path("naver/callback/", NaverCallbackView.as_view(), name="naver_callback"),
path("logout/", logout_view, name="logout"),
```

### 2. API-based Authentication

Located in `api/views.py` and `api/urls.py`, this flow provides JSON API endpoints:

- **User Profile**: `UserViewSet.profile` action returns the current user's profile
- **Profile Update**: `UserViewSet.update_profile` action updates user profile data
- **Social Auth**: `SocialAuthView` provides an API endpoint for social authentication

URL patterns:
```python
router.register(r'users', UserViewSet)
path('social-auth/', SocialAuthView.as_view(), name='social-auth'),
```

## Social Login Integration

### Flow Overview

1. User clicks "Login with Naver" button
2. Browser redirects to Naver OAuth login page 
3. After successful Naver login, Naver redirects back to our callback URL
4. The callback view processes the data and authenticates the user
5. User is redirected to the home page

### Key Components

#### 1. OAuth Configuration

The social authentication is configured via Django settings:

```python
SOCIAL_AUTH_NAVER_KEY = 'your_naver_client_id'
SOCIAL_AUTH_NAVER_SECRET = 'your_naver_client_secret'
```

#### 2. Social Auth Pipeline

Located in `pipeline.py`, the pipeline function `create_user` handles user creation and updates during the OAuth flow:

- Creates new users based on Naver profile data
- Updates existing user profiles with fresh data from Naver
- Sets special nickname "sugnag" for a specific user (gusang0@naver.com)

#### 3. Authentication Backend

Located in `backends.py`, the `SocialAuthBackend` authenticates users based on their social provider and ID:

```python
def authenticate(self, request, provider=None, social_id=None, **kwargs):
    if provider is None or social_id is None:
        return None

    try:
        user = User.objects.get(provider=provider, social_id=social_id)
        return user
    except User.DoesNotExist:
        return None
```

#### 4. Middleware

Located in `middleware.py`, the `NaverAuthMiddleware` handles Naver OAuth state parameter for security.

## Service Layer

The service layer contains the business logic, separated from views:

### 1. Auth Service

Located in `services/auth_service.py`, this provides general authentication utilities:

- `get_user_by_id`: Retrieves a user by ID
- `get_user_by_email`: Retrieves a user by email
- `generate_unique_username`: Generates a unique username

### 2. Social Auth Service

Located in `services/social_auth_service.py`, this handles social authentication logic:

- `get_or_create_user`: Creates or retrieves a user based on social data
- `update_user_profile`: Updates user profile with social data

## API Layer

The API layer provides REST endpoints for user data:

### 1. Serializers

Located in `api/serializers.py`, these convert model instances to JSON:

- `UserSerializer`: Full user model serialization
- `UserProfileSerializer`: User profile data serialization
- `SocialAuthSerializer`: Serializes social auth request data

### 2. Views

Located in `api/views.py`, these handle API requests:

- `UserViewSet`: CRUD operations for user model
- `SocialAuthView`: Handles social authentication via API

## Integration Points

### 1. Django Settings

The app integrates with Django via settings:

```python
AUTH_USER_MODEL = 'users.User'

AUTHENTICATION_BACKENDS = [
    'users.backends.SocialAuthBackend',
    'django.contrib.auth.backends.ModelBackend',
]

MIDDLEWARE = [
    # ...
    'users.middleware.NaverAuthMiddleware',
]

SOCIAL_AUTH_PIPELINE = [
    # ...
    'users.pipeline.create_user',
]
```

### 2. Templates

The app connects to templates for:
- Login page (`auth/login.html`)
- Profile display (`auth/profile.html`)
- The main layout (`base.html`) includes navigation links to profiles and authentication

### 3. Main URLs

The app connects to the main URL configuration:

```python
# In config/urls.py:
path("users/", include("users.urls")),

# Profile URL
path(
    "profile/",
    login_required(TemplateView.as_view(template_name="auth/profile.html")),
    name="profile",
),

# Root-level Naver auth URLs for easier access
path("naver/callback/", NaverCallbackView.as_view(), name="naver_callback"),
path("naver/login/", NaverLoginView.as_view(), name="naver_login"),
```

## Custom Logic for Special Cases

1. **Special Nickname**: For the user with email "gusang0@naver.com", the nickname is set to "sugnag"
2. **Username Format**: For Korean users, their username is set to their Korean name
3. **Profile Image**: Social profile images are stored as URLs, not downloaded

## Testing

The app includes test files that verify:
- User model functionality
- Authentication flows
- Social login integration

## Security Considerations

1. **OAuth State Parameter**: Used to prevent CSRF attacks
2. **Password Storage**: Admin users have passwords stored using Django's hashing
3. **Permissions**: API endpoints have appropriate permission classes
4. **JWT Authentication**: Used for API authentication where appropriate

## Deployment Considerations

1. **Environment Variables**: Social auth keys should be stored as environment variables
2. **HTTPS**: Social auth requires HTTPS in production
3. **Callback URLs**: Must be configured properly on Naver Developer Console 