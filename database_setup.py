# database_setup.py
import sqlite3
import json
from pathlib import Path

DB_FILE = "toyota_sales.db"

# Database Schema
SCHEMA = """
PRAGMA foreign_keys = ON;

-- Dealership Table
CREATE TABLE IF NOT EXISTS Dealership (
    dealership_id INTEGER PRIMARY KEY AUTOINCREMENT,
    dealership_name TEXT NOT NULL,
    city TEXT NOT NULL,
    zipcode TEXT NOT NULL,
    address TEXT,
    email TEXT,
    phone TEXT
);

-- Salesperson Table
CREATE TABLE IF NOT EXISTS Salesperson (
    salesperson_id INTEGER PRIMARY KEY AUTOINCREMENT,
    salesperson_name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT,
    dealership_id INTEGER,
    FOREIGN KEY (dealership_id) REFERENCES Dealership(dealership_id)
);

-- Vehicle Table
CREATE TABLE IF NOT EXISTS Vehicle (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    make TEXT NOT NULL DEFAULT 'Toyota',
    model TEXT NOT NULL,
    trim TEXT,
    color TEXT,
    rate REAL,
    features TEXT -- JSON string
);

-- Inventory Table
CREATE TABLE IF NOT EXISTS Inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_id INTEGER,
    dealership_id INTEGER,
    available_status TEXT DEFAULT 'available',
    vin TEXT UNIQUE,
    FOREIGN KEY (vehicle_id) REFERENCES Vehicle(id),
    FOREIGN KEY (dealership_id) REFERENCES Dealership(dealership_id)
);

-- Customer Table
CREATE TABLE IF NOT EXISTS Customer (
    customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    phone TEXT,
    zipcode TEXT,
    city TEXT
);

-- TestDrive Table
CREATE TABLE IF NOT EXISTS TestDrive (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    dealership_id INTEGER,
    salesperson_id INTEGER,
    vehicle_id INTEGER,
    date TEXT,
    time TEXT,
    special_request TEXT,
    status TEXT DEFAULT 'scheduled',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES Customer(customer_id),
    FOREIGN KEY (dealership_id) REFERENCES Dealership(dealership_id),
    FOREIGN KEY (salesperson_id) REFERENCES Salesperson(salesperson_id),
    FOREIGN KEY (vehicle_id) REFERENCES Vehicle(id)
);

-- Feedback Table
CREATE TABLE IF NOT EXISTS Feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    testdrive_id INTEGER,
    feedback TEXT, -- JSON string
    overall_experience INTEGER CHECK(overall_experience BETWEEN 1 AND 5),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (testdrive_id) REFERENCES TestDrive(id)
);
"""

# Sample Toyota Inventory for North America
SAMPLE_DEALERSHIPS = [
    ("Toyota of Downtown Los Angeles", "Los Angeles", "90012", "123 Main St", "la@toyota.com", "213-555-0100"),
    ("Toyota of San Jose", "San Jose", "95110", "456 Tech Blvd", "sj@toyota.com", "408-555-0200"),
    ("Toyota of Chicago", "Chicago", "60601", "789 Loop Ave", "chicago@toyota.com", "312-555-0300"),
    ("Toyota of New York", "New York", "10001", "321 Broadway", "ny@toyota.com", "212-555-0400"),
    ("Toyota of Dallas", "Dallas", "75201", "654 Commerce St", "dallas@toyota.com", "214-555-0500"),
]

SAMPLE_SALESPERSONS = [
    ("Alice Johnson", "alice@toyota.com", "213-555-0101", 1),
    ("Bob Smith", "bob@toyota.com", "408-555-0201", 2),
    ("Carol Brown", "carol@toyota.com", "312-555-0301", 3),
    ("David Wilson", "david@toyota.com", "212-555-0401", 4),
    ("Eve Davis", "eve@toyota.com", "214-555-0501", 5),
]

