import requests
import time
import os
from datetime import datetime
import json
from pushbullet import Pushbullet

# Configure these variables
API_URL = "https://api.bdtickets.com:20102/v1/coaches/search"
CHECK_INTERVAL_MINUTES = 1  
PUSHBULLET_API_KEY = "o.3aXS4A9KBUIqZ63lF3fCXq4EvOTs4DlY"  
TRAVEL_DATE = "2025-03-12"  # Onward journey
RETURN_DATE = "2025-03-13"  # Return journey

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
def send_notification(tickets):
    if not tickets:
        return
    
    unique_routes = set(ticket['route'] for ticket in tickets)
    unique_companies = set(ticket['company'] for ticket in tickets)
    journey_types = set(ticket['journey_type'] for ticket in tickets)

    title = "🚌 Bus Availability Update"
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
def save_ticket_cache(tickets):
    with open("ticket_cache.json", "w") as f:
        json.dump(tickets, f)

# Load previously found tickets
def load_ticket_cache():
    try:
        with open("ticket_cache.json", "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

# Check if we have new tickets we haven't notified about
def get_new_tickets(current_tickets, cached_tickets):
    if not cached_tickets:
        return current_tickets
    
    cached_keys = {f"{ticket['coach_no']}" for ticket in cached_tickets}
    new_tickets = [ticket for ticket in current_tickets if f"{ticket['coach_no']}" not in cached_keys]
    
    return new_tickets

# Main loop
def main():
    log_message("Bus ticket monitor started")
    
    while True:
        onward_tickets, onward_cache = check_tickets(TRAVEL_DATE, ONWARD_ROUTES, "Onward")
        return_tickets, return_cache = check_tickets(RETURN_DATE, RETURN_ROUTES, "Return")

        all_tickets = onward_tickets + return_tickets
        all_cache = onward_cache + return_cache

        if all_tickets:
            log_message(f"Found {len(all_tickets)} available buses")
            cached_tickets = load_ticket_cache()
            new_tickets = get_new_tickets(all_tickets, cached_tickets)
            
            if new_tickets:
                log_message(f"Found {len(new_tickets)} NEW buses to notify about")
                send_notification(new_tickets)
                save_ticket_cache(all_cache)
            else:
                log_message("No new buses found since last check")
        else:
            log_message("No available buses found")
        
        log_message(f"Sleeping for {CHECK_INTERVAL_MINUTES} minutes until next check")
        log_message("======================")
        time.sleep(CHECK_INTERVAL_MINUTES * 60)

if __name__ == "__main__":
    main()
