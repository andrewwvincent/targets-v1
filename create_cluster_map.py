import pandas as pd
import numpy as np
from scipy.spatial import ConvexHull
import folium
from folium.plugins import GroupedLayerControl, MarkerCluster

def load_cluster_data():
    """Load cluster data from CSV files"""
    print("Loading data...")
    
    try:
        # Load the main data file
        df = pd.read_csv('data/high-priority-ZIPs-with-clusters.csv')
        df['ZCTA5'] = df['ZIP'].astype(str).str.zfill(5)
        
        # Initialize clusters dictionary
        clusters = {}
        
        # Define the cluster analysis types we want to track
        analysis_types = ['A_5mi', 'A_10mi', 'AB_5mi', 'AB_10mi', 'ABC_5mi', 'ABC_10mi', 'BC_5mi', 'BC_10mi']
        
        # For each analysis type, extract its clusters
        for analysis_type in analysis_types:
            # Get all columns that contain this analysis type
            matching_cols = [col for col in df.columns if analysis_type in col]
            if matching_cols:
                # Use the first matching column (there should only be one)
                cluster_col = matching_cols[0]
                # Create a copy of the data with only rows that have a cluster for this analysis
                analysis_df = df[df[cluster_col].notna()].copy()
                
                # Extract just the cluster number from the value (e.g., "A_5mi_C1" -> "1")
                analysis_df['cluster'] = analysis_df[cluster_col].str.extract(r'C(\d+)$')
                
                # Store cluster data
                if not analysis_df.empty:
                    clusters[analysis_type] = analysis_df[['ZCTA5', 'latitude', 'longitude', 'cluster', 'Total Pop', 'Median Income']]
                    print(f"Found {len(analysis_df)} ZIPs in {analysis_type} clusters")
        
        # Fill missing values
        df['Total Pop'] = df['Total Pop'].fillna(0)
        df['Median Income'] = df['Median Income'].fillna(0)
        
        return df, clusters
    except Exception as e:
        print(f"Error loading data: {str(e)}")
        raise

def create_convex_hull(points):
    """Create a convex hull from a set of points"""
    if len(points) < 3:
        return points
    hull = ConvexHull(points)
    return [points[i] for i in hull.vertices]