SAMPLE_VEHICLES = [
    # Sedans
    ("Toyota", "Camry", "LE", "Celestial Silver", 25000.0, json.dumps({"engine": "2.5L 4-Cylinder", "mpg": "28/39", "transmission": "8-Speed Automatic", "safety": "Toyota Safety Sense 2.0"})),
    ("Toyota", "Camry", "SE", "Midnight Black", 27000.0, json.dumps({"engine": "2.5L 4-Cylinder", "mpg": "28/39", "transmission": "8-Speed Automatic", "safety": "Toyota Safety Sense 2.0"})),
    ("Toyota", "Camry", "XSE", "Ruby Flare Pearl", 32000.0, json.dumps({"engine": "2.5L 4-Cylinder", "mpg": "22/32", "transmission": "8-Speed Automatic", "safety": "Toyota Safety Sense 2.0"})),
    ("Toyota", "Corolla", "L", "Classic Silver", 22000.0, json.dumps({"engine": "1.8L 4-Cylinder", "mpg": "31/40", "transmission": "CVT", "safety": "Toyota Safety Sense 2.0"})),
    ("Toyota", "Corolla", "LE", "Barcelona Red", 24000.0, json.dumps({"engine": "1.8L 4-Cylinder", "mpg": "31/40", "transmission": "CVT", "safety": "Toyota Safety Sense 2.0"})),
    ("Toyota", "Avalon", "XLE", "Wind Chill Pearl", 38000.0, json.dumps({"engine": "3.5L V6", "mpg": "22/32", "transmission": "8-Speed Automatic", "safety": "Toyota Safety Sense 2.5+"})),
    
    # SUVs
    ("Toyota", "RAV4", "LE", "Magnetic Gray", 29000.0, json.dumps({"engine": "2.5L 4-Cylinder", "mpg": "27/35", "transmission": "8-Speed Automatic", "drivetrain": "AWD", "safety": "Toyota Safety Sense 2.0"})),
    ("Toyota", "RAV4", "XLE", "Ruby Flare Pearl", 33000.0, json.dumps({"engine": "2.5L 4-Cylinder", "mpg": "27/35", "transmission": "8-Speed Automatic", "drivetrain": "AWD", "safety": "Toyota Safety Sense 2.0"})),
    ("Toyota", "Highlander", "L", "Celestial Silver", 36000.0, json.dumps({"engine": "3.5L V6", "mpg": "21/29", "transmission": "8-Speed Automatic", "drivetrain": "AWD", "seats": 8})),
    ("Toyota", "Highlander", "XLE", "Midnight Black", 42000.0, json.dumps({"engine": "3.5L V6", "mpg": "21/29", "transmission": "8-Speed Automatic", "drivetrain": "AWD", "seats": 8})),
    ("Toyota", "4Runner", "SR5", "Army Green", 40000.0, json.dumps({"engine": "4.0L V6", "mpg": "16/19", "transmission": "5-Speed Automatic", "drivetrain": "4WD", "towing": "5000 lbs"})),
    
    # Hybrids
    ("Toyota", "Prius", "L Eco", "Super White", 25000.0, json.dumps({"engine": "1.8L Hybrid", "mpg": "58/53", "transmission": "CVT", "emissions": "Ultra Low"})),
    ("Toyota", "Prius", "LE", "Barcelona Red", 28000.0, json.dumps({"engine": "1.8L Hybrid", "mpg": "54/50", "transmission": "CVT", "emissions": "Ultra Low"})),
    ("Toyota", "Camry Hybrid", "LE", "Celestial Silver", 29000.0, json.dumps({"engine": "2.5L Hybrid", "mpg": "51/53", "transmission": "CVT", "safety": "Toyota Safety Sense 2.0"})),
    ("Toyota", "RAV4 Hybrid", "LE", "Magnetic Gray", 32000.0, json.dumps({"engine": "2.5L Hybrid", "mpg": "41/38", "transmission": "CVT", "drivetrain": "AWD"})),
    
    # Trucks
    ("Toyota", "Tacoma", "SR", "Super White", 28000.0, json.dumps({"engine": "2.7L 4-Cylinder", "mpg": "20/23", "transmission": "6-Speed Automatic", "bed": "6.1 ft", "towing": "3500 lbs"})),
    ("Toyota", "Tacoma", "TRD Sport", "Army Green", 38000.0, json.dumps({"engine": "3.5L V6", "mpg": "18/22", "transmission": "6-Speed Automatic", "bed": "5 ft", "towing": "6800 lbs"})),
    ("Toyota", "Tundra", "SR5", "Midnight Black", 38000.0, json.dumps({"engine": "3.5L Twin-Turbo V6", "mpg": "18/24", "transmission": "10-Speed Automatic", "bed": "6.5 ft", "towing": "12000 lbs"})),
]

SAMPLE_INVENTORY = [
    # Vehicle ID, Dealership ID, VIN
    (1, 1, "JTDKN3DU5N0123456"),  # Camry LE in LA
    (2, 1, "JTDKN3DU5N0123457"),  # Camry SE in LA
    (3, 2, "JTDKN3DU5N0123458"),  # Camry XSE in San Jose
    (4, 1, "JTDEPRAE5N0123459"),  # Corolla L in LA
    (5, 2, "JTDEPRAE5N0123460"),  # Corolla LE in San Jose
    (6, 3, "4T1BZ1FB5N0123461"),  # Avalon XLE in Chicago
    (7, 1, "JTMWRFEV5N0123462"),  # RAV4 LE in LA
    (8, 2, "JTMWRFEV5N0123463"),  # RAV4 XLE in San Jose
    (9, 3, "5TDBZRFH5N0123464"),  # Highlander L in Chicago
    (10, 4, "5TDBZRFH5N0123465"), # Highlander XLE in NY
    (11, 5, "JTEBU5JR5N0123466"), # 4Runner SR5 in Dallas
    (12, 1, "JTDKARFP5N0123467"), # Prius L Eco in LA
    (13, 2, "JTDKARFP5N0123468"), # Prius LE in San Jose
    (14, 3, "JTNK4RBE5N0123469"), # Camry Hybrid LE in Chicago
    (15, 4, "JTMEB3FV5N0123470"), # RAV4 Hybrid LE in NY
    (16, 5, "3TMCZ5AN5N0123471"), # Tacoma SR in Dallas
    (17, 1, "3TMCZ5AN5N0123472"), # Tacoma TRD Sport in LA
    (18, 2, "5TFDY5F15N0123473"), # Tundra SR5 in San Jose
]


