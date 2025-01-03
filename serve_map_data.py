import os
import signal
import psutil
import sys
import json
from flask import Flask, jsonify, send_from_directory, request
import sqlite3

def kill_existing_process():
    # Kill any Python processes running on port 5000
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Check if it's a Python process
            if proc.info['name'] and 'python' in proc.info['name'].lower():
                cmdline = proc.info.get('cmdline', [])
                # Check if it's running our server file
                if any('serve_map_data.py' in cmd for cmd in cmdline if cmd):
                    print(f"Killing existing Flask process: {proc.info['pid']}")
                    proc.kill()
                    proc.wait()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    # Save current PID
    with open('flask_server.pid', 'w') as f:
        f.write(str(os.getpid()))

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
        SELECT t.organization, t.address, t.phone, t.website, t.population, 
               t.median_income, t.status, t.latitude, t.longitude,
               z.grade
        FROM targets t
        LEFT JOIN zip_data z ON t.region = z.zip_code
        WHERE t.latitude IS NOT NULL AND t.longitude IS NOT NULL
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

@app.route('/api/kanban_data')
def get_kanban_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            t.organization,
            t.address,
            t.phone,
            COALESCE(t.status, 'not-contacted') as status,
            t.population,
            t.median_income,
            z.grade
        FROM targets t
        LEFT JOIN zip_data z ON t.region = z.zip_code
    ''')
    
    targets = []
    for row in cursor.fetchall():
        targets.append({
            'organization': row[0],
            'address': row[1],
            'phone': row[2] if row[2] else 'N/A',
            'status': row[3],
            'population': row[4],
            'median_income': row[5],
            'zip_grade': row[6] if row[6] else 'N/A'
        })
    
    conn.close()
    return jsonify(targets)

@app.route('/api/update_status', methods=['POST'])
def update_status():
    data = request.json
    organization = data.get('organization')
    new_status = data.get('status').replace(' ', '-')  # Convert spaces to hyphens
    
    if not organization or not new_status:
        return jsonify({'error': 'Missing required fields'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            UPDATE targets 
            SET status = ? 
            WHERE organization = ?
        ''', (new_status, organization))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    try:
        kill_existing_process()
        print("Starting Flask server...")
        # Set Flask environment variables
        os.environ['FLASK_ENV'] = 'development'
        os.environ['FLASK_DEBUG'] = '1'
        # Basic configuration
        app.config.update(
            DEBUG=True,
            TEMPLATES_AUTO_RELOAD=True
        )
        app.run(port=5000)
    except Exception as e:
        print(f"Error starting server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
