import requests
import time
import os
from datetime import datetime
import json
from pushbullet import Pushbullet
from dotenv import load_dotenv

load_dotenv()

# Configure from environment variables
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", "3"))
PUSHBULLET_API_KEY = os.getenv("PUSHBULLET_API_KEY")
TRAVEL_DATE = os.getenv("TRAVEL_DATE")
RETURN_DATE = os.getenv("RETURN_DATE")
SEARCH_ONWORD = os.getenv("SEARCH_ONWORD", "True").lower() == "true"
SEARCH_RETURN = os.getenv("SEARCH_RETURN", "True").lower() == "true"

# BDTickets Configuration
BDTICKETS_API_URL = "https://api.bdtickets.com:20102/v1/coaches/search"
BDTICKETS_ONWARD_ROUTES = ["dhaka-to-rajshahi", "dhaka-to-chapainawabganj"]
BDTICKETS_RETURN_ROUTES = ["rajshahi-to-dhaka", "chapainawabganj-to-dhaka"]

# BusBD Configuration
BUSBD_API_URL = "https://api.busbd.com.bd/api/v2/searchlist"
DHAKA_ID = 14
RAJSHAHI_ID = 55
CHAPAI_ID = 9

# Target companies (same for both sources)
TARGET_COMPANIES = [
    "National Travels", "Desh Travels", "Grameen Travels",
    "KTC Hanif", "Hanif Enterprise", "Shyamoli N.R Travels",
    "Shyamoli NR Travels"
]

# Initialize Pushbullet
pb = Pushbullet(PUSHBULLET_API_KEY)

def log_message(message, source=None):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    source_prefix = f"[{source}] " if source else ""
    log_entry = f"[{timestamp}] {source_prefix}{message}"
    print(log_entry)

# ==================== BDTickets Functions ====================

def check_bdtickets(travel_date, routes, journey_type):
    log_message(f"Checking {journey_type} tickets for {travel_date}...", "BDTickets")
    found_tickets = []
    tickets_for_cache = []

    for route in routes:
        log_message(f"Checking route: {route}", "BDTickets")
        payload = {
            "date": travel_date,
            "identifier": route,
            "structureType": "BUS"
        }

        try:
            response = requests.post(BDTICKETS_API_URL, json=payload, headers={"Content-Type": "application/json"})
            response.raise_for_status()
            data = response.json()

            if data.get("data"):
                for coach in data["data"]:
                    company_name = coach.get("companyName", "")
                    coach_no = coach.get("coachNo", "")
                    if company_name in TARGET_COMPANIES:
                        found_tickets.append({
                            "company": company_name,
                            "coach_no": coach_no,
                            "route": route,
                            "journey_type": journey_type,
                            "source": "BDTickets"
                        })
                        tickets_for_cache.append({"coach_no": coach_no})

        except Exception as e:
            log_message(f"Error checking {route}: {str(e)}", "BDTickets")

    return found_tickets, tickets_for_cache

def save_bdtickets_cache(onward_tickets, return_tickets):
    cache_data = {
        "onward": onward_tickets,
        "return": return_tickets
    }
    with open("ticket_cache.json", "w") as f:
        json.dump(cache_data, f)

def load_bdtickets_cache():
    try:
        with open("ticket_cache.json", "r") as f:
            data = json.load(f)
            return data.get("onward", []), data.get("return", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return [], []

# ==================== BusBD Functions ====================

def check_busbd(travel_date, from_ids, to_ids, journey_type):
    log_message(f"Checking {journey_type.lower()} tickets for {travel_date}...", "BusBD")
    found_tickets = []
    tickets_for_cache = []

    for from_id in from_ids:
        for to_id in to_ids:
            log_message(f"Checking from_id: {from_id} -> to_id: {to_id}", "BusBD")
            payload = {
                "jrdate": travel_date,
                "fromid": from_id,
                "toid": to_id,
                "coach_type": None
            }

            try:
                response = requests.post(BUSBD_API_URL, json=payload, headers={"Content-Type": "application/json"})
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
                                "journey_type": journey_type,
                                "source": "BusBD"
                            })
                            tickets_for_cache.append({"coach_no": coach_no})

            except Exception as e:
                log_message(f"Error checking from_id {from_id} to_id {to_id}: {str(e)}", "BusBD")

    return found_tickets, tickets_for_cache

def save_busbd_cache(tickets):
    with open("ticket_cache_busbd.json", "w") as f:
        json.dump(tickets, f)

