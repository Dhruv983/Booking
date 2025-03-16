import json
from datetime import datetime

def generate_status():
    status = []
    # Parse logs or use previous results
    status.append({
        "user": "USER1",
        "status": "Success",
        "timestamp": datetime.now().isoformat()
    })
    
    with open("dashboard/status.json", "w") as f:
        json.dump(status, f)

if __name__ == "__main__":
    generate_status()