from fastapi import APIRouter
from core.metrics import metrics_data
import os
router = APIRouter(prefix="/api/v1/monitoring", tags=["Monitoring"])

def get_recent_errors(log_file="app.log", max_lines=50):
    errors = []
    if not os.path.exists(log_file):
        return errors
    
    with open(log_file, "r") as f:
        lines = f.readlines()
        for line in reversed(lines):
            if " - ERROR - " in line or " - CRITICAL - " in line:
                errors.append(line.strip())
            if len(errors) >= max_lines:
                break
    return errors

@router.get("/dashboard")
def get_dashboard_data():
    req_count = metrics_data["total_requests"]
    err_count = metrics_data["total_errors"]
    total_time = metrics_data["total_response_time"]
    
    avg_response_time = (total_time / req_count) if req_count > 0 else 0
    error_rate = (err_count / req_count * 100) if req_count > 0 else 0
    
    recent_errors = get_recent_errors()
    
    return {
        "status": "ok",
        "service": "E-Commerce API",
        "api_metrics": {
            "total_requests": req_count,
            "error_rate_percentage": round(error_rate, 2),
            "average_response_time_seconds": round(avg_response_time, 4),
        },
        "recent_errors": recent_errors
    }
