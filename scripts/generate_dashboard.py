import json
import os
from datetime import datetime, timedelta
import pytz

def parse_logs(user_prefix):
    log_path = f"logs/{user_prefix}.log"
    status = "Pending"
    details = ""
    timestamp = datetime.now(pytz.utc).isoformat()
    
    if os.path.exists(log_path):
        with open(log_path, 'r') as f:
            lines = f.readlines()
            if lines:
                last_line = lines[-1]
                timestamp_str = last_line.split(' - ')[0]
                timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f').isoformat()
                
                if "Booking failed" in last_line:
                    status = "Failed"
                    details = last_line.split(' - ')[-1].strip()
                elif "Booking finalized successfully" in last_line:
                    status = "Success"
                else:
                    status = "Pending"

    return {
        "user": user_prefix,
        "status": status,
        "timestamp": timestamp,
        "details": details
    }

def generate_status():
    users = []
    # Get all user log files
    for filename in os.listdir("logs"):
        if filename.endswith(".log"):
            user_prefix = filename.split('.')[0]
            users.append(user_prefix)
    
    # Remove duplicates
    users = list(set(users))
    
    status = [parse_logs(user) for user in users]
    
    # Create dashboard directory if not exists
    if not os.path.exists("dashboard"):
        os.makedirs("dashboard")
    
    with open("dashboard/status.json", "w") as f:
        json.dump(status, f, indent=2)

if __name__ == "__main__":
    generate_status()