import requests
import time
import os
from datetime import datetime
import json
from pushbullet import Pushbullet

# Configure these variables
API_URL = "https://api.bdtickets.com:20102/v1/coaches/search"
CHECK_INTERVAL_MINUTES = 1  
PUSHBULLET_API_KEY = os.getenv("PUSHBULLET_API_KEY")
TRAVEL_DATE = "2025-03-12"
RETURN_DATE = "2025-03-13"

# TRAVEL_DATE = "2025-03-27"
# RETURN_DATE = "2025-04-05"


ONWARD_ROUTES = ["dhaka-to-rajshahi", "dhaka-to-chapainawabganj"]
RETURN_ROUTES = ["rajshahi-to-dhaka", "chapainawabganj-to-dhaka"]

TARGET_COMPANIES = ["National Travels", "Desh Travels", "Grameen Travels", "KTC Hanif", "Hanif Enterprise"]

# Initialize Pushbullet for notifications
pb = Pushbullet(PUSHBULLET_API_KEY)

# Create a log file
def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)

# Function to check for available tickets
def check_tickets(travel_date, routes, journey_type):
    log_message(f"Checking {journey_type} tickets for {travel_date}...")
    
    found_tickets = []
    tickets_for_cache = []
    for route in routes:
        log_message(f"Checking route: {route}")
        
        payload = {
            "date": travel_date,
            "identifier": route,
            "structureType": "BUS"
        }
        
        try:
            response = requests.post(API_URL, json=payload, headers={"Content-Type": "application/json"})
            response.raise_for_status()
            data = response.json()
            
            if data.get("data"):
                for coach in data["data"]:
                    company_name = coach.get("companyName", "")
                    coach_no = coach.get("coachNo", "")
                    if company_name in TARGET_COMPANIES and coach.get("availableSeats", 0) > 0:
                        found_tickets.append({
                            "company": company_name,
                            "coach_no": coach_no,
                            "route": route,
                            "journey_type": journey_type
                        })
                        tickets_for_cache.append({"coach_no": coach_no})

        except Exception as e:
            log_message(f"Error checking {route}: {str(e)}")
    
    return found_tickets, tickets_for_cache

# Function to send notifications
def send_notification(tickets, journey_type):
    if not tickets:
        return
    
    unique_routes = set(ticket['route'] for ticket in tickets)
    unique_companies = set(ticket['company'] for ticket in tickets)
    journey_types = set(ticket['journey_type'] for ticket in tickets)

    title = f"🚌 {journey_type} Bus Availability Update"
    body = f"Available Buses: {len(tickets)}\n"
    body += f"Companies: {', '.join(unique_companies)}\n"
    body += f"Routes: {', '.join(unique_routes)}\n"
    body += f"Journey Types: {', '.join(journey_types)}"
    
    try:
        pb.push_note(title, body)
        log_message(f"Notification sent: {title}")
    except Exception as e:
        log_message(f"Failed to send notification: {str(e)}")

# Save previously found tickets to avoid duplicate notifications
def save_ticket_cache(onward_tickets, return_tickets):
    cache_data = {
        "onward": onward_tickets,
        "return": return_tickets
    }
    with open("ticket_cache.json", "w") as f:
        json.dump(cache_data, f)

# Load previously found tickets
def load_ticket_cache():
    try:
        with open("ticket_cache.json", "r") as f:
            data = json.load(f)
            return data.get("onward", []), data.get("return", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return [], []

# Check if we have new tickets we haven't notified about
def get_new_tickets(current_tickets, cached_tickets):
    if not cached_tickets:
        return current_tickets
    
    cached_keys = {ticket['coach_no'] for ticket in cached_tickets}
    return [ticket for ticket in current_tickets if ticket['coach_no'] not in cached_keys]

# Main loop
def main():
    log_message("Bus ticket monitor started (GitHub Actions)")

    onward_tickets, onward_cache = check_tickets(TRAVEL_DATE, ONWARD_ROUTES, "Onward")
    return_tickets, return_cache = check_tickets(RETURN_DATE, RETURN_ROUTES, "Return")

    cached_onward_tickets, cached_return_tickets = load_ticket_cache()

    new_onward_tickets = get_new_tickets(onward_tickets, cached_onward_tickets)
    if new_onward_tickets:
        send_notification(new_onward_tickets, "Onward")

    new_return_tickets = get_new_tickets(return_tickets, cached_return_tickets)
    if new_return_tickets:
        send_notification(new_return_tickets, "Return")

    save_ticket_cache(onward_cache, return_cache)
    log_message("Job completed successfully!")


if __name__ == "__main__":
    main()