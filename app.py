from flask import Flask, render_template, request
import requests
from collections import defaultdict
from datetime import datetime

app = Flask(__name__)

# Constants
API_TOKEN = "AioAuth NWFiNDUyZTYtMGVlZS0zNDgxLTg5ZTUtNjY2N2M3ZTEzN2YxLjcyNmJjOTNmLTUzM2EtNDk3Ni1hMGY3LTkyZTU5ZDcyMWY0NA=="
BASE_URL = "https://tcms.aiojiraapps.com/aio-tcms/api/v1/project/TEG/testcycle/TEG-CY-55/testcase"
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
    "712020:b93551fd-3c96-4f9d-95b7-a5ba3652db73": "Vignesh",
    "61f76776f51e85007082803f": "Vishnu"
}

def to_millis(date_str):
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return int(dt.timestamp() * 1000)
    except Exception:
        return None

def fetch_leaderboard(start_date=None, end_date=None):
    start_millis = to_millis(start_date) if start_date else float("-inf")
    end_millis = to_millis(end_date) if end_date else float("inf")

    start_at = 0
    limit = 100
    has_more = True
    total_automated = 0
    pending_automation = 0
    automated_in_period = 0
    automation_leaderboard = defaultdict(int)

    while has_more:
        url = f"{BASE_URL}?startAt={start_at}&limit={limit}"
        response = requests.get(url, headers=HEADERS)

        if response.status_code != 200:
            break

        try:
            response_data = response.json()
        except Exception:
            break

        test_cases = response_data.get("items", [])
        if not test_cases:
            break

        for item in test_cases:
            test_case = item.get("testCase", {})
            automation_status_info = test_case.get("automationStatus")
            automation_status = automation_status_info.get("name") if automation_status_info else None
            automation_owner_id = test_case.get("automationOwnerID")
            updated_date = test_case.get("updatedDate")

            if automation_status == "Automated":
                total_automated += 1
                if updated_date and start_millis <= updated_date <= end_millis:
                    automated_in_period += 1
                    if automation_owner_id:
                        owner_name = owner_id_to_name.get(automation_owner_id, f"Unknown ({automation_owner_id})")
                        automation_leaderboard[owner_name] += 1
            else:
                pending_automation += 1

        if response_data.get("isLast", True):
            has_more = False
        else:
            start_at += limit

    sorted_leaderboard = sorted(automation_leaderboard.items(), key=lambda x: x[1], reverse=True)
    return sorted_leaderboard, total_automated, pending_automation, automated_in_period

@app.route("/", methods=["GET", "POST"])
def leaderboard():
    leaderboard = []
    total_automated = 0
    pending_automation = 0
    automated_in_period = 0
    start_date = end_date = ""

    if request.method == "POST":
        start_date = request.form.get("start_date", "").strip()
        end_date = request.form.get("end_date", "").strip()
        leaderboard, total_automated, pending_automation, automated_in_period = fetch_leaderboard(start_date or None, end_date or None)

    return render_template("leaderboard.html",
                         leaderboard=leaderboard,
                         total_automated=total_automated,
                         pending_automation=pending_automation,
                         automated_in_period=automated_in_period,
                         start_date=start_date,
                         end_date=end_date)

if __name__ == "__main__":
    app.run(debug=True)
