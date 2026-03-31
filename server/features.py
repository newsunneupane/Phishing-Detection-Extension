import re
import urllib.parse

def extract_features(url):
    features = {}
    
    # 1. URL Length
    features['url_length'] = len(url)
    
    # 2. Presence of @ symbol
    features['has_at_symbol'] = 1 if '@' in url else 0
    
    # 3. Presence of IP address
    ip_pattern = r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'
    features['is_ip'] = 1 if re.search(ip_pattern, url) else 0
    
    # 4. Number of dots
    features['num_dots'] = url.count('.')
    
    # 5. Number of hyphens
    features['num_hyphens'] = url.count('-')
    
    # 6. Presence of "https"
    features['is_https'] = 1 if url.startswith('https') else 0
    
    # 7. Sensitive keywords in URL
    keywords = ['login', 'update', 'bank', 'secure', 'account', 'verify', 'signin']
    features['has_sensitive_keyword'] = 1 if any(k in url.lower() for k in keywords) else 0
    
    # 8. Number of subdomains
    parsed_url = urllib.parse.urlparse(url)
    domain = parsed_url.netloc
    features['num_subdomains'] = domain.count('.') - 1 if domain.count('.') > 1 else 0
    
    # 9. URL contains a dash in the domain
    features['domain_has_dash'] = 1 if '-' in domain else 0

    return features

if __name__ == "__main__":
    # Test
    test_url = "http://secure-login-bank.com/update"
    print(extract_features(test_url))
