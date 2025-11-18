"""
Firebase Admin SDK initialization and token verification service.
"""
import firebase_admin
from firebase_admin import credentials, auth
from firebase_admin.exceptions import FirebaseError
import logging
import os
import json
from typing import Dict, Optional
from app.config import get_settings

logger = logging.getLogger(__name__)


def _load_credentials_with_env_key(json_path: str, private_key_from_env: str) -> Dict:
    """
    Load Firebase credentials from JSON file and replace private_key with value from environment variable.
    
    Args:
        json_path: Path to Firebase credentials JSON file
        private_key_from_env: Private key from FIREBASE_PRIVATE_KEY environment variable
        
    Returns:
        Credentials dictionary with private_key replaced
    """
    with open(json_path, 'r') as f:
        cred_dict = json.load(f)
    
    # Replace private_key with value from environment variable
    if private_key_from_env:
        cred_dict['private_key'] = private_key_from_env.replace("\\n", "\n")  # Handle escaped newlines
    elif 'private_key' not in cred_dict:
        raise ValueError("FIREBASE_PRIVATE_KEY environment variable is required (private_key not found in JSON file)")
    else:
        logger.warning("FIREBASE_PRIVATE_KEY not set, using private_key from JSON file")
    
    return cred_dict

# Global flag to track if Firebase has been initialized
_firebase_initialized = False


def initialize_firebase() -> None:
    """
    Initialize Firebase Admin SDK.
    
    Uses GOOGLE_APPLICATION_CREDENTIALS environment variable if set,
    otherwise tries firebase_credentials_path from settings.
    """
    global _firebase_initialized
    
    if _firebase_initialized:
        logger.info("Firebase Admin SDK already initialized")
        return
    
    try:
        settings = get_settings()
        
        # Check if Firebase is already initialized
        try:
            firebase_admin.get_app()
            logger.info("Firebase Admin SDK already initialized")
            _firebase_initialized = True
            return
        except ValueError:
            # Not initialized yet, continue
            pass
        
        # Try to initialize with credentials
        cred = None
        
        # First, try GOOGLE_APPLICATION_CREDENTIALS (standard approach - file path)
        google_creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if google_creds_path and os.path.exists(google_creds_path):
            logger.info(f"Initializing Firebase with GOOGLE_APPLICATION_CREDENTIALS: {google_creds_path}")
            cred_dict = _load_credentials_with_env_key(google_creds_path, settings.firebase_private_key)
            cred = credentials.Certificate(cred_dict)
        # Second, try firebase_credentials_path from settings (JSON file with private_key from env)
        # Also try default Docker path if not specified but private_key is set
        elif settings.firebase_credentials_path or settings.firebase_private_key:
            # Resolve path - handle both relative and absolute paths
            # Default to Docker path if not specified but private_key is set
            specified_path = settings.firebase_credentials_path.strip() if settings.firebase_credentials_path else ""
            creds_path = specified_path or "/app/firebase-credentials.json"
            
            # Try multiple possible locations
            possible_paths = []
            if creds_path:
                possible_paths.append(creds_path)
            if creds_path and not os.path.isabs(creds_path):
                possible_paths.append(f"/app/{creds_path}")
                possible_paths.append(f"/app/app/{creds_path}")
            # Also try default Docker location
            possible_paths.append("/app/firebase-credentials.json")
            possible_paths.append("./firebase-credentials.json")
            
            found_path = None
            for path in possible_paths:
                if path and os.path.exists(path):
                    found_path = path
                    break
            
            if found_path:
                logger.info(f"Initializing Firebase with credentials path: {found_path}")
                if not settings.firebase_private_key:
                    logger.error("FIREBASE_PRIVATE_KEY must be set when using firebase_credentials_path")
                    raise ValueError("FIREBASE_PRIVATE_KEY environment variable is required")
                cred_dict = _load_credentials_with_env_key(found_path, settings.firebase_private_key)
                cred = credentials.Certificate(cred_dict)
            else:
                logger.warning(f"Firebase credentials file not found. Tried: {', '.join([p for p in possible_paths if p])}")
        # Third, try individual environment variables (alternative approach)
        elif settings.firebase_project_id and settings.firebase_private_key and settings.firebase_client_email:
            logger.info(f"Initializing Firebase with environment variables for project: {settings.firebase_project_id}")
            # Construct credentials dict from environment variables
            cred_dict = {
                "type": "service_account",
                "project_id": settings.firebase_project_id,
                "private_key": settings.firebase_private_key.replace("\\n", "\n"),  # Handle escaped newlines
                "client_email": settings.firebase_client_email,
                "token_uri": "https://oauth2.googleapis.com/token",
            }
            cred = credentials.Certificate(cred_dict)
        # Check if some but not all env vars are set (for better error messages)
        elif settings.firebase_project_id or settings.firebase_private_key or settings.firebase_client_email:
            missing = []
            if not settings.firebase_project_id:
                missing.append("FIREBASE_PROJECT_ID")
            if not settings.firebase_private_key:
                missing.append("FIREBASE_PRIVATE_KEY")
            if not settings.firebase_client_email:
                missing.append("FIREBASE_CLIENT_EMAIL")
            logger.error(f"Firebase environment variables partially set. Missing: {', '.join(missing)}")
            logger.error("All three environment variables (FIREBASE_PROJECT_ID, FIREBASE_PRIVATE_KEY, FIREBASE_CLIENT_EMAIL) must be set to use environment variable authentication.")
        # Fourth, try to use default credentials (for GCP environments)
        elif settings.firebase_project_id:
            logger.info(f"Initializing Firebase with default credentials for project: {settings.firebase_project_id}")
            # Use default credentials (works in GCP environments)
            try:
                cred = credentials.ApplicationDefault()
                firebase_admin.initialize_app(cred, {
                    'projectId': settings.firebase_project_id,
                })
                _firebase_initialized = True
                logger.info("Firebase Admin SDK initialized successfully")
                return
            except Exception as e:
                logger.warning(f"Failed to initialize with default credentials: {e}")
                logger.warning("Falling back to manual credential configuration")
        else:
            logger.warning("Firebase credentials not found. Authentication will fail.")
            logger.warning("Set GOOGLE_APPLICATION_CREDENTIALS environment variable or firebase_credentials_path in settings")
            return
        
        # Initialize with credentials
        if cred:
            firebase_admin.initialize_app(cred)
            _firebase_initialized = True
            logger.info("Firebase Admin SDK initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize Firebase Admin SDK: {e}")
        logger.warning("Authentication will fail until Firebase is properly configured")
        raise


