#!/usr/bin/env python3
import requests
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import sys

# Determine the script's directory and construct absolute paths
script_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(script_dir, '.env')
token_file_path = os.path.join(script_dir, 'chainlink_token.json')

# Load environment variables from .env file using absolute path
load_dotenv(dotenv_path=dotenv_path)

# Settings
TOKEN_FILE = token_file_path # Use the absolute path
BASE_URL = os.getenv("BASE_URL")
if not BASE_URL:
    raise ValueError("BASE_URL not found in environment variables")
SESSION_URL = f"{BASE_URL}/sessions"

# Credentials
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD") # Keep password as is
if not EMAIL or not PASSWORD:
    raise ValueError("EMAIL or PASSWORD not found in environment variables")


def get_saved_token():
    """
    Checks if the saved token is still valid and returns it (cookie name and value).
    """
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            data = json.load(f)
        token = data.get("token")
        cookie_name = data.get("cookie_name")
        expires_str = data.get("expires")
        if token and cookie_name and expires_str:
            expiration = datetime.fromisoformat(expires_str)
            if datetime.now() < expiration:
                return cookie_name, token
    return None, None

def save_token(cookie_name, token, expiration):
    """
    Saves the token (cookie name, value, and expiration date) to a JSON file.
    """
    data = {
        "cookie_name": cookie_name,
        "token": token,
        "expires": expiration.isoformat()
    }
    with open(TOKEN_FILE, "w") as f:
        json.dump(data, f)
    print("Token saved with validity until", expiration.isoformat())

def login():
    """
    Performs login at the /sessions endpoint, extracts the session cookie, and saves it.
    If the cookie has no expiration, sets a default validity of 1 hour.
    """
    payload = {"email": EMAIL, "password": PASSWORD}
    print(f"Attempting login to {SESSION_URL}...")
    try:
        response = requests.post(SESSION_URL, json=payload, timeout=10)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        if len(response.cookies) > 0:
            cookie = list(response.cookies)[0]
            token = cookie.value
            cookie_name = cookie.name
            if cookie.expires:
                # Convert Unix timestamp to datetime object
                expiration = datetime.fromtimestamp(cookie.expires)
            else:
                # Default expiration if not provided
                expiration = datetime.now() + timedelta(hours=1)
            save_token(cookie_name, token, expiration)
            print("Login successful.")
            return cookie_name, token
        else:
            raise Exception("No session cookie received in the login response.")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Login network error: {e}")
    except Exception as e:
        # Catch other potential errors during login
        raise Exception(f"Login failed: {e}")


def list_job_ids(cookie_name, token):
    """
    Lists available jobs via GET /v2/jobs and returns a list of their IDs.
    """
    headers = {"Cookie": f"{cookie_name}={token}"}
    jobs_url = f"{BASE_URL}/v2/jobs"
    print(f"Fetching jobs from {jobs_url}...")
    try:
        response = requests.get(jobs_url, headers=headers, timeout=10)
        response.raise_for_status()
        jobs_data = response.json().get("data", [])
        job_ids = [job.get("id") for job in jobs_data if job.get("id")]
        print(f"Found {len(job_ids)} jobs.")
        return job_ids
    except requests.exceptions.RequestException as e:
        print(f"Error fetching jobs: {e}")
        return []
    except json.JSONDecodeError:
        print("Error decoding JSON response when fetching jobs.")
        return []


def delete_job(cookie_name, token, job_id):
    """
    Deletes the job by ID via DELETE /v2/jobs/{job_id}.
    Returns True if successful, False otherwise.
    """
    headers = {"Cookie": f"{cookie_name}={token}"}
    job_endpoint = f"{BASE_URL}/v2/jobs/{job_id}"
    print(f"Attempting to delete job {job_id} at {job_endpoint}...")
    try:
        response = requests.delete(job_endpoint, headers=headers, timeout=10)
        if response.status_code in [200, 204]:
            print(f"Job {job_id} deleted successfully.")
            return True
        else:
            print(f"Error deleting job {job_id}: {response.status_code} - {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Network error deleting job {job_id}: {e}")
        return False

def main():
    """
    Main function to authenticate, list all jobs, and delete them.
    """
    print("Starting job deletion process...")

    # 1. Authenticate
    cookie_name, token = get_saved_token()
    if token:
        print("Using saved token.")
    else:
        print("No valid saved token found. Logging in...")
        try:
            cookie_name, token = login()
        except Exception as e:
            print(f"Fatal: Login failed - {e}")
            sys.exit(1)

    if not token or not cookie_name:
        print("Fatal: Unable to obtain authentication token.")
        sys.exit(1)

    # 2. List Jobs
    job_ids = list_job_ids(cookie_name, token)
    if not job_ids:
        print("No jobs found or error listing jobs. Exiting.")
        sys.exit(0) # Exit normally if no jobs to delete

    # 3. Delete Jobs
    deleted_count = 0
    failed_count = 0
    print(f"\nStarting deletion of {len(job_ids)} jobs...")
    for job_id in job_ids:
        if delete_job(cookie_name, token, job_id):
            deleted_count += 1
        else:
            failed_count += 1

    print(f"\nDeletion process finished.")
    print(f"Successfully deleted: {deleted_count}")
    print(f"Failed to delete: {failed_count}")

    if failed_count > 0:
        sys.exit(1) # Exit with error code if any deletion failed
    else:
        sys.exit(0) # Exit successfully

if __name__ == "__main__":
    main()
