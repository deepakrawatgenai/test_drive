"""
LangChain tools for Toyota Sales Assistant (UTF-8 clean)
Exports list: tools
"""

import os
import json
from datetime import datetime
from dotenv import load_dotenv

try:
    from langchain_core.tools import Tool
except Exception:
    from langchain.tools import Tool  # type: ignore

try:
    from langchain_community.utilities import GoogleSerperAPIWrapper
except Exception:
    GoogleSerperAPIWrapper = None  # type: ignore

from database_setup import (
    query_db,
    insert_data,
    update_data,
    get_inventory_by_zipcode,
)

load_dotenv()
SERPER_API_KEY = os.getenv("SERPER_API_KEY")


def serper_search_tool(json_input: str) -> str:
    try:
        payload = json.loads(json_input)
        q = payload.get("q", "").strip()
        if not q:
            return json.dumps({"error": "missing_query"})
        if not SERPER_API_KEY or GoogleSerperAPIWrapper is None:
            return json.dumps({
                "ok": True,
                "text": f"No SERPER configured. For '{q}', check toyota.com or official resources.",
            })
        search = GoogleSerperAPIWrapper()
        out = search.run(q)
        return json.dumps({"ok": True, "text": out})
    except Exception as e:
        return json.dumps({"error": "serper_failed", "detail": str(e)})


def vehicle_search_tool(json_input: str) -> str:
    try:
        q = json.loads(json_input)
    except Exception:
        return json.dumps({"error": "invalid_json"})

    model = q.get("model")
    trim = q.get("trim")
    color = q.get("color")
    zipcode = q.get("zipcode")
    features = q.get("features", []) or []

    try:
        inv = (
            get_inventory_by_zipcode(zipcode, model)
            if (zipcode or model)
            else get_inventory_by_zipcode(None, None)
        )
        results = []
        for row in inv:
            (
                vid,
                v_model,
                v_trim,
                v_color,
                v_rate,
                v_features,
                d_name,
                d_city,
                d_zip,
                d_addr,
                d_phone,
                inv_id,
                vin,
            ) = row

            if trim and str(v_trim).lower() != str(trim).lower():
                continue
            if color and str(v_color).lower() != str(color).lower():
                continue

            try:
                feat = json.loads(v_features) if v_features else {}
            except Exception:
                feat = {}

            if features:
                joined = json.dumps(feat).lower()
                if not any(str(f).lower() in joined for f in features):
                    continue

            results.append(
                {
                    "vehicle": {
                        "vehicle_id": vid,
                        "make": "Toyota",
                        "model": v_model,
                        "trim": v_trim,
                        "color": v_color,
                        "price": v_rate,
                        "features": feat,
                        "vin": vin,
                    },
                    "dealership": {
                        "name": d_name,
                        "address": d_addr,
                        "city": d_city,
                        "zipcode": d_zip,
                        "phone": d_phone,
                    },
                    "inventory_id": inv_id,
                }
            )
        return json.dumps({"ok": True, "results": results}, default=str)
    except Exception as e:
        return json.dumps({"error": "inventory_query_failed", "detail": str(e)})


def save_booking_tool(json_input: str) -> str:
    try:
        payload = json.loads(json_input)
    except Exception:
        return json.dumps({"error": "invalid_json"})

    cust = payload.get("customer", {})
    vehicle = payload.get("vehicle", {})
    dealership_id = payload.get("dealership_id")
    salesperson_id = payload.get("salesperson_id")
    inventory_id = payload.get("inventory_id")
    date_s = payload.get("date")
    time_s = payload.get("time")
    special = payload.get("special_request", "")

    # Resolve dealership_id and/or vehicle_id from inventory if provided
    try:
        if (not dealership_id or not vehicle.get("vehicle_id")) and inventory_id:
            inv_rows = query_db(
                "SELECT dealership_id, vehicle_id FROM Inventory WHERE id = ?",
                (inventory_id,),
            )
            if inv_rows:
                inv_dealer_id, inv_vehicle_id = inv_rows[0]
                dealership_id = dealership_id or inv_dealer_id
                if not vehicle.get("vehicle_id"):
                    vehicle["vehicle_id"] = inv_vehicle_id
    except Exception:
        # Continue; required check below will handle any missing pieces
        pass

    required = [cust.get("email"), vehicle.get("vehicle_id"), dealership_id, date_s, time_s]
    if not all(required):
        return json.dumps({"error": "missing_required_fields"})

    try:
        existing = query_db("SELECT customer_id FROM Customer WHERE email = ?", (cust.get("email"),))
        if existing:
            customer_id = existing[0][0]
            update_data(
                "UPDATE Customer SET customer_name=?, phone=?, city=?, zipcode=? WHERE customer_id=?",
                (
                    cust.get("name"),
                    cust.get("phone"),
                    cust.get("city"),
                    cust.get("zipcode"),
                    customer_id,
                ),
            )
        else:
            customer_id = insert_data(
                "INSERT INTO Customer (customer_name, email, phone, zipcode, city) VALUES (?, ?, ?, ?, ?)",
                (
                    cust.get("name"),
                    cust.get("email"),
                    cust.get("phone"),
                    cust.get("zipcode"),
                    cust.get("city"),
                ),
            )

        if not customer_id:
            return json.dumps({"error": "customer_save_failed"})

        created = datetime.utcnow().isoformat()
        testdrive_id = insert_data(
            (
                "INSERT INTO TestDrive (customer_id, dealership_id, salesperson_id, vehicle_id, date, time, special_request, status, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, 'scheduled', ?)"
            ),
            (
                customer_id,
                dealership_id,
                salesperson_id,
                vehicle.get("vehicle_id"),
                date_s,
                time_s,
                special,
                created,
            ),
        )

        if not testdrive_id:
            return json.dumps({"error": "booking_save_failed"})

        # If we know the inventory row, reserve it to avoid double booking
        if inventory_id:
            try:
                update_data(
                    "UPDATE Inventory SET available_status = 'reserved' WHERE id = ?",
                    (inventory_id,),
                )
            except Exception:
                # Non-fatal; booking still succeeded
                pass

        return json.dumps({"ok": True, "testdrive_id": testdrive_id, "inventory_id": inventory_id})
    except Exception as e:
        return json.dumps({"error": "save_failed", "detail": str(e)})


