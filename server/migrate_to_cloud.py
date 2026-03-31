import pymysql
import pymysql.cursors
import os

# --- LOCAL XAMPP CONFIG ---
LOCAL_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'phishing_db',
    'cursorclass': pymysql.cursors.DictCursor
}

# --- CLOUD DB CONFIG (Fill these in via environment variables!) ---
CLOUD_CONFIG = {
    'host': os.getenv('DB_HOST', 'YOUR_AIVEN_HOST'),
    'user': os.getenv('DB_USER', 'avnadmin'),
    'password': os.getenv('DB_PASS', 'YOUR_AIVEN_PASSWORD'),
    'database': os.getenv('DB_NAME', 'defaultdb'), 
    'port': int(os.getenv('DB_PORT', 24015)) 
}

def migrate():
    try:
        # 1. Connect to Local
        print("Connecting to local XAMPP...")
        local_conn = pymysql.connect(**LOCAL_CONFIG)
        
        # 2. Connect to Cloud
        print("Connecting to Cloud Database...")
        cloud_conn = pymysql.connect(**CLOUD_CONFIG)

        with cloud_conn.cursor() as cloud_cursor, local_conn.cursor() as local_cursor:
            # 3. Create tables in Cloud if they don't exist
            print("Creating tables in Cloud...")
            cloud_cursor.execute("""
                CREATE TABLE IF NOT EXISTS websites (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    url VARCHAR(255) UNIQUE NOT NULL,
                    label ENUM('phishing', 'potential phishing', 'legitimate') NOT NULL,
                    phishing_percentage INT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """)
            cloud_cursor.execute("""
                CREATE TABLE IF NOT EXISTS reports (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    url VARCHAR(255) NOT NULL,
                    vote ENUM('phishing', 'potential phishing', 'legitimate') NOT NULL,
                    percentage INT DEFAULT 0,
                    is_trained BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cloud_cursor.execute("""
                CREATE TABLE IF NOT EXISTS ml_models (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    model_data LONGBLOB NOT NULL,
                    version INT DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 4. Fetch from Local
            local_cursor.execute("SELECT * FROM websites")
            rows = local_cursor.fetchall()
            
            # 5. Insert into Cloud
            print(f"Migrating {len(rows)} records...")
            for row in rows:
                cloud_cursor.execute("""
                    INSERT IGNORE INTO websites (url, label, phishing_percentage)
                    VALUES (%s, %s, %s)
                """, (row['url'], row['label'], row['phishing_percentage']))
            
            cloud_conn.commit()
            print("Migration Successful!")
        
        local_conn.close()
        cloud_conn.close()

    except Exception as e:
        print(f"Migration Failed: {e}")

if __name__ == "__main__":
    migrate()
