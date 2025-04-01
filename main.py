#!/usr/bin/env python3
import requests
import os
import json
import argparse
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

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
    response = requests.post(SESSION_URL, json=payload)
    if response.status_code == 200:
        if len(response.cookies) > 0:
            cookie = list(response.cookies)[0]  # Assume the first cookie is the session cookie (e.g., "clsession")
            token = cookie.value
            cookie_name = cookie.name
            if cookie.expires:
                expiration = datetime.fromtimestamp(cookie.expires)
            else:
                expiration = datetime.now() + timedelta(hours=1)
            save_token(cookie_name, token, expiration)
            return cookie_name, token
        else:
            raise Exception("No cookie was received in the response.")
    else:
        raise Exception(f"Login error: {response.status_code} - {response.text}")

def poll_run_status(job_id, job_run_id, cookie_name, token, timeout=60):
    """
    Polls by querying the GET /v2/jobs/{job_id}/runs endpoint and filters by job run ID.
    If the "status" field is empty but "finishedAt" exists, evaluates the "outputs" and "errors" fields
    to decide if the run completed successfully.
    Returns "completed", "errored", or None.
    """
    headers = {"Cookie": f"{cookie_name}={token}"}
    runs_url = f"{BASE_URL}/v2/jobs/{job_id}/runs"
    start_time = time.time()
    while True:
        response = requests.get(runs_url, headers=headers)
        if response.status_code == 200:
            runs = response.json().get("data", [])
            run = next((r for r in runs if str(r.get("id")) == str(job_run_id)), None)
            if run:
                attributes = run.get("attributes", {})
                status = attributes.get("status", "")
                fatal_errors = attributes.get("fatalErrors", []) # Renamed variable
                finished_at = attributes.get("finishedAt") # Renamed variable
                if fatal_errors and any(e is not None for e in fatal_errors):
                    print("Job run failed with fatalErrors:", fatal_errors)
                    return "errored"
                if status:
                    print("Current job run status:", status)
                    if status.lower() == "completed":
                        return "completed"
                    if status.lower() == "errored":
                        return "errored"
                elif finished_at:
                    outputs = attributes.get("outputs", [])
                    errors = attributes.get("errors", [])
                    print("Job run finished. Outputs:", outputs, "Errors:", errors)
                    if outputs and all(o is not None for o in outputs) and (not errors or all(e is None for e in errors)):
                        return "completed"
                    else:
                        return "errored"
                else:
                    print("Job run attributes (empty status):", attributes)
            else:
                print("Job run not found in the listing.")
        else:
            print(f"Error getting run listing: {response.status_code} - {response.text}")
            return None
        if time.time() - start_time > timeout:
            print("Timeout waiting for job run to finish.")
            return None
        time.sleep(2)

def run_job(job_id, cookie_name, token):
    """
    Executes the job via POST /v2/jobs/{job_id}/runs and polls to get the final status.
    """
    headers = {
        "Cookie": f"{cookie_name}={token}",
        "Content-Type": "application/json"
    }
    run_url = f"{BASE_URL}/v2/jobs/{job_id}/runs"
    response = requests.post(run_url, headers=headers, json={})
    if response.status_code in [200, 201]:
        result_json = response.json()
        job_run_id = result_json.get("data", {}).get("id")
        if not job_run_id:
            print("Could not get job run ID from the response.")
            return False
        #print(f"Job {job_id} executed with run ID: {job_run_id}. Waiting for completion...")
        status = poll_run_status(job_id, job_run_id, cookie_name, token)
        if status == "completed":            
            print(f"Job {job_id} executed successfully!")
            return True
        elif status == "errored":            
            print(f"Job {job_id} failed execution.")
            return False
        else:            
            print("Could not determine the final status of the job run.")
            return False
    else:
        print(f"Error executing job {job_id}: {response.status_code} - {response.text}")
        return False

def list_jobs(cookie_name, token):
    """
    Lists available jobs via GET /v2/jobs.
    """
    headers = {"Cookie": f"{cookie_name}={token}"}
    jobs_url = f"{BASE_URL}/v2/jobs"
    response = requests.get(jobs_url, headers=headers)
    if response.status_code == 200:
        print("Jobs obtained successfully:")
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"Error getting jobs: {response.status_code} - {response.text}")

