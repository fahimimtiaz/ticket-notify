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
TRAVEL_DATE = "2025-03-15" 
ROUTES = ["dhaka-to-rajshahi", "dhaka-to-chapainawabganj"]
TARGET_COMPANIES = ["National Travels", "Desh Travels", "Grameen Travels", "KTC Hanif", "Hanif Enterprise"]

# Initialize Pushbullet for notifications
pb = Pushbullet(PUSHBULLET_API_KEY)

# Create a log file
def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)
    with open("ticket_monitor.log", "a") as log_file:
        log_file.write(log_entry + "\n")

# Function to check for available tickets
def check_tickets():
    log_message("Starting ticket availability check...")
    
    found_tickets = []
    tickets_for_cache = []
    for route in ROUTES:
        log_message(f"Checking route: {route}")
        
        payload = {
            "date": TRAVEL_DATE,
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
                            "route": route
                        })
                        tickets_for_cache.append({"coach_no": coach_no})

            
        except Exception as e:
            log_message(f"Error checking {route}: {str(e)}")
    
    return found_tickets, tickets_for_cache

# Function to send notification
def send_notification(tickets):
    if not tickets:
        return
    
    unique_routes = set(ticket['route'] for ticket in tickets)
    unique_companies = set(ticket['company'] for ticket in tickets)

    title = f"🚌 Bus Availability Update"
    body = f"Available Buses: {len(tickets)}\n"
    body += f"Companies: {', '.join(unique_companies)}\n"
    body += f"Routes: {', '.join(unique_routes)}"
    
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
        available_tickets, tickets_for_cache = check_tickets()
        
        if available_tickets:
            log_message(f"Found {len(available_tickets)} available buses")
            cached_tickets = load_ticket_cache()
            new_tickets = get_new_tickets(available_tickets, cached_tickets)
            
            if new_tickets:
                log_message(f"Found {len(new_tickets)} NEW buses to notify about")
                send_notification(new_tickets)
                save_ticket_cache(tickets_for_cache)
            else:
                log_message("No new buses found since last check")
        else:
            log_message("No available buses found")
        
        log_message(f"Sleeping for {CHECK_INTERVAL_MINUTES} minutes until next check")
        log_message(f"======================")
        time.sleep(CHECK_INTERVAL_MINUTES * 60)

if __name__ == "__main__":
    main()