# Database Configuration - SQL Server
DB_CONFIG = {
    'server': '192.168.10.168,1433',   # Use IP + instance name
    'database': 'QualityControlDB',
    'driver': '{ODBC Driver 17 for SQL Server}',
    'trusted_connection': False,              # Use SQL login instead
    'username': 'sa',                         # The sa account you enabled
    'password': 'P@kistan123'                 # The password you set
}

# App Configuration
APP_CONFIG = {
    'app_name': 'Quality Control System',
    'version': '2.0',
    'company': 'Professional Solutions',
    'theme_colors': {
        'primary': '#2196F3',
        'secondary': '#607D8B',
        'success': '#4CAF50',
        'danger': '#F44336',
        'warning': '#FF9800',
        'dark': '#1A1A1A',
        'light': '#F5F5F5',
        'gray': '#9E9E9E'
    }
}

# Roles and Permissions
ROLES = {
    'admin': ['view_dashboard', 'manage_products', 'manage_inspections', 
              'manage_users', 'view_reports', 'export_data', 'delete_data'],
    'inspector': ['view_dashboard', 'manage_inspections', 'view_products', 'view_reports'],
    'viewer': ['view_dashboard', 'view_products', 'view_reports']
}