def create_job(cookie_name, token):
    """
    Creates a new job via POST /v2/jobs using the provided job spec.
    The job spec is sent in the "toml" key as a TOML string.
    Returns the ID of the created job if the operation is successful.
    """
    headers = {"Cookie": f"{cookie_name}={token}", "Content-Type": "application/json"}
    job_endpoint = f"{BASE_URL}/v2/jobs"

    # Construct the absolute path to config.toml relative to this script's location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.toml")

    # Read the TOML spec from config.toml using the absolute path
    try:
        with open(config_path, "r") as f:
            toml_spec = f.read()
    except FileNotFoundError:
        print(f"Error: {config_path} not found.")
        return None
    except Exception as e:
        print(f"Error reading config.toml: {e}")
        return None

    payload = {"toml": toml_spec}
    response = requests.post(job_endpoint, headers=headers, json=payload)
    if response.status_code in [200, 201]:
        data = response.json().get("data", {})
        job_id = data.get("id")
        #print("Job created successfully!")
        #print(json.dumps(response.json(), indent=2))
        if job_id:
            #print("Created job ID:", job_id)
            return job_id
        else:
            print("Could not extract the created job ID.")
    else:
        print(f"Error creating job: {response.status_code} - {response.text}")
        return None

def delete_job(cookie_name, token, job_id):
    """
    Deletes the job by ID via DELETE /v2/jobs/{job_id}.
    """
    headers = {"Cookie": f"{cookie_name}={token}"}
    job_endpoint = f"{BASE_URL}/v2/jobs/{job_id}"
    response = requests.delete(job_endpoint, headers=headers)
    '''if response.status_code in [200, 204]:
        print("Job deleted successfully!")
    else:
        print(f"Error deleting job: {response.status_code} - {response.text}")'''

def main(STATUS):
    '''parser = argparse.ArgumentParser(description="Manage token, run, create, and delete Chainlink jobs")
    parser.add_argument("--job", help="ID of the job to run")
    parser.add_argument("--create", action="store_true", help="Create a new job with the fixed job spec")
    parser.add_argument("--delete", help="Delete the job by ID")
    args = parser.parse_args()'''

    # Check connection to BASE_URL
    #print(f"Attempting to connect to BASE_URL: {BASE_URL}...")
    try:
        # Use a timeout to avoid hanging indefinitely
        response = requests.get(BASE_URL, timeout=5)
        # Check for a successful status code (e.g., 2xx)
        response.raise_for_status()
        #print("Successfully connected to BASE_URL.")
    except requests.exceptions.RequestException as e:
        pass
        #print(f"Error connecting to BASE_URL: {e}")
        # Optionally exit if connection fails, as other operations will likely fail too
        # import sys
        # sys.exit(1)
        # For now, just print the error and continue to attempt login/token check

    cookie_name, token = get_saved_token()
    if token:
        pass
        #print("Valid token found.") # Don't print the token itself for security
    else:
        #print("Token not found or expired. Performing login...")
        try:
            cookie_name, token = login()
            #print("New token obtained successfully.") # Don't print the token
        except Exception as e:
            print(f"Login failed: {e}")
            # Exit if login fails
            import sys
            sys.exit(1)


    # Proceed only if we have a valid token
    if not token or not cookie_name:
        print("Unable to proceed without a valid token. Exiting.")
        import sys
        sys.exit(1)
    
    try:
        job_id = create_job(cookie_name, token)
        if job_id is not None:
            STATUS=run_job(job_id, cookie_name, token)
        else:
            print("Failed to create job. Exiting.")
            STATUS = True
    
    finally:
        if job_id is not None:
            delete_job(cookie_name, token, job_id)    

if __name__ == "__main__":
    STATUS = False
    main(STATUS)
    print("Exiting with status:", STATUS)
    if STATUS:
        exit(0)
    else:
        exit(1)
    # exit(0) if successful, exit(1) if failed