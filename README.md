# ZIP Code Cluster Analysis v1.0

This project provides tools for analyzing and visualizing ZIP code clusters based on various demographic and economic factors. It creates an interactive web map showing ZIP codes, their grades (A-F), and cluster boundaries for different analysis types.

## Features

- Interactive map with multiple layers:
  - ZIP codes colored by grade (A-F)
  - Cluster boundaries for different analyses (A_5mi, A_10mi, AB_5mi, etc.)
  - Athletic center locations
  - Layer controls for toggling visibility
- Detailed popups with demographic information
- Convex hull generation for cluster boundaries
- Multiple analysis types supported (5mi and 10mi radii)

## Setup

1. Install required Python packages:
```bash
pip install pandas numpy scipy folium
```

2. Place your data files in the `data` directory:
- high-priority-ZIPs-with-clusters.csv
- athletic-center-targets-2024-01-02.csv

## Usage

Run the map generation script:
```bash
python create_cluster_map.py
```

This will create an `index.html` file that you can open in any web browser to view the interactive map.

## Data Structure

The project expects CSV files with the following structure:

### high-priority-ZIPs-with-clusters.csv
- ZIP: ZIP code
- latitude/longitude: Coordinates
- grade: ZIP grade (A-F)
- Total Pop: Population
- Median Income: Median household income
- Cluster columns (e.g., A_5mi_C1): Cluster assignments

### athletic-center-targets-2024-01-02.csv
- Location information for athletic centers
- Population and demographic data

## Version History

- v1.0 (2025-01-02): Initial release with cluster mapping functionality
