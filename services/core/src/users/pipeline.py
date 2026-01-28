"""
Social auth pipeline functions for Naver OAuth.
"""

import json
import logging
import secrets
import string

import requests
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)

User = get_user_model()


def get_naver_profile_data(access_token: str) -> dict:
    """
    Make an additional API call to get more profile data including mobile number.

    Args:
        access_token: The OAuth access token from Naver

    Returns:
        dict: Additional profile data from Naver
    """
    try:
        logger.info("Fetching additional profile data from Naver API")
        headers = {"Authorization": f"Bearer {access_token}"}

        response = requests.get(
            "https://openapi.naver.com/v1/nid/me",
            headers=headers,
            timeout=10,
        )

        if response.status_code != 200:
            logger.error(
                f"Failed to fetch profile data: {response.status_code} - {response.text}"
            )
            return {}

        data = response.json()
        logger.info(
            f"Received profile API response: {json.dumps(data, indent=2, ensure_ascii=False)}"
        )

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

    try:
        logger.info(
            f"Full response: {json.dumps(response, indent=2, ensure_ascii=False)}"
        )
    except Exception:
        logger.info(f"Full response (not JSON serializable): {response}")

    logger.info(f"Contains 'mobile' field: {'mobile' in response}")
    if "mobile" in response:
        logger.info(f"Mobile value: {response.get('mobile')}")
    logger.info("============================")

    # Fetch additional profile data if we have an access token
    additional_profile_data = {}
    access_token = response.get("access_token")
    if access_token:
        additional_profile_data = get_naver_profile_data(access_token)
        logger.info("Access token found in response - will store for later use")

    # Get mobile from additional profile data if available
    mobile = additional_profile_data.get("mobile", "")
    if mobile:
        logger.info(f"Found mobile in additional profile data: {mobile}")
        response["mobile"] = mobile

    if user:
        # User already exists, update their profile data
        logger.info(f"Existing user found: {user.id}")

        if backend.name == "naver" and user.provider == "naver":
            try:
                # Update profile data
                if response.get("profile_image"):
                    user.profile_image = response.get("profile_image")

                # Get Korean name from 'username' field in Naver response
                korean_name = response.get("username", "")
                if korean_name:
                    user.name = korean_name

                # Update nickname
                if response.get("nickname"):
                    user.nickname = response.get("nickname")
                elif not user.nickname and response.get("email"):
                    email_parts = response.get("email").split("@")
                    user.nickname = email_parts[0] if email_parts else ""

                # Update mobile if available
                if mobile:
                    logger.info(f"Updating mobile for existing user: {mobile}")
                    user.mobile = mobile

                # Store access token for disconnection
                if access_token:
                    logger.info(f"Updating access token for user {user.id}")
                    user.naver_access_token = access_token

                user.save()
                logger.info(f"Updated existing user: {user.id}")
            except Exception as e:
                logger.error(f"Error updating user data: {str(e)}")

        return {"is_new": False}

    # Create new user
    if backend.name == "naver":
        logger.info("Processing Naver response")
        try:
            email = response.get("email")
            korean_name = response.get("username", "")
            profile_image = response.get("profile_image", "")
            social_id = response.get("id", "")

            nickname = response.get("nickname", "")
            if not nickname and email:
                nickname = email.split("@")[0]

            logger.info(
                f"Mapped data: email={email}, name={korean_name}, "
                f"nickname={nickname}, id={social_id}, mobile={mobile}"
            )

            if not email:
                logger.error("No email provided by Naver")
                return None

            # Generate a secure random password
            alphabet = string.ascii_letters + string.digits + string.punctuation
            password = "".join(secrets.choice(alphabet) for _ in range(20))

            # Create the username explicitly using provider_social_id format
            username = f"{backend.name}_{social_id}"
            logger.info(
                f"Creating new user with social_id as username: {username}, name: {korean_name}"
            )

            if mobile:
                logger.info(f"Setting mobile for new user: {mobile}")

            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                user_type="social",
                provider="naver",
                social_id=social_id,
                profile_image=profile_image,
                name=korean_name,
                nickname=nickname,
                mobile=mobile,
                naver_access_token=access_token,
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
