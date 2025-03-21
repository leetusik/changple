import json
import logging
import re
import secrets
import string
import uuid

import requests
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)

User = get_user_model()


def get_naver_profile_data(access_token):
    """
    Make an additional API call to get more profile data including mobile number

    Args:
        access_token: The OAuth access token from Naver

    Returns:
        dict: Additional profile data from Naver
    """
    try:
        logger.info("Fetching additional profile data from Naver API")
        headers = {"Authorization": f"Bearer {access_token}"}

        # Make API call to Naver's profile API
        response = requests.get("https://openapi.naver.com/v1/nid/me", headers=headers)

        if response.status_code != 200:
            logger.error(
                f"Failed to fetch profile data: {response.status_code} - {response.text}"
            )
            return {}

        # Parse response
        data = response.json()
        logger.info(
            f"Received profile API response: {json.dumps(data, indent=2, ensure_ascii=False)}"
        )

        # Extract mobile from response if available
        profile_data = data.get("response", {})
        mobile = profile_data.get("mobile", "")

        logger.info(f"Mobile from profile API: {mobile}")
        return profile_data

    except Exception as e:
        logger.error(f"Error fetching Naver profile data: {str(e)}")
        return {}


def create_user(backend, user, response, *args, **kwargs):
    """
    Custom pipeline function to create a new user from Naver login data.
    """
    logger.info("Pipeline create_user called")
    logger.info(f"Backend: {backend.name}")
    logger.info(f"User exists: {user is not None}")

    # Log full response data for debugging
    logger.info("==== FULL RESPONSE DATA ====")
    logger.info(f"Response type: {type(response)}")
    logger.info(
        f"Response keys: {response.keys() if hasattr(response, 'keys') else 'No keys method'}"
    )

    # Pretty print the entire response for better readability
    try:
        logger.info(
            f"Full response: {json.dumps(response, indent=2, ensure_ascii=False)}"
        )
    except:
        logger.info(f"Full response (not JSON serializable): {response}")

    # Check specifically for mobile field
    logger.info(f"Contains 'mobile' field: {'mobile' in response}")
    if "mobile" in response:
        logger.info(f"Mobile value: {response.get('mobile')}")
    logger.info("============================")

    # Fetch additional profile data if we have an access token
    additional_profile_data = {}
    if response.get("access_token"):
        additional_profile_data = get_naver_profile_data(response.get("access_token"))

    # Get mobile from additional profile data if available
    mobile = additional_profile_data.get("mobile", "")
    if mobile:
        logger.info(f"Found mobile in additional profile data: {mobile}")
        # Add to response for later use
        response["mobile"] = mobile

    if user:
        # User already exists, update their profile data
        logger.info(f"Existing user found: {user.id}")

        # Only update if it's a Naver user
        if backend.name == "naver" and user.provider == "naver":
            try:
                # Update profile data
                if response.get("profile_image"):
                    user.profile_image = response.get("profile_image")

                # Get Korean name from 'username' field in Naver response
                korean_name = response.get("username", "")
                if korean_name:
                    # Set name to Korean name (primary name field)
                    user.name = korean_name

                # Set nickname (special case for specific user)
                if response.get("email") == "gusang0@naver.com":
                    user.nickname = "sugnag"
                elif not user.nickname and response.get("email"):
                    # For other users, set nickname to email username
                    email_parts = response.get("email").split("@")
                    user.nickname = email_parts[0] if email_parts else ""

                # Update from nickname field in response if available
                if response.get("nickname"):
                    user.nickname = response.get("nickname")

                # Update mobile if available (from additional profile data)
                if mobile:
                    logger.info(f"Updating mobile for existing user: {mobile}")
                    user.mobile = mobile
                else:
                    logger.info("No mobile field found for existing user")

                user.save()
                logger.info(f"Updated existing user: {user.id}")
            except Exception as e:
                logger.error(f"Error updating user data: {str(e)}")

        return {"is_new": False}

    # Log response data for debugging
    if backend.name == "naver":
        logger.info("Processing Naver response")
        try:
            # Extract user data directly from the response
            email = response.get("email")
            korean_name = response.get(
                "username", ""
            )  # Korean name is in username field
            profile_image = response.get("profile_image", "")
            social_id = response.get("id", "")
            # Mobile now comes from additional profile data

            # Get nickname from response or fallback to email username
            nickname = response.get("nickname", "")
            if not nickname:
                if email == "gusang0@naver.com":
                    nickname = "sugnag"
                elif email:
                    nickname = email.split("@")[0]

            logger.info(
                f"Mapped data: email={email}, name={korean_name}, nickname={nickname}, id={social_id}, mobile={mobile}"
            )

            if not email:
                logger.error("No email provided by Naver")
                return None

            # Generate a secure random password
            # Social users won't use this password, but Django's User model requires it
            alphabet = string.ascii_letters + string.digits + string.punctuation
            password = "".join(secrets.choice(alphabet) for _ in range(20))

            # Create the username explicitly using provider_social_id format
            username = f"{backend.name}_{social_id}"
            logger.info(
                f"Creating new user with social_id as username: {username}, name: {korean_name}"
            )

            # Log if mobile field is being set
            if mobile:
                logger.info(f"Setting mobile for new user: {mobile}")
            else:
                logger.info("No mobile field available when creating new user")

            user = User.objects.create_user(
                username=username,  # Must explicitly provide username for create_user method
                email=email,
                password=password,  # Set the random password
                user_type="social",
                provider="naver",
                social_id=social_id,  # This should be unique per user
                profile_image=profile_image,
                name=korean_name,  # Set the Korean name as the primary name
                nickname=nickname,  # Set the nickname
                mobile=mobile,
                # Don't use first_name/last_name for Korean context
            )

            logger.info(f"User created successfully with ID: {user.id}")
            return {
                "user": user,
                "is_new": True,
            }
        except Exception as e:
            logger.error(f"Error creating user from Naver data: {str(e)}")
            import traceback

            logger.error(traceback.format_exc())

    else:
        logger.info(f"Unsupported backend: {backend.name}")

    return None
