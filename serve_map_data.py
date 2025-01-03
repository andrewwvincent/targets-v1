from flask import Flask, jsonify, send_from_directory
import sqlite3
import json
import os

app = Flask(__name__, static_folder='.', static_url_path='')

def get_db_connection():
    conn = sqlite3.connect('data/targets.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def root():
    return send_from_directory('.', 'index.html')

@app.route('/db')
def db_view():
    return send_from_directory('.', 'index_db.html')

@app.route('/api/targets')
def get_targets():
    conn = get_db_connection()
    targets = conn.execute('''
        SELECT organization, address, phone, website, population, 
               median_income, status, latitude, longitude
        FROM targets
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
    ''').fetchall()
    conn.close()
    return jsonify([dict(row) for row in targets])

@app.route('/api/zips')
def get_zips():
    conn = get_db_connection()
    zips = conn.execute('''
        SELECT zip_code, geographic_area, households, total_pop,
               median_income, grade, latitude, longitude,
               cluster_a_5mi, cluster_a_10mi, cluster_ab_5mi, 
               cluster_ab_10mi, cluster_abc_5mi, cluster_abc_10mi,
               cluster_bc_5mi, cluster_bc_10mi
        FROM zip_data
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
    ''').fetchall()
    conn.close()
    return jsonify([dict(row) for row in zips])

@app.route('/api/clusters/<analysis_type>')
def get_clusters(analysis_type):
    conn = get_db_connection()
    cluster_col = f'cluster_{analysis_type.lower()}'
    
    # Get all ZIPs that belong to clusters of this type
    query = f'''
    SELECT zip_code, latitude, longitude, {cluster_col}, 
           total_pop, median_income, grade
    FROM zip_data 
    WHERE {cluster_col} IS NOT NULL
    AND latitude IS NOT NULL AND longitude IS NOT NULL
    '''
    
    results = conn.execute(query).fetchall()
    conn.close()
    
    # Group ZIPs by cluster
    clusters = {}
    for row in results:
        cluster_name = row[cluster_col]
        if cluster_name not in clusters:
            clusters[cluster_name] = []
        clusters[cluster_name].append({
            'zip': row['zip_code'],
            'lat': row['latitude'],
            'lng': row['longitude'],
            'total_pop': row['total_pop'],
            'median_income': row['median_income'],
            'grade': row['grade']
        })
    
    return jsonify(clusters)

if __name__ == '__main__':
    app.run(port=5000)
