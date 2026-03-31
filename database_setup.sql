-- Database for Phishing Site Detection
CREATE DATABASE IF NOT EXISTS phishing_db;
USE phishing_db;

-- Table to store URLs and their labels
CREATE TABLE IF NOT EXISTS websites (
    id INT AUTO_INCREMENT PRIMARY KEY,
    url VARCHAR(255) UNIQUE NOT NULL,
    label ENUM('phishing', 'potential phishing', 'legitimate') NOT NULL,
    phishing_percentage INT DEFAULT 0, -- Store user's percentage vote (0-100)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Table to track user reports/votes for model retraining
CREATE TABLE IF NOT EXISTS reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    url VARCHAR(255) NOT NULL,
    vote ENUM('phishing', 'potential phishing', 'legitimate') NOT NULL,
    percentage INT DEFAULT 0, -- Store user's percentage vote (0-100)
    is_trained BOOLEAN DEFAULT FALSE, -- Track if this report has been used in model training
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table to store the ML Model binary
CREATE TABLE IF NOT EXISTS ml_models (
    id INT AUTO_INCREMENT PRIMARY KEY,
    model_data LONGBLOB NOT NULL,
    version INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed data for testing (optional)
INSERT IGNORE INTO websites (url, label) VALUES 
('https://www.google.com', 'legitimate'),
('https://www.github.com', 'legitimate'),
('http://example.com', 'phishing'),
('http://bad-login-update-bank.com', 'phishing'),
('http://192.168.1.1/secure', 'phishing');
