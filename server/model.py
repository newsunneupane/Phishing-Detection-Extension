import os
import joblib
import io
import mysql.connector
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from features import extract_features

MODEL_PATH = 'phishing_model.joblib'

# Reuse DB config from environment or defaults
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASS', ''),
        database=os.getenv('DB_NAME', 'phishing_db'),
        port=int(os.getenv('DB_PORT', 3306))
    )

def train_model(data):
    """
    Trains a Random Forest classifier and saves it to the Database.
    """
    if not data:
        print("No data available to train model.")
        return None
    
    # Feature extraction
    features_list = []
    labels = []
    for entry in data:
        features = extract_features(entry['url'])
        features_list.append(list(features.values()))
        labels.append(entry['label'])
    
    # Create NumPy array instead of DataFrame to save memory/space
    X = np.array(features_list)
    y = np.array(labels)
    
    # Train Random Forest model
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X, y)
    
    # 1. Save model locally
    joblib.dump(model, MODEL_PATH)
    print(f"Model saved locally to {MODEL_PATH}")

    # 2. Save model to Database
    try:
        buffer = io.BytesIO()
        joblib.dump(model, buffer)
        binary_model = buffer.getvalue()

        conn = get_db_connection()
        cursor = conn.cursor()
        # Insert as a new version
        cursor.execute("INSERT INTO ml_models (model_data) VALUES (%s)", (binary_model,))
        conn.commit()
        conn.close()
        print("Model successfully uploaded to Database table 'ml_models'.")
    except Exception as e:
        print(f"Failed to save model to DB: {e}")

    return model

def load_model():
    # 1. Try loading from Database first
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Check if table exists first (to prevent crash on fresh DB)
        cursor.execute("SHOW TABLES LIKE 'ml_models'")
        if not cursor.fetchone():
            print("Table 'ml_models' does not exist yet.")
            conn.close()
            return None
            
        # Get the latest model version
        cursor.execute("SELECT model_data FROM ml_models ORDER BY created_at DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()

        if row:
            print("Loading latest model from Database...")
            buffer = io.BytesIO(row[0])
            return joblib.load(buffer)
    except Exception as e:
        print(f"Failed to load model from DB: {e}. Falling back to local.")

    # 2. Fallback to local file
    try:
        if os.path.exists(MODEL_PATH):
            return joblib.load(MODEL_PATH)
    except:
        pass
    
    return None

def predict_url(url, model=None):
    if model is None:
        model = load_model()
    
    if model is None:
        print("Model not found.")
        return "legitimate" # Default to safe if model missing
    
    features = extract_features(url)
    # Use NumPy array for prediction instead of DataFrame
    features_array = np.array([list(features.values())])
    
    prediction = model.predict(features_array)[0]
    return "phishing" if prediction == 1 else "legitimate"

if __name__ == "__main__":
    # Test data
    sample_data = [
        {'url': 'http://secure-bank-login.com/update', 'label': 1},
        {'url': 'http://legit-site.org/index.html', 'label': 0},
        {'url': 'https://www.google.com', 'label': 0},
        {'url': 'http://192.168.1.1/admin', 'label': 1}
    ]
    
    # Train
    train_model(sample_data)
    
    # Predict
    test_url = "http://bad-site-with-at@phishing.net"
    result = predict_url(test_url)
    print(f"Prediction for {test_url}: {result}")
