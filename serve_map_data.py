from flask import Flask, send_from_directory, jsonify, request
import os
import sqlite3

app = Flask(__name__, static_folder='.', static_url_path='')

def get_db_connection():
    conn = sqlite3.connect('data/targets.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def root():
    return send_from_directory('.', 'index_db.html')

@app.route('/index_db.html')
def index_db():
    return send_from_directory('.', 'index_db.html')

@app.route('/kanban.html')
def kanban():
    return send_from_directory('.', 'kanban.html')

@app.route('/api/targets')
def get_targets():
    conn = get_db_connection()
    try:
        targets = conn.execute('''
            SELECT t.organization, t.address, t.phone, t.website, t.population, 
                   t.median_income, t.status, t.latitude, t.longitude,
                   z.grade
            FROM targets t
            LEFT JOIN zip_data z ON t.region = z.zip_code
            WHERE t.latitude IS NOT NULL AND t.longitude IS NOT NULL
        ''').fetchall()
        return jsonify([dict(row) for row in targets])
    except Exception as e:
        print(f"Error getting targets: {e}")
        return str(e), 500
    finally:
        conn.close()

@app.route('/api/kanban_data')
def get_kanban_data():
    conn = get_db_connection()
    try:
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
        return jsonify(targets)
    except Exception as e:
        print(f"Error getting kanban data: {e}")
        return str(e), 500
    finally:
        conn.close()

@app.route('/api/update_status', methods=['POST'])
def update_status():
    data = request.json
    organization = data.get('organization')
    new_status = data.get('status')
    
    if not organization or not new_status:
        return jsonify({'error': 'Missing organization or status'}), 400

    conn = get_db_connection()
    try:
        # Get current status
        current = conn.execute(
            'SELECT status FROM targets WHERE organization = ?',
            (organization,)
        ).fetchone()
        
        if not current:
            return jsonify({'error': 'Organization not found'}), 404
        
        old_status = current[0]
        
        # Update status
        conn.execute('''
            UPDATE targets 
            SET status = ?, last_updated = CURRENT_TIMESTAMP 
            WHERE organization = ?
        ''', (new_status, organization))
        
        # Log the change
        conn.execute('''
            INSERT INTO activity_log (organization, old_status, new_status)
            VALUES (?, ?, ?)
        ''', (organization, old_status, new_status))
        
        conn.commit()
        print(f"Updated status for {organization}: {old_status} -> {new_status}")
        return jsonify({'success': True, 'old_status': old_status, 'new_status': new_status})
    
    except Exception as e:
        conn.rollback()
        print(f"Error updating status: {e}")
        return str(e), 500
    finally:
        conn.close()

@app.route('/api/zips')
def get_zips():
    conn = get_db_connection()
    try:
        zips = conn.execute('''
            SELECT zip_code, geographic_area, households, total_pop,
                   median_income, grade, latitude, longitude,
                   cluster_a_5mi, cluster_a_10mi, cluster_ab_5mi, 
                   cluster_ab_10mi, cluster_abc_5mi, cluster_abc_10mi,
                   cluster_bc_5mi, cluster_bc_10mi
            FROM zip_data
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        ''').fetchall()
        print(f"Retrieved {len([dict(row) for row in zips])} ZIP codes")
        return jsonify([dict(row) for row in zips])
    except Exception as e:
        print(f"Error getting ZIP data: {e}")
        return str(e), 500
    finally:
        conn.close()

@app.route('/api/clusters/<analysis_type>')
def get_clusters(analysis_type):
    conn = get_db_connection()
    try:
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
        
        print(f"Retrieved {len(clusters)} clusters for analysis type {analysis_type}")
        return jsonify(clusters)
    except Exception as e:
        print(f"Error getting clusters: {e}")
        return str(e), 500
    finally:
        conn.close()

if __name__ == '__main__':
    print("Starting test server...")
    print(f"Current directory: {os.getcwd()}")
    print(f"index_db.html exists: {os.path.exists('index_db.html')}")
    print(f"kanban.html exists: {os.path.exists('kanban.html')}")
    
    # Test database connection
    try:
        conn = get_db_connection()
        print("Database connection successful")
        print("Tables:", [t[0] for t in conn.execute('SELECT name FROM sqlite_master WHERE type="table"').fetchall()])
        conn.close()
    except Exception as e:
        print(f"Database connection error: {e}")
    
    app.run(debug=True, port=5000)
