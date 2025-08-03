from flask import Flask, render_template, request
import requests
from collections import defaultdict
from datetime import datetime
import os
import logging
import sys
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Constants
API_TOKEN = os.getenv('API_TOKEN')
BASE_URL = os.getenv('BASE_URL', "https://tcms.aiojiraapps.com/aio-tcms/api/v1/project/TEG/testcycle/TEG-CY-55/testcase")

# Log startup configuration
logger.info(f"Starting application with BASE_URL: {BASE_URL}")
logger.info(f"API_TOKEN is {'set' if API_TOKEN else 'not set'}")
logger.info(f"Environment: {os.getenv('FLASK_ENV', 'not set')}")
logger.info(f"Port: {os.getenv('PORT', 'not set')}")

if not API_TOKEN:
    logger.error("API_TOKEN environment variable is not set")
    raise ValueError("API_TOKEN environment variable is not set")

HEADERS = {
    "accept": "application/json;charset=utf-8",
    "Authorization": API_TOKEN
}

# Owner ID to Name Mapping
owner_id_to_name = {
    "712020:89f10278-b7f4-4811-8de9-94344d66600b": "Eswar",
    "712020:79790c87-248d-46ba-9d79-bfa17e10132d": "Mahi",
    "712020:ba53b74f-3aa8-4f41-be66-ed7093ac03b1": "Sneha",
    "712020:86eb614f-7084-492b-ab3b-53196fea7c6b": "Shameer",
    "712020:c496c155-9d04-4860-92d1-e274eaa32f48": "Suchitra",
    "712020:b93551fd-3c96-4f9d-95b7-a5ba3652db73": "Vignesh"
}

def to_millis(date_str):
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return int(dt.timestamp() * 1000)
    except Exception as e:
        logger.error(f"Error converting date {date_str}: {str(e)}")
        return None

def fetch_leaderboard(start_date=None, end_date=None):
    try:
        start_millis = to_millis(start_date) if start_date else float("-inf")
        end_millis = to_millis(end_date) if end_date else float("inf")

        start_at = 0
        limit = 100
        has_more = True
        test_case_count = 0
        automation_leaderboard = defaultdict(int)

        # Create session with specific configurations
        session = requests.Session()
        
        # Configure session with retry settings
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        # Basic headers
        headers = {
            "Authorization": API_TOKEN,
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        while has_more:
            try:
                url = f"{BASE_URL}?startAt={start_at}&limit={limit}"
                logger.info(f"Making request to: {url}")
                
                # Make request with increased timeout
                response = session.get(
                    url,
                    headers=headers,
                    timeout=30,  # 30 seconds timeout
                    verify=True
                )
                
                logger.info(f"Response Status: {response.status_code}")
                
                if response.status_code == 403:
                    logger.error("Authentication failed - check API token")
                    return [], 0

                response.raise_for_status()
                response_data = response.json()
                
                test_cases = response_data.get("items", [])
                logger.info(f"Retrieved {len(test_cases)} test cases")
                
                if not test_cases:
                    break

                for item in test_cases:
                    test_case = item.get("testCase", {})
                    automation_status_info = test_case.get("automationStatus")
                    automation_status = automation_status_info.get("name") if automation_status_info else None
                    automation_owner_id = test_case.get("automationOwnerID")
                    updated_date = test_case.get("updatedDate")

                    if updated_date is None:
                        continue

                    if not (start_millis <= updated_date <= end_millis):
                        continue

                    if automation_status == "Automated" and automation_owner_id:
                        owner_name = owner_id_to_name.get(automation_owner_id, f"Unknown ({automation_owner_id})")
                        automation_leaderboard[owner_name] += 1

                    test_case_count += 1

                if response_data.get("isLast", True):
                    has_more = False
                else:
                    start_at += limit

            except requests.exceptions.Timeout:
                logger.error("Request timed out")
                return [], 0
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error: {str(e)}")
                if hasattr(e, 'response'):
                    logger.error(f"Response content: {e.response.content if e.response else 'No response'}")
                return [], 0
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                logger.exception("Full traceback:")
                return [], 0

        logger.info(f"Successfully processed {test_case_count} test cases")
        sorted_leaderboard = sorted(automation_leaderboard.items(), key=lambda x: x[1], reverse=True)
        return sorted_leaderboard, test_case_count

    except Exception as e:
        logger.error(f"Error in fetch_leaderboard: {str(e)}")
        logger.exception("Full traceback:")
        return [], 0

@app.route("/", methods=["GET", "POST"])
def leaderboard():
    try:
        leaderboard = []
        test_case_count = 0
        start_date = end_date = ""
        error_message = None

        if request.method == "POST":
            try:
                start_date = request.form.get("start_date", "").strip()
                end_date = request.form.get("end_date", "").strip()

                # Validate dates
                if start_date and end_date:
                    try:
                        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                        
                        if end_dt < start_dt:
                            error_message = "End date must be after start date"
                            return render_template("leaderboard.html",
                                                leaderboard=[],
                                                test_case_count=0,
                                                start_date=start_date,
                                                end_date=end_date,
                                                error_message=error_message)
                    except ValueError:
                        error_message = "Invalid date format. Please use YYYY-MM-DD format."
                        return render_template("leaderboard.html",
                                            leaderboard=[],
                                            test_case_count=0,
                                            start_date=start_date,
                                            end_date=end_date,
                                            error_message=error_message)

                logger.info(f"Fetching leaderboard for date range: {start_date} to {end_date}")
                leaderboard, test_case_count = fetch_leaderboard(start_date or None, end_date or None)
                
                if not leaderboard and test_case_count == 0:
                    error_message = "No data found for the selected date range. Please try different dates or check the API connection."
                
                logger.info(f"Retrieved leaderboard with {len(leaderboard)} entries and {test_case_count} test cases")

            except Exception as e:
                logger.error(f"Error processing request: {str(e)}")
                error_message = "An error occurred while processing your request. Please try again."
                return render_template("leaderboard.html",
                                    leaderboard=[],
                                    test_case_count=0,
                                    start_date=start_date,
                                    end_date=end_date,
                                    error_message=error_message)

        return render_template("leaderboard.html",
                            leaderboard=leaderboard,
                            test_case_count=test_case_count,
                            start_date=start_date,
                            end_date=end_date,
                            error_message=error_message)
                            
    except Exception as e:
        logger.error(f"Error in leaderboard route: {str(e)}")
        logger.exception("Full traceback:")
        return render_template("leaderboard.html",
                            leaderboard=[],
                            test_case_count=0,
                            start_date="",
                            end_date="",
                            error_message="An unexpected error occurred. Please try again later.")

@app.errorhandler(404)
def not_found_error(error):
    return render_template('leaderboard.html', error_message="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('leaderboard.html', error_message="Internal server error. Please try again later."), 500

@app.route("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.route("/debug")
def debug_info():
    if os.getenv('FLASK_ENV') == 'development':
        return {
            "env_vars": dict(os.environ),
            "python_version": sys.version,
            "working_directory": os.getcwd(),
        }
    return {"status": "Debug endpoint only available in development"}

if __name__ == "__main__":
    port = int(os.getenv('PORT', 8080))
    logger.info(f"Starting server on port {port}")
    app.run(host='0.0.0.0', port=port)
