# Naver OAuth2 Login Integration

This guide will help you test the Naver OAuth2 login integration locally.

## Prerequisites

1. Make sure you have registered your application in the [Naver Developer Center](https://developers.naver.com)
2. Configure the following settings in your Naver application:
   - Service URL: `http://localhost:8000`
   - Callback URL: `http://localhost:8000/users/api/login/naver/callback/`
3. Update your `.env` file with your Naver API credentials:
   ```
   SOCIAL_AUTH_NAVER_CLIENT_ID=your_client_id
   SOCIAL_AUTH_NAVER_CLIENT_SECRET=your_client_secret
   ```

## Testing Locally

### Session-based Authentication

1. Visit `http://localhost:8000/login/` or `http://localhost:8000/users/login/`
2. Click on "Login with Naver (Session)"
3. After logging in to Naver, you will be redirected to your profile page
4. You're now logged in using Django's session-based authentication

### API/JWT Authentication

1. Visit `http://localhost:8000/login/` or `http://localhost:8000/users/login/`
2. Click on "Login with Naver (API/JWT)"
3. After logging in to Naver, you will be redirected to a success page
4. Your JWT tokens are stored in local storage
5. Visit `http://localhost:8000/users/api/test/` to test API authentication
6. Click "Test API Endpoint" to verify that your JWT token is working

## API Endpoints

- `/users/api/login/naver/` - Initiates Naver login flow for API clients
- `/users/api/login/naver/callback/` - Callback URL for Naver OAuth
- `/users/api/me/` - Returns information about the authenticated user (requires JWT)

## Using JWT in Your Frontend

To use the JWT token in your frontend application:

```javascript
// Add the token to API requests
async function fetchData() {
  const token = localStorage.getItem('access_token');
  
  const response = await fetch('/api/endpoint', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  return await response.json();
}
```

## Troubleshooting

1. **Callback URL Error**: Make sure the callback URL in Naver Developer Center exactly matches `http://localhost:8000/users/api/login/naver/callback/`
2. **Invalid Client ID/Secret**: Verify that your `.env` file contains the correct credentials
3. **JWT Authentication Error**: Check that you're including the token in the Authorization header with the 'Bearer' prefix 