from google.cloud import firestore
from google.cloud.firestore_v1 import AsyncClient
import os
from typing import Optional

class FirestoreDB:
    """
    Firestore database operations for the RAG application.
    """
    
    def __init__(self):
        """
        Initialize Firestore client.
        """
        # Initialize Firestore client
        # In Google Cloud Run, credentials are automatically provided
        self.db = firestore.AsyncClient()
        self.collection_name = "rag_users"
    
    async def user_exists(self, user_email: str) -> bool:
        """
        Check if a user exists in the rag_users collection.

        Args:
            user_email: The email of the user to check

        Returns:
            True if user exists, False otherwise
        """
        try:
            doc_ref = self.db.collection(self.collection_name).document(user_email)
            doc = await doc_ref.get()
            return doc.exists
        except Exception as e:
            print(f"Error checking if user exists: {e}")
            return False
    
    async def is_user_admin(self, user_email: str) -> bool:
        """
        Check if a user has admin privileges.

        Args:
            user_email: The email of the user to check

        Returns:
            True if user is admin, False otherwise
        """
        try:
            doc_ref = self.db.collection(self.collection_name).document(user_email)
            doc = await doc_ref.get()

            if doc.exists:
                user_data = doc.to_dict()
                return user_data.get("is_admin", False)
            return False
        except Exception as e:
            print(f"Error checking if user is admin: {e}")
            return False
    
    async def add_user(self, user_email: str, is_admin: bool = False) -> bool:
        """
        Add a new user to the rag_users collection.

        Args:
            user_email: The email of the user to add
            is_admin: Whether the user should have admin privileges

        Returns:
            True if user was added successfully, False otherwise
        """
        try:
            doc_ref = self.db.collection(self.collection_name).document(user_email)

            # Check if user already exists
            doc = await doc_ref.get()
            if doc.exists:
                return False  # User already exists

            # Add the new user
            user_data = {
                "user_email": user_email,
                "is_admin": is_admin,
                "created_at": firestore.SERVER_TIMESTAMP
            }

            await doc_ref.set(user_data)
            return True
        except Exception as e:
            print(f"Error adding user: {e}")
            return False
    
    async def get_user(self, user_email: str) -> Optional[dict]:
        """
        Get user data from the rag_users collection.

        Args:
            user_email: The email of the user to retrieve

        Returns:
            User data dict if found, None otherwise
        """
        try:
            doc_ref = self.db.collection(self.collection_name).document(user_email)
            doc = await doc_ref.get()

            if doc.exists:
                return doc.to_dict()
            return None
        except Exception as e:
            print(f"Error getting user: {e}")
            return None