def get_connection():
    """Get SQLite database connection"""
    return sqlite3.connect(DB_FILE)


def init_database():
    """Initialize database with schema and sample data"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Create tables
    cursor.executescript(SCHEMA)
    
    # Insert sample data
    try:
        # Insert dealerships
        cursor.executemany(
            "INSERT OR IGNORE INTO Dealership (dealership_name, city, zipcode, address, email, phone) VALUES (?, ?, ?, ?, ?, ?)",
            SAMPLE_DEALERSHIPS
        )
        
        # Insert salespersons
        cursor.executemany(
            "INSERT OR IGNORE INTO Salesperson (salesperson_name, email, phone, dealership_id) VALUES (?, ?, ?, ?)",
            SAMPLE_SALESPERSONS
        )
        
        # Insert vehicles
        cursor.executemany(
            "INSERT OR IGNORE INTO Vehicle (make, model, trim, color, rate, features) VALUES (?, ?, ?, ?, ?, ?)",
            SAMPLE_VEHICLES
        )
        
        # Insert inventory
        cursor.executemany(
            "INSERT OR IGNORE INTO Inventory (vehicle_id, dealership_id, vin) VALUES (?, ?, ?)",
            SAMPLE_INVENTORY
        )

        conn.commit()
        # Note: avoid emojis in console to prevent UnicodeEncodeError on some Windows shells
        print("Database initialized successfully with sample data")

    except Exception as e:
        # Avoid emojis in console output
        print(f"Database initialization error: {e}")
        conn.rollback()

    finally:
        conn.close()


def query_db(query, params=None):
    """Execute a SELECT query and return results"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        results = cursor.fetchall()
        return results
    except Exception as e:
        print(f"Query error: {e}")
        return []
    finally:
        conn.close()


def insert_data(query, params):
    """Execute an INSERT query and return the last row ID"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"Insert error: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()


def update_data(query, params):
    """Execute an UPDATE query"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        conn.commit()
        return cursor.rowcount
    except Exception as e:
        print(f"Update error: {e}")
        conn.rollback()
        return 0
    finally:
        conn.close()


def get_inventory_by_zipcode(zipcode, model=None):
    """Get available inventory near a zipcode"""
    query = """
    SELECT v.id, v.model, v.trim, v.color, v.rate, v.features, 
           d.dealership_name, d.city, d.zipcode, d.address, d.phone,
           i.id as inventory_id, i.vin
    FROM Vehicle v
    JOIN Inventory i ON v.id = i.vehicle_id
    JOIN Dealership d ON i.dealership_id = d.dealership_id
    WHERE i.available_status = 'available'
    """
    
    params = []
    if zipcode:
        query += " AND d.zipcode = ?"
        params.append(zipcode)
    
    if model:
        query += " AND LOWER(v.model) = LOWER(?)"
        params.append(model)
    
    query += " ORDER BY v.model, v.trim"
    
    return query_db(query, params if params else None)


def get_vehicle_types():
    """Get distinct vehicle types based on model categories"""
    vehicle_categories = {
        "Sedan": ["Camry", "Corolla", "Avalon"],
        "SUV": ["RAV4", "Highlander", "4Runner", "Sequoia", "Land Cruiser"],
        "Hybrid": ["Prius", "Camry Hybrid", "RAV4 Hybrid", "Highlander Hybrid"],
        "Truck": ["Tacoma", "Tundra"],
        "Sports Car": ["GR86", "GR Supra"],
        "Minivan": ["Sienna"]
    }
    return vehicle_categories


def get_models_by_type(vehicle_type):
    """Get models for a specific vehicle type"""
    vehicle_categories = get_vehicle_types()
    return vehicle_categories.get(vehicle_type, [])


def get_all_models():
    """Get all available Toyota models from database"""
    query = "SELECT DISTINCT model FROM Vehicle ORDER BY model"
    results = query_db(query)
    return [row[0] for row in results] if results else []


def get_trims_by_model(model):
    """Get available trims for a specific model"""
    query = "SELECT DISTINCT trim FROM Vehicle WHERE model = ? ORDER BY trim"
    results = query_db(query, (model,))
    return [row[0] for row in results] if results else []


if __name__ == "__main__":
    init_database()