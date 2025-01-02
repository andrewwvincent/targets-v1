import pandas as pd
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import time
import re
import os
from math import radians, sin, cos, sqrt, atan2

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate the distance between two points on Earth"""
    R = 6371  # Earth's radius in kilometers

    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    distance = R * c

    return distance

def find_nearby_zip(target_zip, zip_data, max_distance=10):
    """Find the nearest ZIP code in our data within max_distance km"""
    if target_zip in zip_data.index:
        return zip_data.loc[target_zip, 'latitude'], zip_data.loc[target_zip, 'longitude']
    
    target_loc = None
    geolocator = Nominatim(user_agent="my_app")
    try:
        location = geolocator.geocode({"postalcode": target_zip, "country": "USA"})
        if location:
            target_loc = (location.latitude, location.longitude)
    except GeocoderTimedOut:
        return None, None
    
    if not target_loc:
        return None, None
    
    nearest_distance = float('inf')
    nearest_coords = None
    
    for idx, row in zip_data.iterrows():
        if pd.isna(row['latitude']) or pd.isna(row['longitude']):
            continue
        
        distance = haversine_distance(target_loc[0], target_loc[1], 
                                    row['latitude'], row['longitude'])
        
        if distance < nearest_distance and distance <= max_distance:
            nearest_distance = distance
            nearest_coords = (row['latitude'], row['longitude'])
    
    if nearest_coords:
        print(f"Found nearby ZIP within {nearest_distance:.2f} km")
        return nearest_coords
    return None, None

def extract_zip(address):
    """Extract ZIP code from address string"""
    # Look for 5 digits at the end of the address
    match = re.search(r'\b(\d{5})\b(?![-\d])', address)
    if match:
        return match.group(1)
    return None

def extract_city_state(address):
    """Extract city and state from address string"""
    # Look for ", CITY, ST" pattern
    match = re.search(r',\s*([^,]+),\s*([A-Z]{2})\s*\d', address)
    if match:
        return f"{match.group(1)}, {match.group(2)}"
    return None

def extract_street_city_state(address):
    """Extract street, city and state from address string"""
    # Look for "STREET Rd/St/Ave/etc, CITY, ST" pattern
    match = re.search(r'(\d+\s+[^,]+(?:Rd|St|Ave|Blvd|Ln|Dr|Ct|Way|Pike|Circle|Square|Trail|Place|Highway|Parkway))[,\s]+([^,]+),\s*([A-Z]{2})', address, re.IGNORECASE)
    if match:
        street = re.sub(r'^\d+\s+', '', match.group(1))  # Remove house number
        return f"{street}, {match.group(2)}, {match.group(3)}"
    return None

def geocode_with_retry(geolocator, query, max_retries=3):
    """Try geocoding with retries and longer timeout"""
    for attempt in range(max_retries):
        try:
            location = geolocator.geocode(query, timeout=10)
            if location:
                return location.latitude, location.longitude
        except (GeocoderTimedOut, Exception) as e:
            if attempt == max_retries - 1:  # Last attempt
                print(f"Failed after {max_retries} attempts: {str(e)}")
                return None, None
            print(f"Attempt {attempt + 1} failed, retrying...")
            time.sleep(2)  # Wait before retry
    return None, None

def geocode_address(address, zip_code=None, zip_data=None):
    """Geocode an address using Nominatim, fall back to ZIP if address fails"""
    # Special cases for problematic addresses
    if "11594 Old Georgetown Rd Rockville, MD" in address:
        print("Using hardcoded coordinates for Old Georgetown Rd location")
        return 39.0485, -77.1277
    elif "24316 W 143rd St, Plainfield, IL" in address:
        print("Using hardcoded coordinates for Eich's Sports Complex")
        return 41.6297, -88.2435  # Correct coordinates for Plainfield, IL location
        
    geolocator = Nominatim(user_agent="my_app")
    
    # Try full address first
    lat, lon = geocode_with_retry(geolocator, address)
    if lat and lon:
        return lat, lon
    
    # If full address fails and we have a ZIP code, try that
    if zip_code:
        lat, lon = geocode_with_retry(geolocator, {"postalcode": zip_code, "country": "USA"})
        if lat and lon:
            return lat, lon
        
        # If direct ZIP lookup fails, try finding a nearby ZIP from our data
        if zip_data is not None:
            lat, lon = find_nearby_zip(zip_code, zip_data)
            if lat and lon:
                return lat, lon
    
    # If ZIP fails, try street, city and state
    street_city_state = extract_street_city_state(address)
    if street_city_state:
        lat, lon = geocode_with_retry(geolocator, street_city_state)
        if lat and lon:
            print(f"Using street/city/state coordinates for: {street_city_state}")
            return lat, lon
    
    # If street fails, try just city and state
    city_state = extract_city_state(address)
    if city_state:
        lat, lon = geocode_with_retry(geolocator, city_state)
        if lat and lon:
            print(f"Using city/state coordinates for: {city_state}")
            return lat, lon
    
    return None, None

# Load the CSV
csv_path = 'data/athletic-center-targets-2024-01-02.csv'
df = pd.read_csv(csv_path)

# Load ZIP data from clusters
zip_data = None
cluster_file = 'data/A_5mi.csv'
if os.path.exists(cluster_file):
    zip_data = pd.read_csv(cluster_file)
    zip_data.set_index('ZIP', inplace=True)
    print("Loaded ZIP code data for nearby location lookup")

# Initialize Latitude and Longitude columns if they don't exist
if 'Latitude' not in df.columns:
    df['Latitude'] = None
if 'Longitude' not in df.columns:
    df['Longitude'] = None

# Force rerun of all addresses
print(f"Processing all {len(df)} addresses")
for i, (idx, row) in enumerate(df.iterrows(), 1):
    address = row['Address']
    zip_code = extract_zip(address)
    
    print(f"Processing {i} of {len(df)}: {address}")
    
    # Try full address first, fall back to ZIP, then nearby ZIPs
    lat, lon = geocode_address(address, zip_code, zip_data)
    
    if lat and lon:
        df.loc[idx, 'Latitude'] = lat
        df.loc[idx, 'Longitude'] = lon
        print(f"Successfully geocoded to: {lat}, {lon}")
    else:
        print(f"Failed to geocode address: {address}")
    
    time.sleep(1)  # Be nice to the geocoding service

# Save updated CSV
df.to_csv(csv_path, index=False)

# Report results
missing = df[df['Latitude'].isna() | df['Longitude'].isna()].shape[0]
print(f"\nGeocoding complete!")
print(f"Successfully geocoded: {len(df) - missing}")
print(f"Failed to geocode: {missing}")
