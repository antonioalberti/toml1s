# Chainlink Job Management Script

This Python script interacts with a Chainlink node's API to manage jobs. It allows you to:
- Log in to the node and save the session token.
- List available jobs.
- Create a new job using a specification defined in `config.toml`.
- Run an existing job by its ID.
- Delete a job by its ID.
- Poll the status of a running job.

## Setup

1.  **Clone the repository (if applicable):**
    ```bash
    git clone <your-repo-url>
    cd <repo-directory>
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    Create a file named `.env` in the root directory with the following content, replacing the placeholder values with your actual Chainlink node details:
    ```dotenv
    EMAIL="your_node_email@example.com"
    PASSWORD="your_node_password"
    BASE_URL="http://your_node_ip:port"
    ```
    *Note: This `.env` file is included in `.gitignore` to prevent accidental commits of sensitive information.*

5.  **Define Job Specification (for creating jobs):**
    Ensure you have a `config.toml` file in the root directory containing the TOML specification for the job you want to create using the `--create` flag. An example structure is provided in the repository.

## Usage

Run the script using `python main.py` with optional arguments:

-   **List jobs (default action):**
    ```bash
    python main.py
    ```
    If no arguments are provided, the script will log in (if necessary) and list all available jobs on the node.

-   **Run a specific job:**
    ```bash
    python main.py --job <JOB_ID>
    ```
    Replace `<JOB_ID>` with the ID of the job you want to execute. The script will trigger the job run and poll its status until completion or timeout.

-   **Create a new job:**
    ```bash
    python main.py --create
    ```
    This command reads the job specification from `config.toml` and attempts to create a new job on the node.

-   **Delete a job:**
    ```bash
    python main.py --delete <JOB_ID>
    ```
    Replace `<JOB_ID>` with the ID of the job you want to delete.

### Token Management
The script automatically handles login and session token management. It saves a valid token to `chainlink_token.json` and reuses it until it expires. If the token is invalid or missing, it performs a new login.

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues.

## License

This project is licensed under the MIT License.

**MIT License**

Copyright (c) Ariel Dalla Costa and Antonio Alberti

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