def create_cluster_map(all_zips, cluster_data):
    """Create an interactive map with cluster boundaries and ZIP points"""
    # Create base map centered on US
    m = folium.Map(location=[39.8283, -98.5795], zoom_start=4)
    
    # Define colors for different analyses
    cluster_colors = {
        'A_5mi': '#2ECC40',    # Green
        'A_10mi': '#3D9970',   # Dark Green
        'AB_5mi': '#0074D9',   # Blue
        'AB_10mi': '#001f3f',  # Dark Blue
        'ABC_5mi': '#FFDC00',  # Yellow
        'ABC_10mi': '#FF851B', # Orange
        'BC_5mi': '#B10DC9',   # Purple
        'BC_10mi': '#85144b'   # Maroon
    }
    
    # Define colors for ZIP grades
    grade_colors = {
        'A': '#2ECC40',  # Green
        'B': '#0074D9',  # Blue
        'C': '#FFDC00',  # Yellow
        'D': '#FF851B',  # Orange
        'F': '#FF4136',  # Red
        'Ungraded': '#AAAAAA'  # Gray
    }

    # Create feature groups for ZIP grades with clustering
    grade_groups = {}
    for grade in grade_colors.keys():
        group = folium.FeatureGroup(name=f'Grade {grade}', show=False)
        marker_cluster = MarkerCluster().add_to(group)
        grade_groups[grade] = {'group': group, 'cluster': marker_cluster}
        m.add_child(group)
    
    # Add ZIP points to appropriate grade groups
    for _, row in all_zips.iterrows():
        # Skip if coordinates are missing
        if pd.isna(row['latitude']) or pd.isna(row['longitude']):
            continue
            
        grade = row['grade']
        popup_html = f"""
        <b>ZIP: {row['ZCTA5']}</b><br>
        Grade: {grade}<br>
        Population: {row['Total Pop']:,.0f}<br>
        Income: ${float(str(row['Median Income']).replace('+', '').replace(',', '')):,.0f}<br>
        Families with Children: {row['Families with Children <18']:,.0f}
        """
        
        folium.CircleMarker(
            location=[row['latitude'], row['longitude']],
            radius=3,
            color='black',  # Stroke color
            weight=1,      # Stroke width
            fill=True,
            fillColor=grade_colors[grade],
            fillOpacity=0.7,
            popup=popup_html,
            opacity=1
        ).add_to(grade_groups[grade]['cluster'])
    
    # Load athletic centers data
    athletic_centers = pd.read_csv('data/athletic-center-targets-2024-01-02.csv')
    athletic_centers['Population'] = pd.to_numeric(athletic_centers['Population'].str.replace(',', ''), errors='coerce')
    athletic_centers['Median HH Income'] = pd.to_numeric(athletic_centers['Median HH Income'].str.replace('$', '').str.replace(',', ''), errors='coerce')
    
    # Create legend
    legend_html = '''
    <div style="position: fixed; bottom: 50px; left: 50px; z-index: 1000; 
         background-color: white; padding: 10px; border: 2px solid grey; border-radius: 5px">
    <h4>Legend</h4>
    <h5>Cluster Types</h5>
    '''
    for name, color in cluster_colors.items():
        legend_html += f'<p><i class="fa fa-square fa-1x" style="color:{color}"></i> {name}</p>'
    legend_html += '<h5>ZIP Grades</h5>'
    for grade, color in grade_colors.items():
        legend_html += f'<p><i class="fa fa-circle fa-1x" style="color:{color}"></i> Grade {grade}</p>'
    legend_html += '<h5>Categories</h5>'
    legend_html += '<p><i class="fa fa-map-marker fa-1x" style="color:#FF0000"></i> Athletic Centers</p>'
    legend_html += '</div>'
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Create cluster groups
    cluster_groups = {}
    for analysis_name, df in cluster_data.items():
        show_layer = analysis_name == 'A_10mi'
        group = folium.FeatureGroup(name=analysis_name, show=show_layer)
        cluster_groups[analysis_name] = group
        
        # Process each cluster in this analysis
        for cluster_id in df['cluster'].unique():
            if pd.isna(cluster_id):
                print(f"Skipping null cluster ID in {analysis_name}")
                continue
                
            cluster_df = df[df['cluster'] == cluster_id]
            print(f"\nCluster {cluster_id} in {analysis_name}:")
            print(f"Number of ZIPs: {len(cluster_df)}")
            
            # Get coordinates for cluster
            coords = cluster_df[['latitude', 'longitude']].values
            print(f"Number of coordinates: {len(coords)}")
            
            # Create convex hull for cluster boundary
            if len(coords) >= 3:
                hull_points = create_convex_hull(coords)
                print(f"Number of hull points: {len(hull_points)}")
                
                # Calculate cluster center for label
                center = np.mean(coords, axis=0)
                
                # Create popup content
                popup_html = f"""
                <b>Cluster Information</b><br>
                Analysis: {analysis_name}<br>
                Cluster ID: {cluster_id}<br>
                Number of ZIPs: {len(cluster_df)}<br>
                Total Population: {cluster_df['Total Pop'].sum():,.0f}<br>
                Avg Income: ${cluster_df['Median Income'].mean():,.0f}
                """
                
                # Draw polygon for cluster boundary
                folium.Polygon(
                    locations=[[p[0], p[1]] for p in hull_points],
                    color=cluster_colors[analysis_name],
                    weight=2,
                    fill=True,
                    fillColor=cluster_colors[analysis_name],
                    fillOpacity=0.2,
                    popup=popup_html
                ).add_to(group)
        
        # Add group to map after all polygons are added
        m.add_child(group)

    # Create athletic centers group with clustering
    athletic_centers_group = folium.FeatureGroup(name='Athletic Centers', show=True)
    athletic_centers_cluster = MarkerCluster().add_to(athletic_centers_group)
    m.add_child(athletic_centers_group)

    # Add athletic centers to map
    for _, row in athletic_centers.iterrows():
        # Skip if coordinates are missing
        if pd.isna(row['Latitude']) or pd.isna(row['Longitude']):
            continue
            
        popup_html = f"""
        <b>{row['Organization']}</b><br>
        Address: {row['Address']}<br>
        Phone: {row['Phone']}<br>
        Website: <a href="{row['Website']}" target="_blank">{row['Website']}</a><br>
        Population: {row['Population']:,.0f}<br>
        Median HH Income: ${row['Median HH Income']:,.0f}
        """
        
        folium.Marker(
            location=[row['Latitude'], row['Longitude']],
            popup=popup_html,
            icon=folium.Icon(color='red', icon='info-sign')
        ).add_to(athletic_centers_cluster)
    
    # Add layer control (hidden but functional)
    folium.LayerControl(
        position='topright',
        collapsed=True,
        overlay=True
    ).add_to(m)
    
    # Add custom control panel HTML
    custom_control_html = """
    <div class='custom-control' style='position: fixed; top: 10px; right: 50px; z-index: 1000; background: white; padding: 10px; border: 2px solid grey; border-radius: 5px'>
        <div>
            <h4>Map Controls</h4>
            <div id='custom-zip-controls'>
                <label>
                    <input type='checkbox' class='parent-toggle' data-group='zip'/> ZIP Codes
                </label>
                <div style='margin-left: 20px;'>
    """
    
    for grade in grade_colors.keys():
        custom_control_html += f"""
            <label>
                <input type='checkbox' class='custom-toggle zip-toggle' data-layer='Grade {grade}'/> Grade {grade}
            </label><br>
        """
    
    custom_control_html += """
                </div>
            </div>
            <div id='custom-cluster-controls' style='margin-top: 10px;'>
                <label>
                    <input type='checkbox' checked class='parent-toggle' data-group='cluster'/> Clusters
                </label>
                <div style='margin-left: 20px;'>
    """
    
    for name in cluster_colors.keys():
        is_a_10mi = 'checked' if name == 'A_10mi' else ''
        custom_control_html += f"""
            <label>
                <input type='checkbox' {is_a_10mi} class='custom-toggle cluster-toggle' data-layer='{name}'/> {name}
            </label><br>
        """
    
    custom_control_html += """
                </div>
            </div>
            <div id='custom-category-controls' style='margin-top: 10px;'>
                <label>
                    <input type='checkbox' checked class='parent-toggle' data-group='category'/> All Categories
                </label>
                <div style='margin-left: 20px;'>
                    <label>
                        <input type='checkbox' checked class='custom-toggle category-toggle' data-layer='Athletic Centers'/> Athletic Centers
                    </label><br>
                </div>
            </div>
        </div>
    </div>
    """
    
    # Add JavaScript for custom controls
    custom_control_js = """
    <script>
    document.addEventListener('DOMContentLoaded', function() {
        // Function to find Leaflet checkbox by layer name
        function findLeafletCheckbox(layerName) {
            var labels = document.querySelectorAll('.leaflet-control-layers-overlays label');
            for (var i = 0; i < labels.length; i++) {
                if (labels[i].textContent.trim() === layerName) {
                    return labels[i].querySelector('input[type="checkbox"]');
                }
            }
            return null;
        }
        
        // Function to update parent checkbox state
        function updateParentState(groupName) {
            var children = document.getElementsByClassName(groupName + '-toggle');
            var parent = document.querySelector('.parent-toggle[data-group="' + groupName + '"]');
            
            var allChecked = true;
            var allUnchecked = true;
            
            for (var i = 0; i < children.length; i++) {
                if (children[i].checked) {
                    allUnchecked = false;
                } else {
                    allChecked = false;
                }
            }
            
            if (allChecked) {
                parent.checked = true;
                parent.indeterminate = false;
            } else if (allUnchecked) {
                parent.checked = false;
                parent.indeterminate = false;
            } else {
                parent.checked = false;
                parent.indeterminate = true;
            }
        }
        
        // Add click handlers to custom toggles
        var customToggles = document.getElementsByClassName('custom-toggle');
        for (var i = 0; i < customToggles.length; i++) {
            customToggles[i].addEventListener('change', function(e) {
                var layerName = e.target.dataset.layer;
                var leafletCheckbox = findLeafletCheckbox(layerName);
                if (leafletCheckbox) {
                    leafletCheckbox.click();  // Simulate click on Leaflet checkbox
                }
                
                // Update parent state
                if (this.classList.contains('zip-toggle')) {
                    updateParentState('zip');
                } else if (this.classList.contains('cluster-toggle')) {
                    updateParentState('cluster');
                } else if (this.classList.contains('category-toggle')) {
                    updateParentState('category');
                }
            });
        }
        
        // Add click handlers to parent toggles
        var parentToggles = document.getElementsByClassName('parent-toggle');
        for (var i = 0; i < parentToggles.length; i++) {
            parentToggles[i].addEventListener('change', function(e) {
                var groupName = this.dataset.group;
                var children = document.getElementsByClassName(groupName + '-toggle');
                var targetState = this.checked;
                
                // First update all custom checkboxes
                for (var j = 0; j < children.length; j++) {
                    children[j].checked = targetState;
                }
                
                // Then trigger all needed Leaflet checkbox changes at once
                for (var j = 0; j < children.length; j++) {
                    var layerName = children[j].dataset.layer;
                    var leafletCheckbox = findLeafletCheckbox(layerName);
                    if (leafletCheckbox && leafletCheckbox.checked !== targetState) {
                        leafletCheckbox.click();
                    }
                }
                
                // Clear indeterminate state
                this.indeterminate = false;
            });
        }
        
        // Function to sync Leaflet checkbox states to custom checkboxes
        function syncCheckboxStates() {
            var customToggles = document.getElementsByClassName('custom-toggle');
            for (var i = 0; i < customToggles.length; i++) {
                var layerName = customToggles[i].dataset.layer;
                var leafletCheckbox = findLeafletCheckbox(layerName);
                if (leafletCheckbox) {
                    customToggles[i].checked = leafletCheckbox.checked;
                }
            }
            
            // Update parent states
            updateParentState('zip');
            updateParentState('cluster');
            updateParentState('category');
        }
        
        // Add mutation observer to sync states when Leaflet checkboxes change
        var layerControl = document.querySelector('.leaflet-control-layers-overlays');
        if (layerControl) {
            var observer = new MutationObserver(syncCheckboxStates);
            observer.observe(layerControl, { 
                attributes: true, 
                childList: true, 
                subtree: true 
            });
        }
        
        // Initial parent state update
        updateParentState('zip');
        updateParentState('cluster');
        updateParentState('category');
    });
    </script>
    """
    
    # Add custom elements to map
    m.get_root().html.add_child(folium.Element(custom_control_html))
    m.get_root().html.add_child(folium.Element(custom_control_js))
    
    return m

def main():
    print("Loading data...")
    all_zips, cluster_data = load_cluster_data()
    
    print("Creating map...")
    m = create_cluster_map(all_zips, cluster_data)
    
    print("Saving map...")
    m.save('index.html')
    print("Done! Open index.html to view the map")

if __name__ == "__main__":
    main()