def verify_token(token: str) -> Dict:
    """
    Verify Firebase ID token and return decoded token.
    
    Args:
        token: Firebase ID token string
        
    Returns:
        Decoded token dictionary containing user information (uid, email, etc.)
        
    Raises:
        ValueError: If token is invalid, expired, or revoked, or if Firebase is not initialized
        FirebaseError: For other Firebase-related errors
    """
    if not _firebase_initialized:
        try:
            initialize_firebase()
        except Exception as e:
            logger.error(f"Failed to initialize Firebase during token verification: {e}")
            raise ValueError(f"Firebase not initialized: {str(e)}")
    
    # Double-check initialization succeeded
    if not _firebase_initialized:
        raise ValueError("Firebase Admin SDK is not initialized. Check Firebase credentials configuration.")
    
    try:
        # Verify the token
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except auth.InvalidIdTokenError as e:
        logger.warning(f"Invalid Firebase token: {e}")
        raise ValueError(f"Invalid token: {str(e)}")
    except auth.ExpiredIdTokenError as e:
        logger.warning(f"Expired Firebase token: {e}")
        raise ValueError(f"Token expired: {str(e)}")
    except auth.RevokedIdTokenError as e:
        logger.warning(f"Revoked Firebase token: {e}")
        raise ValueError(f"Token revoked: {str(e)}")
    except FirebaseError as e:
        logger.error(f"Firebase error verifying token: {e}")
        raise ValueError(f"Firebase error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error verifying token: {e}")
        raise ValueError(f"Token verification failed: {str(e)}")


def get_user_id_from_token(token: str) -> str:
    """
    Extract user ID (uid) from Firebase token.
    
    Args:
        token: Firebase ID token string
        
    Returns:
        User ID (uid) string
        
    Raises:
        ValueError: If token is invalid or user_id cannot be extracted
    """
    decoded_token = verify_token(token)
    user_id = decoded_token.get('uid')
    
    if not user_id:
        raise ValueError("Token does not contain user ID (uid)")
    
    return user_id

