import sqlite3
import pandas as pd

def verify_database():
    conn = sqlite3.connect('data/targets.db')
    
    # Check targets table
    targets_df = pd.read_sql_query("SELECT * FROM targets", conn)
    print("\nTargets Table Summary:")
    print(f"Total rows: {len(targets_df)}")
    print(f"Missing coordinates: {len(targets_df[targets_df['latitude'].isna() | targets_df['longitude'].isna()])}")
    print("\nSample of targets data:")
    print(targets_df.head().to_string())
    
    # Check zip_data table
    zips_df = pd.read_sql_query("SELECT * FROM zip_data", conn)
    print("\nZIP Data Table Summary:")
    print(f"Total rows: {len(zips_df)}")
    print(f"Missing coordinates: {len(zips_df[zips_df['latitude'].isna() | zips_df['longitude'].isna()])}")
    print("\nSample of ZIP data:")
    print(zips_df.head().to_string())
    
    conn.close()

if __name__ == "__main__":
    verify_database()
