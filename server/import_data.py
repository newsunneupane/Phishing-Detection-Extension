import pickle
import mysql.connector
import os

# Database configuration (matching app.py)
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'phishing_db'
}

def import_from_pickle(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found.")
        return

    try:
        with open(file_path, 'rb') as f:
            data = pickle.load(f)
        
        # Expected data format: list of dicts like [{'url': '...', 'label': '...'}, ...]
        # or a dictionary mapping {url: label}
        
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        count = 0
        if isinstance(data, list):
            for item in data:
                url = item.get('url')
                label = item.get('label')
                if url and label:
                    cursor.execute("""
                        INSERT IGNORE INTO websites (url, label) 
                        VALUES (%s, %s)
                    """, (url, label))
                    count += 1
        elif isinstance(data, dict):
            for url, label in data.items():
                cursor.execute("""
                    INSERT IGNORE INTO websites (url, label) 
                    VALUES (%s, %s)
                """, (url, label))
                count += 1
        
        conn.commit()
        conn.close()
        print(f"Successfully imported {count} sites from {file_path}")
        
    except Exception as e:
        print(f"Error importing from pickle: {e}")

if __name__ == "__main__":
    # You can change the filename here if needed
    import_from_pickle('sites_data.pkl')
