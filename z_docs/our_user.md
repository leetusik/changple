# 창플 (Changple) Users App Documentation

## Overview

The Users app manages user authentication, registration, and profile management for the Changple application. It supports both traditional web-based authentication and API-based authentication, with a focus on social login integration (specifically Naver OAuth).

## Recent Updates

### Username & User Model Updates (2024-03-21)

1. **Username Handling**:
   - Username field is now hidden from forms and admin interface
   - Automatically generated from social_id for social users (`provider_social_id`)
   - Uses ID-based format for admin users (`id_123`)
   - Still maintains uniqueness required by Django auth

2. **Korean-Focused User Model**:
   - Primary focus on `name` and `nickname` fields for Korean users
   - De-emphasized `first_name` and `last_name` fields in the admin interface
   - Updated `__str__` representation to use name/nickname instead of username

3. **Mobile Number Integration**:
   - Added API integration to fetch mobile numbers from Naver's profile API
   - Automatic storage of mobile numbers during user creation and profile updates

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
    # Username is hidden from forms but maintained for Django auth
    username = models.CharField(
        max_length=150,
        unique=True,
        help_text="Internal field used for authentication only.",
        editable=False,  # Hide from forms
    )
    
    # User type (admin or social)
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default="social")
    
    # Social auth fields
    provider = models.CharField(max_length=30, blank=True)
    social_id = models.CharField(max_length=100, blank=True)
    profile_image = models.URLField(blank=True)
    
    # Korean context fields
    name = models.CharField(max_length=255, null=True, blank=True)
    nickname = models.CharField(max_length=100, blank=True)
    mobile = models.CharField(max_length=20, blank=True, null=True)
    
    # Query limit fields
    daily_query_limit = models.IntegerField(default=10)
    daily_queries_used = models.IntegerField(default=0)
    last_query_reset = models.DateTimeField(default=timezone.now)
    
    # Premium status
    is_premium = models.BooleanField(default=False)
    premium_until = models.DateTimeField(null=True, blank=True)
    
    def save(self, *args, **kwargs):
        # For social users, use social_id as username if available
        if self.is_social_user() and self.social_id and not self.username:
            provider_prefix = f"{self.provider}_" if self.provider else ""
            self.username = f"{provider_prefix}{self.social_id}"
        
        # For admin users or if no social_id is available, use ID-based username
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new and not self.username and not self.social_id:
            self.username = f"id_{self.pk}"
            type(self).objects.filter(pk=self.pk).update(username=self.username)
```

Key features:
- `username`: Hidden field used internally for Django authentication
- `user_type`: Distinguishes between admin users and social login users
- `provider`: Identifies the social login provider (e.g., "naver")
- `social_id`: Stores the unique ID from the social provider
- `profile_image`: URL to the user's profile image from social provider
- `name`: User's full Korean name (from social provider)
- `nickname`: User's preferred display name
- `mobile`: User's mobile number (retrieved from Naver API)

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
- Retrieves mobile number via additional API call to Naver's profile API

The mobile number retrieval is handled by the `get_naver_profile_data` function:

```python
def get_naver_profile_data(access_token):
    """
    Make an additional API call to get more profile data including mobile number
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get("https://openapi.naver.com/v1/nid/me", headers=headers)
    # Process response to extract mobile number
    profile_data = response.json().get("response", {})
    return profile_data
```

#### 3. Authentication Backend

Located in `backends.py`, the app provides two custom authentication backends:

1. `SocialAuthBackend`: Authenticates users based on their social provider and ID
2. `EmailBackend`: Allows admin users to log in using email instead of username

```python
class SocialAuthBackend(ModelBackend):
    def authenticate(self, request, provider=None, social_id=None, **kwargs):
        if provider is None or social_id is None:
            return None

        try:
            user = User.objects.get(provider=provider, social_id=social_id)
            return user
        except User.DoesNotExist:
            return None
```

## Admin Interface

The admin interface has been customized to hide the username field and focus on the name and nickname fields:

```python
class CustomUserAdmin(UserAdmin):
    list_display = (
        "id",
        "name",
        "nickname",
        "email",
        "user_type",
        "is_premium",
        "daily_queries_used",
        "is_staff",
        "is_active",
    )
    
    fieldsets = (
        (None, {"fields": ("password",)}),  # Username removed
        (
            _("Korean User Information"),
            {
                "fields": (
                    "name",
                    "nickname",
                    "email",
                    "mobile",
                    "profile_image",
                ),
            },
        ),
        # ... other fieldsets
    )
```

## Service Layer

The service layer contains the business logic, separated from views:

### 1. Auth Service

Located in `services/auth_service.py`, this provides general authentication utilities:

- `get_user_by_id`: Retrieves a user by ID
- `get_user_by_email`: Retrieves a user by email

### 2. Social Auth Service

Located in `services/social_auth_service.py`, this handles social authentication logic:

- `get_or_create_user`: Creates or retrieves a user based on social data
- `update_user_profile`: Updates user profile with social data

## API Layer

The API layer provides REST endpoints for user data:

### 1. Serializers

Located in `api/serializers.py`, these convert model instances to JSON:

- `UserSerializer`: Full user model serialization with username as read-only
- `UserProfileSerializer`: User profile data serialization with username as read-only
- `SocialAuthSerializer`: Serializes social auth request data

### 2. Views

Located in `api/views.py`, these handle API requests:

- `UserViewSet`: CRUD operations for user model
- `SocialAuthView`: Handles social authentication via API

## Security Considerations

1. **OAuth State Parameter**: Used to prevent CSRF attacks
2. **Password Storage**: Admin users have passwords stored using Django's hashing
3. **Social Users**: Automatically assigned a secure random password (never used)
4. **Username Field**: Hidden from forms and API but maintained for Django auth
5. **Mobile Number Security**: Retrieved securely via API using OAuth token

## Custom Logic for Special Cases

1. **Username Generation**: 
   - Social users: `{provider}_{social_id}` (e.g., "naver_12345")
   - Admin users: `id_{id}` (e.g., "id_123")
   
2. **Special Nickname**: For user with email "gusang0@naver.com", nickname is set to "sugnag"

3. **Korean Name Handling**: 
   - Displays Korean names properly 
   - Focuses on full name rather than first/last name split

4. **Mobile Number**: Retrieved from Naver's additional profile API

## Testing

The app includes test files that verify:
- User model functionality
- Authentication flows
- Social login integration

## Deployment Considerations

1. **Environment Variables**: Social auth keys should be stored as environment variables
2. **HTTPS**: Social auth requires HTTPS in production
3. **Callback URLs**: Must be configured properly on Naver Developer Console 