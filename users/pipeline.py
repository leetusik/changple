import logging

from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)

User = get_user_model()


def create_user(backend, user, response, *args, **kwargs):
    """
    Custom pipeline function to create a new user from Naver login data.
    """
    logger.info("Pipeline create_user called")
    logger.info(f"Backend: {backend.name}")
    logger.info(f"User exists: {user is not None}")

    if user:
        # User already exists, update their profile data
        logger.info(f"Existing user found: {user.username}")

        # Only update if it's a Naver user
        if backend.name == "naver" and user.provider == "naver":
            try:
                # Update profile data
                if response.get("profile_image"):
                    user.profile_image = response.get("profile_image")

                # Get Korean name from 'username' field in Naver response
                korean_name = response.get("username", "")
                if korean_name:
                    # Set name to Korean name but keep username as is
                    user.name = korean_name

                    # Set nickname to 'sugnag' for this specific user
                    if response.get("email") == "gusang0@naver.com":
                        user.nickname = "sugnag"
                    else:
                        # For other users, set nickname to email username
                        email_parts = user.email.split("@")
                        user.nickname = email_parts[0] if email_parts else ""

                user.save()
                logger.info(f"Updated existing user: {user.username}")
            except Exception as e:
                logger.error(f"Error updating user data: {str(e)}")

        return {"is_new": False}

    # Log response data for debugging
    if backend.name == "naver":
        logger.info("Processing Naver response")
        try:
            # Log the full response for debugging
            logger.info(f"Raw response keys: {response.keys()}")
            logger.info(f"Raw response data: {response}")

            # Extract user data directly from the response
            email = response.get("email")
            korean_name = response.get(
                "username", ""
            )  # Korean name is in username field
            profile_image = response.get("profile_image", "")
            social_id = response.get("id", "")

            # Set nickname to 'sugnag' for this specific user
            nickname = "sugnag" if email == "gusang0@naver.com" else email.split("@")[0]

            logger.info(
                f"Mapped data: email={email}, name={korean_name}, nickname={nickname}, id={social_id}"
            )

            if not email:
                logger.error("No email provided by Naver")
                return None

            # Create the user with the desired mapping
            logger.info(f"Creating new user with username: {korean_name}")
            user = User.objects.create(
                username=korean_name,  # Use Korean name as username
                email=email,
                user_type="social",
                provider="naver",
                social_id=social_id,
                profile_image=profile_image,
                name=korean_name,
                first_name=korean_name,
                nickname=nickname,  # Set nickname to 'sugnag' for this specific user
            )

            logger.info(f"User created successfully: {user.id}")
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
