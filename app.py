from flask import Flask, render_template, request
import requests
from collections import defaultdict
from datetime import datetime
import os
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Constants
API_TOKEN = os.getenv('API_TOKEN')
BASE_URL = os.getenv('BASE_URL', "https://tcms.aiojiraapps.com/aio-tcms/api/v1/project/TEG/testcycle/TEG-CY-55/testcase")

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

        while has_more:
            url = f"{BASE_URL}?startAt={start_at}&limit={limit}"
            try:
                response = requests.get(url, headers=HEADERS, timeout=10)
                response.raise_for_status()
            except requests.RequestException as e:
                logger.error(f"API request failed: {str(e)}")
                return [], 0

            try:
                response_data = response.json()
            except Exception as e:
                logger.error(f"Failed to parse JSON response: {str(e)}")
                return [], 0

            test_cases = response_data.get("items", [])
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

        sorted_leaderboard = sorted(automation_leaderboard.items(), key=lambda x: x[1], reverse=True)
        return sorted_leaderboard, test_case_count
    except Exception as e:
        logger.error(f"Error in fetch_leaderboard: {str(e)}")
        return [], 0

@app.route("/", methods=["GET", "POST"])
def leaderboard():
    try:
        leaderboard = []
        test_case_count = 0
        start_date = end_date = ""
        error_message = None

        if request.method == "POST":
            start_date = request.form.get("start_date", "").strip()
            end_date = request.form.get("end_date", "").strip()

            # Validate dates
            try:
                if start_date:
                    datetime.strptime(start_date, "%Y-%m-%d")
                if end_date:
                    datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                error_message = "Invalid date format. Please use YYYY-MM-DD format."
                return render_template("leaderboard.html",
                                    leaderboard=[],
                                    test_case_count=0,
                                    start_date=start_date,
                                    end_date=end_date,
                                    error_message=error_message)

            leaderboard, test_case_count = fetch_leaderboard(start_date or None, end_date or None)

        return render_template("leaderboard.html",
                            leaderboard=leaderboard,
                            test_case_count=test_case_count,
                            start_date=start_date,
                            end_date=end_date,
                            error_message=error_message)
    except Exception as e:
        logger.error(f"Error in leaderboard route: {str(e)}")
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

if __name__ == "__main__":
    # Only enable debug mode in development
    debug_mode = os.getenv('FLASK_ENV') == 'development'
    app.run(debug=debug_mode)
