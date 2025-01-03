import sqlite3
import pandas as pd
import os

def init_database():
    # Create database file if it doesn't exist
    db_path = 'data/targets.db'
    
    # Create the database directory if it doesn't exist
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Drop existing tables if they exist
    cursor.execute('DROP TABLE IF EXISTS targets')
    cursor.execute('DROP TABLE IF EXISTS zip_data')
    
    # Create targets table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS targets (
        organization TEXT PRIMARY KEY,
        address TEXT,
        region TEXT,
        phone TEXT,
        website TEXT,
        notes TEXT,
        drive_radius TEXT,
        population INTEGER,
        households INTEGER,
        median_income INTEGER,
        latitude REAL,
        longitude REAL,
        status TEXT DEFAULT 'not-contacted'
    )
    ''')
    
    # Create zip_data table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS zip_data (
        zip_code TEXT PRIMARY KEY,
        geographic_area TEXT,
        households INTEGER,
        total_pop INTEGER,
        median_income REAL,
        latitude REAL,
        longitude REAL,
        grade TEXT,
        cluster_a_5mi TEXT,
        cluster_a_10mi TEXT,
        cluster_ab_5mi TEXT,
        cluster_ab_10mi TEXT,
        cluster_abc_5mi TEXT,
        cluster_abc_10mi TEXT,
        cluster_bc_5mi TEXT,
        cluster_bc_10mi TEXT
    )
    ''')
    
    # Load and process targets data
    targets_df = pd.read_csv('data/athletic-center-targets-2024-01-02.csv', encoding='latin1')
    
    # Clean up the data
    targets_df['Population'] = targets_df['Population'].str.replace(',', '').astype(float).astype(int)
    targets_df['Households'] = targets_df['Households'].str.replace(',', '').astype(float).astype(int)
    targets_df['Household Size'] = targets_df['Household Size'].astype(float)
    
    # Handle income with '+' symbol
    targets_df['Median HH Income'] = targets_df['Median HH Income'].str.replace('$', '').str.replace(',', '').str.replace('+', '').str.strip().astype(float).astype(int)
    
    # Add status column if it doesn't exist
    if 'status' not in targets_df.columns:
        targets_df['status'] = 'not-contacted'
    
    # Insert targets data
    for _, row in targets_df.iterrows():
        cursor.execute('''
        INSERT OR REPLACE INTO targets (
            organization, address, region, phone, website, notes, drive_radius,
            population, households, median_income, latitude, longitude, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            row['Organization'],
            row['Address'],
            row['Region'],
            row['Phone'],
            row['Website'],
            row['Notes'],
            row['Drive Radius'],
            row['Population'],
            row['Households'],
            row['Median HH Income'],
            row['Latitude'],
            row['Longitude'],
            row.get('status', 'not-contacted')
        ))
    
    # Load and process ZIP data
    zips_df = pd.read_csv('data/high-priority-ZIPs-with-clusters.csv', encoding='latin1')
    
    # Clean up the data
    zips_df['Number HH'] = zips_df['Number HH'].astype(int)
    zips_df['ZCTA5'] = zips_df['ZIP'].astype(str).str.zfill(5)
    median_income_col = [col for col in zips_df.columns if 'Median' in col][0]
    zips_df[median_income_col] = zips_df[median_income_col].astype(float)
    
    # Extract cluster information
    analysis_types = ['A_5mi', 'A_10mi', 'AB_5mi', 'AB_10mi', 'ABC_5mi', 'ABC_10mi', 'BC_5mi', 'BC_10mi']
    
    # Insert ZIP data
    for _, row in zips_df.iterrows():
        # Get cluster values for each analysis type
        cluster_values = {}
        for analysis_type in analysis_types:
            matching_cols = [col for col in zips_df.columns if analysis_type in col]
            if matching_cols:
                cluster_values[f'cluster_{analysis_type.lower()}'] = row[matching_cols[0]]
            else:
                cluster_values[f'cluster_{analysis_type.lower()}'] = None

        cursor.execute('''
        INSERT OR REPLACE INTO zip_data (
            zip_code, geographic_area, households, total_pop, median_income,
            latitude, longitude, grade,
            cluster_a_5mi, cluster_a_10mi, cluster_ab_5mi, cluster_ab_10mi,
            cluster_abc_5mi, cluster_abc_10mi, cluster_bc_5mi, cluster_bc_10mi
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            row['ZCTA5'],
            row['Geographic Area Name'],
            row['Number HH'],
            row['Total Pop'] if 'Total Pop' in row else None,
            row[median_income_col],
            row['latitude'],
            row['longitude'],
            row.get('grade', 'Ungraded'),
            cluster_values['cluster_a_5mi'],
            cluster_values['cluster_a_10mi'],
            cluster_values['cluster_ab_5mi'],
            cluster_values['cluster_ab_10mi'],
            cluster_values['cluster_abc_5mi'],
            cluster_values['cluster_abc_10mi'],
            cluster_values['cluster_bc_5mi'],
            cluster_values['cluster_bc_10mi']
        ))
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    print("Database initialized successfully!")

if __name__ == "__main__":
    init_database()