def send_email_tool(json_input: str) -> str:
    try:
        payload = json.loads(json_input)
    except Exception:
        return json.dumps({"error": "invalid_json"})

    to = payload.get("to")
    subject = payload.get("subject", "Toyota Test Drive")
    html = payload.get("html", "")

    try:
        from notifications import send_email as send_email_fn
    except Exception as e:
        return json.dumps({"error": "email_helper_missing", "detail": str(e)})

    ok = send_email_fn(to, subject, html, is_html=True)
    return json.dumps({"ok": bool(ok), "to": to})


def get_vehicle_details_tool(json_input: str) -> str:
    try:
        payload = json.loads(json_input)
        vid = payload.get("vehicle_id")
        if not vid:
            return json.dumps({"error": "missing_vehicle_id"})
    except Exception:
        return json.dumps({"error": "invalid_json"})

    try:
        query = (
            "SELECT v.id, v.make, v.model, v.trim, v.color, v.rate, v.features, "
            "d.dealership_name, d.address, d.city, d.zipcode, d.phone, i.vin "
            "FROM Vehicle v JOIN Inventory i ON i.vehicle_id = v.id "
            "JOIN Dealership d ON i.dealership_id = d.dealership_id "
            "WHERE v.id = ? AND i.available_status = 'available' LIMIT 1"
        )
        rows = query_db(query, (vid,))
        if not rows:
            return json.dumps({"error": "not_found"})
        (
            v_id,
            make,
            model_name,
            trim,
            color,
            rate,
            features_json,
            dealership_name,
            address,
            city,
            zipcode,
            phone,
            vin,
        ) = rows[0]

        try:
            features = json.loads(features_json) if features_json else {}
        except Exception:
            features = {}

        result = {
            "vehicle": {
                "id": v_id,
                "make": make,
                "model": model_name,
                "trim": trim,
                "color": color,
                "price": rate,
                "features": features,
                "vin": vin,
            },
            "dealership": {
                "name": dealership_name,
                "address": address,
                "city": city,
                "zipcode": zipcode,
                "phone": phone,
            },
        }
        return json.dumps({"ok": True, "result": result}, default=str)
    except Exception as e:
        return json.dumps({"error": "db_failed", "detail": str(e)})


# LangChain Tool wrappers
serper_tool = Tool(
    name="search_toyota_info",
    func=lambda q: serper_search_tool(json.dumps({"q": q})),
    description=(
        "Search Toyota info/specs/reviews via Serper (falls back gracefully without API key). "
        "Input: plain query string."
    ),
)

inventory_tool = Tool(
    name="search_inventory",
    func=lambda s: (
        vehicle_search_tool(json.dumps({"zipcode": s}) if isinstance(s, str) and s.isdigit() else s)
    ),
    description=(
        "Search inventory by ZIP (string) or JSON with filters: {zipcode, model, trim, color, features}."
    ),
)

booking_tool = Tool(
    name="save_test_drive",
    func=save_booking_tool,
    description=(
        "Save test drive booking. Input JSON: {customer:{name,email,phone,city,zipcode}, "
        "vehicle:{vehicle_id}, dealership_id OR inventory_id, salesperson_id, date, time, special_request}."
    ),
)

vehicle_details_tool = Tool(
    name="get_vehicle_details",
    func=lambda s: get_vehicle_details_tool(s if isinstance(s, str) else json.dumps({"vehicle_id": s})),
    description="Get vehicle details. Input JSON: {vehicle_id} or just vehicle_id as string.",
)

send_email = Tool(
    name="send_email",
    func=send_email_tool,
    description="Send HTML email via configured SMTP (delegates to notifications.py). Input JSON: {to, subject, html}.",
)

# Export list for agent creation
tools = [serper_tool, inventory_tool, booking_tool, vehicle_details_tool, send_email]
