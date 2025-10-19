import sqlite3
import json
from typing import List, Dict, Any
import os
from dotenv import load_dotenv
load_dotenv()
DB_PATH = os.getenv('DB_PATH','toyota_sales.db')

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def inventory_lookup(zipcode: str, model: str = None) -> List[Dict[str,Any]]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT dealership_id FROM Dealership WHERE zipcode=?", (zipcode,))
    dealers = cur.fetchall()
    dealer_ids = [d[0] for d in dealers]
    if not dealer_ids:
        return []

    seq = ','.join(['?']*len(dealer_ids))
    query = f"""SELECT Inventory.id as inventory_id, Inventory.vin, Inventory.available_status, 
                Vehicle.model, Vehicle.trim, Vehicle.features, Dealership.dealership_name, Dealership.address
                FROM Inventory 
                JOIN Vehicle ON Inventory.vehicle_id = Vehicle.id 
                JOIN Dealership ON Inventory.dealership_id = Dealership.dealership_id
                WHERE Inventory.dealership_id IN ({seq})"""
    params = dealer_ids
    if model:
        query += " AND Vehicle.model LIKE ?"
        params = dealer_ids + [f"%{model}%"]

    cur.execute(query, params)
    rows = cur.fetchall()
    out = []
    for r in rows:
        feats = []
        try:
            feats = json.loads(r['features']) if r['features'] else []
        except Exception:
            feats = []
        out.append({
            'inventory_id': r['inventory_id'],
            'vin': r['vin'],
            'available_status': r['available_status'],
            'model': r['model'],
            'trim': r['trim'],
            'features': feats,
            'dealership_name': r['dealership_name'],
            'address': r['address'],
            'dealership_id': r.get('dealership_id')
        })
    conn.close()
    return out
