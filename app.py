import requests
import os
from datetime import datetime
import json
from flask import Flask, request, jsonify
from pushbullet import Pushbullet
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Initialize Pushbullet
PUSHBULLET_API_KEY = os.getenv("PUSHBULLET_API_KEY")
pb = Pushbullet(PUSHBULLET_API_KEY) if PUSHBULLET_API_KEY else None

# BDTickets Configuration
BDTICKETS_API_URL = "https://api.bdtickets.com:20102/v1/coaches/search"
BDTICKETS_ONWARD_ROUTES = ["dhaka-to-rajshahi", "dhaka-to-chapainawabganj"]
BDTICKETS_RETURN_ROUTES = ["rajshahi-to-dhaka", "chapainawabganj-to-dhaka"]

# BusBD Configuration
BUSBD_API_URL = "https://api.busbd.com.bd/api/v2/searchlist"
DHAKA_ID = 14
RAJSHAHI_ID = 55
CHAPAI_ID = 9

# Target companies
TARGET_COMPANIES = [
    "National Travels", "Desh Travels", "Grameen Travels",
    "KTC Hanif", "Hanif Enterprise", "Shyamoli N.R Travels",
    "Shyamoli NR Travels"
]

def log_message(message, source=None):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    source_prefix = f"[{source}] " if source else ""
    log_entry = f"[{timestamp}] {source_prefix}{message}"
    print(log_entry)
    return log_entry

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
            response = requests.post(BDTICKETS_API_URL, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
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

# ==================== BusBD Functions ====================

def check_busbd(travel_date, from_ids, to_ids, journey_type):
    log_message(f"Checking {journey_type} tickets for {travel_date}...", "BusBD")
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
                response = requests.post(BUSBD_API_URL, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
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

# ==================== Notification Functions ====================

def send_notification(tickets, journey_type, source, journey_date):
    """Send notification for tickets from a specific source"""
    if not tickets or not pb:
        return False

    unique_routes = set(ticket['route'] for ticket in tickets)
    unique_companies = set(ticket['company'] for ticket in tickets)

    title = f"🚌 {journey_type} Bus Availability - {source}"
    body = f"Journey Date: {journey_date}\n"
    body += f"Available Buses: {len(tickets)}\n"
    body += f"Companies: {', '.join(unique_companies)}\n"
    body += f"Routes: {', '.join(unique_routes)}"

    try:
        pb.push_note(title, body)
        log_message(f"Notification sent: {title} for {journey_date}", source)
        return True
    except Exception as e:
        log_message(f"Failed to send notification: {str(e)}", source)
        return False

# ==================== Cache Functions ====================

def load_cache(cache_file):
    try:
        with open(cache_file, "r") as f:
            cache = json.load(f)
            # Ensure all required fields exist
            if "search_params" not in cache:
                cache["search_params"] = {}
            if "tickets_by_date" not in cache:
                cache["tickets_by_date"] = {}
            return cache
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "search_params": {},
            "tickets_by_date": {}
        }

def get_cached_tickets_for_date(cache, date, journey_type):
    """Get cached tickets for a specific date and journey type"""
    tickets_by_date = cache.get("tickets_by_date", {})
    date_cache = tickets_by_date.get(date, {})
    return date_cache.get(journey_type.lower(), [])

def save_tickets_for_date(cache, date, journey_type, tickets):
    """Save tickets for a specific date and journey type"""
    if "tickets_by_date" not in cache:
        cache["tickets_by_date"] = {}
    if date not in cache["tickets_by_date"]:
        cache["tickets_by_date"][date] = {}
    cache["tickets_by_date"][date][journey_type.lower()] = tickets

def save_cache(cache_file, cache_data):
    with open(cache_file, "w") as f:
        json.dump(cache_data, f, indent=2)

def has_new_tickets(current_tickets, cached_tickets):
    current_coach_nos = set(ticket["coach_no"] for ticket in current_tickets)
    cached_coach_nos = set(ticket["coach_no"] for ticket in cached_tickets)
    return bool(current_coach_nos - cached_coach_nos)

# ==================== Flask Routes ====================

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "status": "ok",
        "message": "Ticket Monitor API is running",
        "endpoints": {
            "/check": "POST - Check for tickets",
            "/health": "GET - Health check"
        }
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.route('/check', methods=['POST'])
def check_tickets():
    try:
        # Load cache first to get cached search params
        cache = load_cache("ticket_cache_api.json")
        cached_search_params = cache.get("search_params", {})

        # Get payload data (can be empty to use cached params)
        data = request.get_json() or {}

        # Use provided params or fall back to cached params
        travel_date = data.get('TRAVEL_DATE') or cached_search_params.get('TRAVEL_DATE')
        return_date = data.get('RETURN_DATE') or cached_search_params.get('RETURN_DATE')
        search_onward = data.get('SEARCH_ONWARD', cached_search_params.get('SEARCH_ONWARD', True))
        search_return = data.get('SEARCH_RETURN', cached_search_params.get('SEARCH_RETURN', False))

        if not travel_date:
            return jsonify({
                "status": "error",
                "message": "TRAVEL_DATE is required (either in payload or cached)"
            }), 400

        # Save current search params for future use
        current_search_params = {
            'TRAVEL_DATE': travel_date,
            'RETURN_DATE': return_date,
            'SEARCH_ONWARD': search_onward,
            'SEARCH_RETURN': search_return
        }

        log_message("="*50)
        log_message(f"Starting ticket check")
        log_message(f"Travel Date: {travel_date}")
        log_message(f"Return Date: {return_date}")
        log_message(f"Search Onward: {search_onward}")
        log_message(f"Search Return: {search_return}")

        # Get cached tickets for specific dates
        cached_onward = get_cached_tickets_for_date(cache, travel_date, "onward") if travel_date else []
        cached_return = get_cached_tickets_for_date(cache, return_date, "return") if return_date else []

        # Check onward tickets
        if search_onward and travel_date:
            # Check BDTickets
            bdtickets_onward, bdtickets_onward_cache = check_bdtickets(
                travel_date,
                BDTICKETS_ONWARD_ROUTES,
                "Onward"
            )

            # Check for new BDTickets tickets and notify
            if bdtickets_onward and has_new_tickets(bdtickets_onward_cache, cached_onward):
                log_message(f"Found {len(bdtickets_onward)} NEW onward buses from BDTickets for {travel_date}", "BDTickets")
                if send_notification(bdtickets_onward, "Onward", "BDTickets", travel_date):
                    # Merge with existing cache for this date
                    updated_cache = cached_onward + bdtickets_onward_cache
                    save_tickets_for_date(cache, travel_date, "onward", updated_cache)
                else:
                    log_message("Notification failed, not caching tickets", "BDTickets")

            # Check BusBD
            busbd_onward, busbd_onward_cache = check_busbd(
                travel_date,
                [DHAKA_ID],
                [RAJSHAHI_ID, CHAPAI_ID],
                "Onward"
            )

            # Check for new BusBD tickets and notify
            if busbd_onward and has_new_tickets(busbd_onward_cache, cached_onward):
                log_message(f"Found {len(busbd_onward)} NEW onward buses from BusBD for {travel_date}", "BusBD")
                if send_notification(busbd_onward, "Onward", "BusBD", travel_date):
                    # Merge with existing cache for this date
                    current_cache = get_cached_tickets_for_date(cache, travel_date, "onward")
                    updated_cache = current_cache + busbd_onward_cache
                    save_tickets_for_date(cache, travel_date, "onward", updated_cache)
                else:
                    log_message("Notification failed, not caching tickets", "BusBD")

        # Check return tickets
        if search_return and return_date:
            # Check BDTickets
            bdtickets_return, bdtickets_return_cache = check_bdtickets(
                return_date,
                BDTICKETS_RETURN_ROUTES,
                "Return"
            )

            # Check for new BDTickets tickets and notify
            if bdtickets_return and has_new_tickets(bdtickets_return_cache, cached_return):
                log_message(f"Found {len(bdtickets_return)} NEW return buses from BDTickets for {return_date}", "BDTickets")
                if send_notification(bdtickets_return, "Return", "BDTickets", return_date):
                    # Merge with existing cache for this date
                    updated_cache = cached_return + bdtickets_return_cache
                    save_tickets_for_date(cache, return_date, "return", updated_cache)
                else:
                    log_message("Notification failed, not caching tickets", "BDTickets")

            # Check BusBD
            busbd_return, busbd_return_cache = check_busbd(
                return_date,
                [RAJSHAHI_ID, CHAPAI_ID],
                [DHAKA_ID],
                "Return"
            )

            # Check for new BusBD tickets and notify
            if busbd_return and has_new_tickets(busbd_return_cache, cached_return):
                log_message(f"Found {len(busbd_return)} NEW return buses from BusBD for {return_date}", "BusBD")
                if send_notification(busbd_return, "Return", "BusBD", return_date):
                    # Merge with existing cache for this date
                    current_cache = get_cached_tickets_for_date(cache, return_date, "return")
                    updated_cache = current_cache + busbd_return_cache
                    save_tickets_for_date(cache, return_date, "return", updated_cache)
                else:
                    log_message("Notification failed, not caching tickets", "BusBD")

        # Save search params
        cache["search_params"] = current_search_params
        save_cache("ticket_cache_api.json", cache)

        log_message("="*50)
        log_message(f"Check completed successfully")

        return jsonify({
            "status": "success",
            "message": "Ticket check completed",
            "search_params": current_search_params,
            "timestamp": datetime.now().isoformat()
        }), 200

    except Exception as e:
        log_message(f"Error in check_tickets endpoint: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

