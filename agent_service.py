import requests
import subprocess
import json
import os
from typing import List, Dict, Tuple, Optional

class AgentService:
    """
    Service for communicating with the Papers RAG agent.
    Based on the provided sample code.
    """
    
    def __init__(self):
        """
        Initialize the agent service with configuration.
        """
        self.cloud_run_url = "https://papers-rag-1-master-1031636165462.us-central1.run.app"
        self.app_name = "papers-rag-agent"
    
    def get_gcloud_auth_token(self) -> str:
        """
        Uses the gcloud CLI to generate an identity token for authenticating with Cloud Run.
        """
        try:
            token = subprocess.check_output(
                ["gcloud", "auth", "print-identity-token"],
                text=True
            ).strip()
            return token
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print("Error: Failed to get gcloud auth token.")
            print("Please ensure gcloud CLI is installed and authenticated (`gcloud auth login`).")
            raise Exception("gcloud command failed") from e

    def get_or_create_session(
        self,
        auth_token: str,
        app_name: str,
        user_id: str,
        new_session_id_if_needed: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Checks if an existing session exists for a specific user and returns it.
        If no sessions exist for that user, it creates a new one.

        Args:
            auth_token: The gcloud authentication token.
            app_name: The name of the agent application.
            user_id: The identifier for the user to check sessions for.
            new_session_id_if_needed: The ID to use ONLY if a new session needs to be created.

        Returns:
            Tuple of (success: bool, session_id: str | None)
        """
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Step 1: Request the list of sessions for the SPECIFIC user_id.
        list_sessions_url = f"{self.cloud_run_url}/apps/{app_name}/users/{user_id}/sessions"
        print(f"Checking for existing sessions for user '{user_id}'...")

        try:
            response = requests.get(list_sessions_url, headers=headers, timeout=60)
            response.raise_for_status()
            sessions_list = response.json()
            
            # Step 2: If the returned list is not empty, USE the first session.
            if sessions_list:
                existing_session_id = sessions_list[0]['id']
                print(f"Success: Found existing session '{existing_session_id}' for this user. Reusing it.")
                return True, existing_session_id

        except requests.exceptions.RequestException as e:
            print(f"An error occurred while checking for sessions: {e}")
            return False, None

        # Step 3: If the list was empty, CREATE a new session for that user.
        print(f"No existing sessions found for user '{user_id}'. Creating a new one.")
        create_session_url = f"{self.cloud_run_url}/apps/{app_name}/users/{user_id}/sessions/{new_session_id_if_needed}"
        
        headers["Content-Type"] = "application/json"
        payload = {"state": {}}

        try:
            response = requests.post(create_session_url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            print(f"Success: Created new session '{new_session_id_if_needed}'.")
            return True, new_session_id_if_needed
            
        except requests.exceptions.RequestException as e:
            print(f"An error occurred while creating a new session: {e}")
            return False, None

    def run_agent_sse(
        self,
        auth_token: str,
        app_name: str,
        message: str,
        user_id: str,
        session_id: str,
        use_streaming: bool = False
    ) -> List[Dict]:
        """
        Sends a prompt to the agent's /run_sse endpoint using an existing session.
        """
        endpoint_url = f"{self.cloud_run_url}/run_sse"
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        if use_streaming:
            headers["Accept"] = "text/event-stream"

        payload = {
            "app_name": app_name,
            "user_id": user_id,
            "session_id": session_id,
            "new_message": {"role": "user", "parts": [{"text": message}]},
            "streaming": use_streaming
        }

        print(f"\nSending request to {endpoint_url}...")
        print("--- Agent Response Stream ---")
        all_events = []

        try:
            with requests.post(endpoint_url, headers=headers, json=payload, stream=use_streaming, timeout=300) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line and line.decode('utf-8').startswith('data: '):
                        json_str = line.decode('utf-8')[len('data: '):]
                        try:
                            event = json.loads(json_str)
                            all_events.append(event)
                        except json.JSONDecodeError:
                            print(f"Warning: Could not decode line: {json_str}")

        except requests.exceptions.HTTPError as e:
            print(f"\nHTTP Error running agent: {e.response.status_code} {e.response.reason}")
            print(f"Response Body: {e.response.text}")
            raise e
        except requests.exceptions.RequestException as e:
            print(f"\nA request error occurred while running agent: {e}")
            raise e

        return all_events

    async def send_message(self, user_id: str, session_id: str, message: str) -> List[Dict]:
        """
        Send a message to the agent and return the events.
        
        Args:
            user_id: The user identifier (email)
            session_id: The session identifier
            message: The message to send to the agent
            
        Returns:
            List of events from the agent response
        """
        try:
            # Step 1: Get authentication token
            token = self.get_gcloud_auth_token()
            
            # Step 2: Get or create session
            session_created, actual_session_id = self.get_or_create_session(
                auth_token=token,
                app_name=self.app_name,
                user_id=user_id,
                new_session_id_if_needed=session_id
            )
            
            if not session_created:
                raise Exception("Failed to create or retrieve session")
            
            # Step 3: Send message to agent
            events = self.run_agent_sse(
                auth_token=token,
                app_name=self.app_name,
                message=message,
                user_id=user_id,
                session_id=actual_session_id
            )
            
            return events, actual_session_id
            
        except Exception as e:
            print(f"Error in send_message: {e}")
            raise e

    def delete_session(
        self,
        auth_token: str,
        app_name: str,
        user_id: str,
        session_id: str
    ) -> bool:
        """
        Deletes a specific session for a given user.

        Args:
            auth_token: The gcloud authentication token.
            app_name: The name of the agent application.
            user_id: The identifier for the user who owns the session.
            session_id: The specific session ID to delete.

        Returns:
            True if the session was deleted successfully, False otherwise.
        """
        headers = {"Authorization": f"Bearer {auth_token}"}

        # Construct the specific URL for the session to be deleted, as per the docs.
        delete_url = f"{self.cloud_run_url}/apps/{app_name}/users/{user_id}/sessions/{session_id}"
        print(f"Attempting to delete session: {delete_url}")

        try:
            # Make the DELETE request.
            response = requests.delete(delete_url, headers=headers, timeout=60)

            # This will raise an HTTPError for bad status codes (like 4xx or 5xx).
            # A successful 204 No Content status from the server will NOT raise an error.
            response.raise_for_status()

            print(f"Success: Session '{session_id}' was deleted (Status Code: {response.status_code}).")
            return True

        except requests.exceptions.HTTPError as e:
            # This block catches errors like 404 (Not Found) or 401 (Unauthorized).
            print(f"HTTP Error: Failed to delete session. Status code: {e.response.status_code}")
            print(f"Response Body: {e.response.text}")
            return False
        except requests.exceptions.RequestException as e:
            # This block catches other network-related errors (e.g., connection timeout).
            print(f"An error occurred while deleting the session: {e}")
            return False

    async def delete_user_session(self, user_id: str, session_id: str) -> bool:
        """
        Delete a session for a specific user.

        Args:
            user_id: The user identifier (email)
            session_id: The session identifier to delete

        Returns:
            True if session was deleted successfully, False otherwise
        """
        try:
            # Step 1: Get authentication token
            token = self.get_gcloud_auth_token()

            # Step 2: Delete the session
            success = self.delete_session(
                auth_token=token,
                app_name=self.app_name,
                user_id=user_id,
                session_id=session_id
            )

            return success

        except Exception as e:
            print(f"Error in delete_user_session: {e}")
            return False