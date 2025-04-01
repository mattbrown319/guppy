import os
import requests
import base64
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def test_jira_connection():
    # Get credentials from environment variables
    email = os.getenv("JIRA_EMAIL")
    api_token = os.getenv("JIRA_API_TOKEN")
    domain = os.getenv("JIRA_DOMAIN")
    
    # Print diagnostic information
    print(f"Testing JIRA connection with:")
    print(f"  Email: {email}")
    print(f"  Domain: {domain}")
    print(f"  API Token: {api_token[:5]}...{api_token[-5:] if api_token else ''}")
    
    # Ensure domain doesn't have trailing slash
    if domain and domain.endswith('/'):
        domain = domain.rstrip('/')
    
    # Create Basic Auth header
    auth_string = f"{email}:{api_token}"
    auth_bytes = auth_string.encode('ascii')
    base64_bytes = base64.b64encode(auth_bytes)
    base64_auth = base64_bytes.decode('ascii')
    
    headers = {
        "Accept": "application/json",
        "Authorization": f"Basic {base64_auth}"
    }
    
    # Try different API endpoints to see which works
    api_versions = ["2", "3"]
    base_url_formats = [
        "https://{domain}/rest/api/{version}",
        "https://{domain}.atlassian.net/rest/api/{version}"
    ]
    
    for base_url_fmt in base_url_formats:
        for version in api_versions:
            base_url = base_url_fmt.format(domain=domain, version=version)
            
            # First try a simple endpoint like myself (current user)
            user_url = f"{base_url}/myself"
            print(f"\nTrying connection to: {user_url}")
            
            try:
                response = requests.get(
                    user_url,
                    headers=headers
                )
                
                print(f"Status code: {response.status_code}")
                
                if response.status_code == 200:
                    print("✅ Connection successful!")
                    print(f"Response: {response.json()}")
                    print(f"\nSuccessful URL format: {base_url}")
                    return
                else:
                    print(f"Error response: {response.text}")
            except Exception as e:
                print(f"Error connecting: {e}")
    
    # If we get here, all connection attempts failed
    print("\n❌ All connection attempts failed.")
    print("Please check your JIRA credentials and domain.")
    print("\nTroubleshooting tips:")
    print("1. Verify your API token is correct and not expired")
    print("2. Confirm your JIRA domain is in the correct format")
    print("3. Check that your account has API access permissions")

if __name__ == "__main__":
    test_jira_connection() 