def load_busbd_cache():
    try:
        with open("ticket_cache_busbd.json", "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

# ==================== Common Functions ====================

def send_notification(tickets, journey_type, source):
    if not tickets:
        return

    unique_routes = set(ticket['route'] for ticket in tickets)
    unique_companies = set(ticket['company'] for ticket in tickets)

    title = f"🚌 {journey_type} Bus Availability - {source}"
    body = f"Available Buses: {len(tickets)}\n"
    body += f"Companies: {', '.join(unique_companies)}\n"
    body += f"Routes: {', '.join(unique_routes)}"

    try:
        pb.push_note(title, body)
        log_message(f"Notification sent: {title}", source)
    except Exception as e:
        log_message(f"Failed to send notification: {str(e)}", source)

def get_new_tickets(current_tickets, cached_tickets):
    if not cached_tickets:
        return current_tickets

    cached_keys = {ticket['coach_no'] for ticket in cached_tickets}
    return [ticket for ticket in current_tickets if ticket['coach_no'] not in cached_keys]

# ==================== Main Monitoring Loop ====================

def monitor_bdtickets():
    """Monitor BDTickets.com for ticket availability"""
    try:
        cached_onward_tickets, cached_return_tickets = load_bdtickets_cache()
        onward_cache = []
        return_cache = []

        if SEARCH_ONWORD:
            onward_tickets, onward_cache = check_bdtickets(TRAVEL_DATE, BDTICKETS_ONWARD_ROUTES, "Onward")
            new_onward_tickets = get_new_tickets(onward_tickets, cached_onward_tickets)
            if new_onward_tickets:
                log_message(f"Found {len(new_onward_tickets)} NEW onward buses to notify about", "BDTickets")
                send_notification(new_onward_tickets, "Onward", "BDTickets")

        if SEARCH_RETURN:
            return_tickets, return_cache = check_bdtickets(RETURN_DATE, BDTICKETS_RETURN_ROUTES, "Return")
            new_return_tickets = get_new_tickets(return_tickets, cached_return_tickets)
            if new_return_tickets:
                log_message(f"Found {len(new_return_tickets)} NEW return buses to notify about", "BDTickets")
                send_notification(new_return_tickets, "Return", "BDTickets")

        # Save updated cache
        save_bdtickets_cache(onward_cache, return_cache)

    except Exception as e:
        log_message(f"Error in BDTickets monitoring: {str(e)}", "BDTickets")

def monitor_busbd():
    """Monitor BusBD.com for ticket availability"""
    try:
        cached_tickets = load_busbd_cache()
        all_new_tickets = []
        updated_cache = []

        if SEARCH_ONWORD:
            from_ids = [DHAKA_ID]
            to_ids = [RAJSHAHI_ID, CHAPAI_ID]
            onward_tickets, onward_cache = check_busbd(TRAVEL_DATE, from_ids, to_ids, "Onward")
            new_onward = get_new_tickets(onward_tickets, cached_tickets)
            if new_onward:
                log_message(f"Found {len(new_onward)} NEW onward buses to notify about", "BusBD")
                send_notification(new_onward, "Onward", "BusBD")
                all_new_tickets.extend(new_onward)
                updated_cache.extend(onward_cache)

        if SEARCH_RETURN:
            from_ids = [RAJSHAHI_ID, CHAPAI_ID]
            to_ids = [DHAKA_ID]
            return_tickets, return_cache = check_busbd(RETURN_DATE, from_ids, to_ids, "Return")
            new_return = get_new_tickets(return_tickets, cached_tickets)
            if new_return:
                log_message(f"Found {len(new_return)} NEW return buses to notify about", "BusBD")
                send_notification(new_return, "Return", "BusBD")
                all_new_tickets.extend(new_return)
                updated_cache.extend(return_cache)

        # Save updated cache
        if all_new_tickets:
            save_busbd_cache(updated_cache)

    except Exception as e:
        log_message(f"Error in BusBD monitoring: {str(e)}", "BusBD")

def main():
    log_message("=" * 60)
    log_message("Unified Bus Ticket Monitor Started")
    log_message(f"Monitoring: BDTickets.com & BusBD.com")
    log_message(f"Check Interval: {CHECK_INTERVAL_MINUTES} minutes")
    log_message(f"Travel Date: {TRAVEL_DATE}")
    log_message(f"Return Date: {RETURN_DATE}")
    log_message(f"Search Onward: {SEARCH_ONWORD}")
    log_message(f"Search Return: {SEARCH_RETURN}")
    log_message("=" * 60)

    while True:
        try:
            log_message("\n" + "=" * 60)
            log_message("Starting new check cycle...")
            log_message("=" * 60)

            # Monitor both sources independently
            # If one fails, the other will continue
            monitor_bdtickets()
            monitor_busbd()

            log_message("=" * 60)
            log_message(f"Check cycle completed. Sleeping for {CHECK_INTERVAL_MINUTES} minutes...")
            log_message("=" * 60 + "\n")

            time.sleep(CHECK_INTERVAL_MINUTES * 60)

        except KeyboardInterrupt:
            log_message("Monitor stopped by user")
            break
        except Exception as e:
            log_message(f"Unexpected error in main loop: {str(e)}")
            log_message(f"Retrying in {CHECK_INTERVAL_MINUTES} minutes...")
            time.sleep(CHECK_INTERVAL_MINUTES * 60)

if __name__ == "__main__":
    main()

