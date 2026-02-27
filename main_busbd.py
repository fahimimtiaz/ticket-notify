import requests
import time
import os
from datetime import datetime
import json
from pushbullet import Pushbullet
from dotenv import load_dotenv

load_dotenv()

# Configure from environment variables
API_URL = "https://api.busbd.com.bd/api/v2/searchlist"
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", "3"))
PUSHBULLET_API_KEY = os.getenv("PUSHBULLET_API_KEY")
TRAVEL_DATE = os.getenv("TRAVEL_DATE")
RETURN_DATE = os.getenv("RETURN_DATE")
SEARCH_ONWORD = os.getenv("SEARCH_ONWORD", "False").lower() == "true"
SEARCH_RETURN = os.getenv("SEARCH_RETURN", "False").lower() == "true"

# Bus stop IDs
DHAKA_ID = 14
RAJSHAHI_ID = 55
CHAPAI_ID = 9

# Target companies
TARGET_COMPANIES = [
    "National Travels", "Desh Travels", "Grameen Travels",
    "KTC Hanif", "Hanif Enterprise", "Shyamoli N.R Travels"
]

# Initialize Pushbullet
pb = Pushbullet(PUSHBULLET_API_KEY)

def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)

def check_tickets(travel_date, from_ids, to_ids, journey_type):
    log_message(f"Checking {journey_type.lower()} tickets for {travel_date}...")
    found_tickets = []
    tickets_for_cache = []

    for from_id in from_ids:
        for to_id in to_ids:
            log_message(f"Checking from_id: {from_id} -> to_id: {to_id}")
            payload = {
                "jrdate": travel_date,
                "fromid": from_id,
                "toid": to_id,
                "coach_type": None
            }

            try:
                response = requests.post(API_URL, json=payload, headers={"Content-Type": "application/json"})
                response.raise_for_status()
                data = response.json()

                if data.get("data") and data["data"].get("coaches"):
                    for coach in data["data"]["coaches"]:
                        company_name = coach.get("company_name", "")
                        coach_no = coach.get("coach_no", "")
                        if company_name in TARGET_COMPANIES:
                            found_tickets.append({
                                "company": company_name,
                                "coach_no": coach_no,
                                "route": f"{coach.get('route_name', '')}",
                                "journey_type": journey_type
                            })
                            tickets_for_cache.append({"coach_no": coach_no})

            except Exception as e:
                log_message(f"Error checking from_id {from_id} to_id {to_id}: {str(e)}")

    return found_tickets, tickets_for_cache

def send_notification(tickets, journey_type):
    if not tickets:
        return

    unique_routes = set(ticket['route'] for ticket in tickets)
    unique_companies = set(ticket['company'] for ticket in tickets)

    title = f"🚌 {journey_type} Bus Availability Update"
    body = f"Available Buses: {len(tickets)}\n"
    body += f"Companies: {', '.join(unique_companies)}\n"
    body += f"Routes: {', '.join(unique_routes)}"

    try:
        pb.push_note(title, body)
        log_message(f"Notification sent: {title}")
    except Exception as e:
        log_message(f"Failed to send notification: {str(e)}")

def save_ticket_cache(tickets):
    with open("ticket_cache_busbd.json", "w") as f:
        json.dump(tickets, f)

def load_ticket_cache():
    try:
        with open("ticket_cache_busbd.json", "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def get_new_tickets(current_tickets, cached_tickets):
    if not cached_tickets:
        return current_tickets

    cached_keys = {ticket['coach_no'] for ticket in cached_tickets}
    return [ticket for ticket in current_tickets if ticket['coach_no'] not in cached_keys]

def main():
    log_message("Bus ticket monitor started")

    while True:
        cached_tickets = load_ticket_cache()
        all_new_tickets = []
        updated_cache = []

        if SEARCH_ONWORD:
            from_ids = [DHAKA_ID]
            to_ids = [RAJSHAHI_ID, CHAPAI_ID]
            onward_tickets, onward_cache = check_tickets(TRAVEL_DATE, from_ids, to_ids, "Onward")
            new_onward = get_new_tickets(onward_tickets, cached_tickets)
            if new_onward:
                log_message(f"Found {len(new_onward)} NEW onward buses to notify about")
                send_notification(new_onward, "Onward")
                all_new_tickets.extend(new_onward)
                updated_cache.extend(onward_cache)

        if SEARCH_RETURN:
            from_ids = [RAJSHAHI_ID, CHAPAI_ID]
            to_ids = [DHAKA_ID]
            return_tickets, return_cache = check_tickets(RETURN_DATE, from_ids, to_ids, "Return")
            new_return = get_new_tickets(return_tickets, cached_tickets)
            if new_return:
                log_message(f"Found {len(new_return)} NEW return buses to notify about")
                send_notification(new_return, "Return")
                all_new_tickets.extend(new_return)
                updated_cache.extend(return_cache)

        # Save updated cache
        if all_new_tickets:
            save_ticket_cache(updated_cache)

        log_message(f"Sleeping for {CHECK_INTERVAL_MINUTES} minutes until next check")
        log_message("======================")
        time.sleep(CHECK_INTERVAL_MINUTES * 60)

if __name__ == "__main__":
    main()
