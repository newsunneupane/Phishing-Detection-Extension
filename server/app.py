from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
import joblib
import os
from model import predict_url, train_model, load_model
from features import extract_features

app = Flask(__name__)
CORS(app) # Allow extension to make requests

# Database configuration using Environment Variables
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASS', ''),
    'database': os.getenv('DB_NAME', 'phishing_db'),
    'port': int(os.getenv('DB_PORT', 3306))
}

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Internal server error', 'message': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    try:
        conn = get_db_connection()
        conn.ping(reconnect=True)
        conn.close()
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'env_vars': {
                'DB_HOST': 'Set' if os.getenv('DB_HOST') else 'Missing',
                'DB_USER': 'Set' if os.getenv('DB_USER') else 'Missing',
                'DB_NAME': 'Set' if os.getenv('DB_NAME') else 'Missing'
            }
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': str(e)
        }), 500

@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
            
        url = data.get('url')
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        # Normalize URL (remove trailing slash and protocol for matching)
        url_no_proto = url.replace('https://', '').replace('http://', '').rstrip('/')
        
        print(f"Checking URL (normalized): {url_no_proto}")
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Check if URL is in database (matching both http and https)
        query = """
            SELECT label FROM websites 
            WHERE url = %s OR url = %s 
            OR url = %s OR url = %s
        """
        params = (
            f"http://{url_no_proto}", f"http://{url_no_proto}/",
            f"https://{url_no_proto}", f"https://{url_no_proto}/"
        )
        cursor.execute(query, params)
        result = cursor.fetchone()
        
        if result:
            label = result['label']
            conn.close()
            print(f"URL found in database! Label: {label}")
            return jsonify({
                'url': url,
                'label': label,
                'source': 'database',
                'warning': True if label in ['phishing', 'potential phishing'] else False
            })
        
        # If not in database, use ML model
        print("URL not in database. Using ML model for prediction...")
        conn.close()
        prediction = predict_url(url)
        print(f"ML Model prediction: {prediction}")
        return jsonify({
            'url': url,
            'label': prediction,
            'source': 'ml_model',
            'warning': True if prediction == 'phishing' else False
        })
    except Exception as e:
        print(f"Error in /predict: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/feedback', methods=['POST'])
def feedback():
    data = request.json
    url = data.get('url')
    vote = data.get('vote') # 'phishing', 'potential phishing', 'legitimate'
    percentage = data.get('percentage', 0) # User's percentage vote (0-100)
    
    if not url or not vote:
        return jsonify({'error': 'URL and vote are required'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Update the websites table (or insert if not exists)
    cursor.execute("""
        INSERT INTO websites (url, label, phishing_percentage) 
        VALUES (%s, %s, %s) 
        ON DUPLICATE KEY UPDATE 
            label = VALUES(label),
            phishing_percentage = VALUES(phishing_percentage)
    """, (url, vote, percentage))
    
    # 2. Log user vote to reports table
    cursor.execute("INSERT INTO reports (url, vote, percentage) VALUES (%s, %s, %s)", (url, vote, percentage))
    conn.commit()
    
    # 3. Check for model retraining (after 100 new phishing reports)
    cursor.execute("SELECT COUNT(*) FROM reports WHERE is_trained = FALSE AND vote IN ('phishing', 'potential phishing')")
    new_reports_count = cursor.fetchone()[0]
    
    if new_reports_count >= 100:
        print(f"Triggering model retraining with {new_reports_count} new reports...")
        retrain_model_from_db()
        
        # Mark reports as trained
        cursor.execute("UPDATE reports SET is_trained = TRUE WHERE is_trained = FALSE")
        conn.commit()
    
    conn.close()
    return jsonify({'message': 'Feedback received. Thank you!', 'retrain_triggered': new_reports_count >= 100})

def retrain_model_from_db():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Fetch all websites with labels for retraining
    cursor.execute("SELECT url, label FROM websites")
    rows = cursor.fetchall()
    conn.close()
    
    # Format data for training
    training_data = []
    for row in rows:
        # Convert enum to binary label (1 for phishing/potential, 0 for legitimate)
        label_val = 1 if row['label'] in ['phishing', 'potential phishing'] else 0
        training_data.append({'url': row['url'], 'label': label_val})
    
    # Retrain
    train_model(training_data)

if __name__ == '__main__':
    # Initial model training if it doesn't exist
    model = load_model()
    if model is None:
        print("No model found locally or on S3. Performing initial training...")
        try:
            retrain_model_from_db()
        except Exception as e:
            print(f"Initial training failed: {e}. Ensure MySQL is running.")
            
    app.run(host='127.0.0.1', port=5001, debug=True)
