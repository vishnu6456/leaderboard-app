from flask import Flask, render_template, request
import requests
from collections import defaultdict
from datetime import datetime

app = Flask(__name__)

# Constants
API_TOKEN = "AioAuth NWFiNDUyZTYtMGVlZS0zNDgxLTg5ZTUtNjY2N2M3ZTEzN2YxLjcyNmJjOTNmLTUzM2EtNDk3Ni1hMGY3LTkyZTU5ZDcyMWY0NA=="
BASE_URL = "https://tcms.aiojiraapps.com/aio-tcms/api/v1/project/TEG/testcycle/TEG-CY-161/testcase"
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
    "61f76776f51e85007082803f": "Vishnu",
    "712020:c5ac7c55-2162-41a0-94fc-1f881b748f94": "Mantina",
    "712020:80c70e4f-43c9-4fb4-af99-9fbc8970e39f": "Deeksha",
    "712020:bd70b0da-719f-4c31-9099-a73d1f4322a8": "Santhosh",
    "712020:befbc7e4-66bd-4e3a-b3f9-1a27c9b4bbbf": "Akash",

}

def to_millis(date_str):
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return int(dt.timestamp() * 1000)
    except Exception:
        return None

def get_aes_value(test_case):
    """Extract AES value from custom fields"""
    custom_fields = test_case.get("customFields", [])
    
    for field in custom_fields:
        field_name = field.get("name", "")
        field_id = field.get("ID", "")
        
        # Match by field name, field ID, or partial name match
        if field_name == "Automation Effort Score (AES)" or field_id == 14 or "AES" in field_name:
            value_obj = field.get("value", {})
            if isinstance(value_obj, dict):
                aes_str = value_obj.get("value", "0")
            else:
                aes_str = str(value_obj) if value_obj else "0"
            try:
                return int(aes_str)
            except (ValueError, TypeError):
                return 0
    
    return 0

def fetch_leaderboard(start_date=None, end_date=None):
    start_millis = to_millis(start_date) if start_date else float("-inf")
    end_millis = to_millis(end_date) if end_date else float("inf")

    start_at = 0
    limit = 100
    has_more = True
    total_automated = 0
    pending_automation = 0
    automated_in_period = 0
    in_progress_in_period = 0
    
    # Automated tracking
    automation_leaderboard = defaultdict(int)
    aes_automated_leaderboard = defaultdict(int)
    
    # In Progress tracking
    in_progress_leaderboard = defaultdict(int)
    aes_in_progress_leaderboard = defaultdict(int)

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
                        # Add AES score for automated test cases
                        aes_value = get_aes_value(test_case)
                        aes_automated_leaderboard[owner_name] += aes_value
                        
            elif automation_status == "In Progress":
                # Track In Progress test cases
                if updated_date and start_millis <= updated_date <= end_millis:
                    in_progress_in_period += 1
                    if automation_owner_id:
                        owner_name = owner_id_to_name.get(automation_owner_id, f"Unknown ({automation_owner_id})")
                        in_progress_leaderboard[owner_name] += 1
                        # Add AES score for in-progress test cases
                        aes_value = get_aes_value(test_case)
                        aes_in_progress_leaderboard[owner_name] += aes_value
            else:
                pending_automation += 1

        if response_data.get("isLast", True):
            has_more = False
        else:
            start_at += limit

    # Combine automated count and AES scores
    automated_combined = []
    for owner_name in automation_leaderboard.keys():
        automated_combined.append({
            'name': owner_name,
            'count': automation_leaderboard[owner_name],
            'aes': aes_automated_leaderboard[owner_name]
        })
    automated_combined.sort(key=lambda x: x['count'], reverse=True)
    
    # Combine in-progress count and AES scores
    in_progress_combined = []
    for owner_name in in_progress_leaderboard.keys():
        in_progress_combined.append({
            'name': owner_name,
            'count': in_progress_leaderboard[owner_name],
            'aes': aes_in_progress_leaderboard[owner_name]
        })
    in_progress_combined.sort(key=lambda x: x['count'], reverse=True)
    
    # Print summary for debugging
    print("\n=== AUTOMATED LEADERBOARD ===")
    for entry in automated_combined:
        print(f"{entry['name']}: {entry['count']} tests, AES: {entry['aes']}")
    print(f"Total Automated in Period: {automated_in_period}")
    
    print("\n=== IN PROGRESS LEADERBOARD ===")
    for entry in in_progress_combined:
        print(f"{entry['name']}: {entry['count']} tests, AES: {entry['aes']}")
    print(f"Total In Progress in Period: {in_progress_in_period}")
    print("=" * 30 + "\n")
    
    return automated_combined, in_progress_combined, total_automated, pending_automation, automated_in_period, in_progress_in_period

@app.route("/", methods=["GET", "POST"])
def leaderboard():
    automated_leaderboard = []
    in_progress_leaderboard = []
    total_automated = 0
    pending_automation = 0
    automated_in_period = 0
    in_progress_in_period = 0
    start_date = end_date = ""

    if request.method == "POST":
        start_date = request.form.get("start_date", "").strip()
        end_date = request.form.get("end_date", "").strip()
        
        automated_leaderboard, in_progress_leaderboard, total_automated, pending_automation, automated_in_period, in_progress_in_period = fetch_leaderboard(start_date or None, end_date or None)

    return render_template("leaderboard.html",
                         automated_leaderboard=automated_leaderboard,
                         in_progress_leaderboard=in_progress_leaderboard,
                         total_automated=total_automated,
                         pending_automation=pending_automation,
                         automated_in_period=automated_in_period,
                         in_progress_in_period=in_progress_in_period,
                         start_date=start_date,
                         end_date=end_date)

if __name__ == "__main__":
    app.run(debug=True)
