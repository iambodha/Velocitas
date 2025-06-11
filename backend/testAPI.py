import requests
import json
import webbrowser
from urllib.parse import urlparse, parse_qs

class SupabaseAPITester:
    def __init__(self, base_url="http://localhost:3001"):
        self.base_url = base_url
        self.session = requests.Session()
        self.token = None
        self.user_data = None
    
    def signup(self, email, password, name):
        """Test user signup"""
        print(f"\n🔐 Testing signup for {email}...")
        
        data = {
            "email": email,
            "password": password,
            "name": name
        }
        
        response = self.session.post(f"{self.base_url}/api/auth/signup", json=data)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Signup successful!")
            print(f"User ID: {result['user']['id']}")
            print(f"Email: {result['user']['email']}")
            print(f"Needs Google Auth: {result['needsGoogleAuth']}")
            return result
        else:
            print(f"❌ Signup failed: {response.json()}")
            return None
    
    def login(self, email, password):
        """Test user login"""
        print(f"\n🔓 Testing login for {email}...")
        
        data = {
            "email": email,
            "password": password
        }
        
        response = self.session.post(f"{self.base_url}/api/auth/login", json=data)
        
        if response.status_code == 200:
            result = response.json()
            self.token = result['session']['access_token']
            self.user_data = result['user']
            
            # Set authorization header for future requests
            self.session.headers.update({
                'Authorization': f'Bearer {self.token}'
            })
            
            print("✅ Login successful!")
            print(f"User ID: {result['user']['id']}")
            print(f"Email: {result['user']['email']}")
            print(f"Token: {self.token[:20]}...")
            return result
        else:
            print(f"❌ Login failed: {response.json()}")
            return None
    
    def get_profile(self):
        """Test get user profile"""
        print("\n👤 Testing get profile...")
        
        if not self.token:
            print("❌ No token available. Please login first.")
            return None
        
        response = self.session.get(f"{self.base_url}/api/user/profile")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Profile retrieved successfully!")
            print(f"User ID: {result['user']['id']}")
            print(f"Email: {result['user']['email']}")
            print(f"Google Connected: {result['googleConnected']}")
            if result['googleEmail']:
                print(f"Google Email: {result['googleEmail']}")
            return result
        else:
            print(f"❌ Get profile failed: {response.json()}")
            return None
    
    def get_google_auth_url(self):
        """Test getting Google OAuth URL"""
        print("\n🔗 Testing Google OAuth URL generation...")
        
        if not self.token:
            print("❌ No token available. Please login first.")
            return None
        
        response = self.session.get(f"{self.base_url}/api/auth/google/url")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Google OAuth URL generated!")
            print(f"Auth URL: {result['authUrl']}")
            
            # Open the URL in browser for manual testing
            print("\n🌐 Opening Google OAuth URL in browser...")
            print("After authorizing, copy the 'code' parameter from the callback URL")
            webbrowser.open(result['authUrl'])
            
            return result['authUrl']
        else:
            print(f"❌ Failed to get Google OAuth URL: {response.json()}")
            return None
    
    def google_callback(self, code):
        """Test Google OAuth callback"""
        print(f"\n🔄 Testing Google OAuth callback with code: {code[:20]}...")
        
        if not self.token:
            print("❌ No token available. Please login first.")
            return None
        
        data = {"code": code}
        response = self.session.post(f"{self.base_url}/api/auth/google/callback", json=data)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Google account connected successfully!")
            print(f"Google Email: {result['googleUser']['email']}")
            print(f"Google Name: {result['googleUser']['name']}")
            return result
        else:
            print(f"❌ Google callback failed: {response.json()}")
            return None
    
    def update_profile(self, name=None, avatar_url=None):
        """Test profile update"""
        print("\n📝 Testing profile update...")
        
        if not self.token:
            print("❌ No token available. Please login first.")
            return None
        
        data = {}
        if name:
            data['name'] = name
        if avatar_url:
            data['avatar_url'] = avatar_url
        
        response = self.session.put(f"{self.base_url}/api/user/profile", json=data)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Profile updated successfully!")
            return result
        else:
            print(f"❌ Profile update failed: {response.json()}")
            return None
    
    def health_check(self):
        """Test health check endpoint"""
        print("\n❤️ Testing health check...")
        
        response = self.session.get(f"{self.base_url}/health")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Server is healthy!")
            print(f"Status: {result['status']}")
            print(f"Timestamp: {result['timestamp']}")
            return result
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return None
    
    def logout(self):
        """Test logout"""
        print("\n🚪 Testing logout...")
        
        if not self.token:
            print("❌ No token available. Please login first.")
            return None
        
        response = self.session.post(f"{self.base_url}/api/auth/logout")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Logout successful!")
            
            # Clear token and headers
            self.token = None
            self.user_data = None
            if 'Authorization' in self.session.headers:
                del self.session.headers['Authorization']
            
            return result
        else:
            print(f"❌ Logout failed: {response.json()}")
            return None
    
    def sync_emails(self, max_results=50):
        """Test email sync from Gmail"""
        print(f"\n📧 Testing email sync (max {max_results} emails)...")
        
        if not self.token:
            print("❌ No token available. Please login first.")
            return None
        
        data = {"maxResults": max_results}
        response = self.session.post(f"{self.base_url}/api/emails/sync", json=data)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Emails synced successfully!")
            print(f"Message: {result['message']}")
            print(f"Emails synced: {result['count']}")
            return result
        elif response.status_code == 400:
            error = response.json()
            print(f"⚠️ Gmail not connected: {error['error']}")
            return None
        else:
            print(f"❌ Email sync failed: {response.json()}")
            return None
    
    def get_emails(self, page=1, limit=20):
        """Test getting emails with pagination"""
        print(f"\n📬 Testing get emails (page {page}, limit {limit})...")
        
        if not self.token:
            print("❌ No token available. Please login first.")
            return None
        
        params = {"page": page, "limit": limit}
        response = self.session.get(f"{self.base_url}/api/emails", params=params)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Emails retrieved successfully!")
            print(f"Retrieved {len(result['emails'])} emails")
            
            # Display first few emails
            for i, email in enumerate(result['emails'][:3]):
                print(f"\n📧 Email {i+1}:")
                print(f"  Subject: {email.get('subject', 'No subject')}")
                print(f"  From: {email.get('senderEmail', 'Unknown sender')}")
                print(f"  Date: {email.get('receivedAt', 'Unknown date')}")
                print(f"  Thread ID: {email.get('gmailThreadId', 'No thread ID')}")
                if email.get('snippet'):
                    print(f"  Preview: {email['snippet'][:100]}...")
            
            return result
        elif response.status_code == 400:
            error = response.json()
            print(f"⚠️ Gmail not connected: {error['error']}")
            return None
        else:
            print(f"❌ Get emails failed: {response.json()}")
            return None
    
    def get_single_email(self, email_id):
        """Test getting a single email by ID"""
        print(f"\n📧 Testing get single email (ID: {email_id})...")
        
        if not self.token:
            print("❌ No token available. Please login first.")
            return None
        
        response = self.session.get(f"{self.base_url}/api/emails/{email_id}")
        
        if response.status_code == 200:
            result = response.json()
            email = result['email']
            print("✅ Email retrieved successfully!")
            print(f"\n📧 EMAIL DETAILS:")
            print(f"Subject: {email.get('subject', 'No subject')}")
            print(f"From: {email.get('senderEmail', 'Unknown')} ({email.get('senderName', 'No name')})")
            print(f"To: {', '.join(email.get('recipientEmails', []))}")
            if email.get('ccEmails'):
                print(f"CC: {', '.join(email['ccEmails'])}")
            print(f"Date: {email.get('receivedAt', 'Unknown')}")
            print(f"Read: {'Yes' if email.get('isRead') else 'No'}")
            print(f"Starred: {'Yes' if email.get('isStarred') else 'No'}")
            print(f"Has Attachments: {'Yes' if email.get('hasAttachments') else 'No'}")
            print(f"Labels: {', '.join(email.get('labels', []))}")
            
            if email.get('bodyText'):
                print(f"\nText Content (first 200 chars):")
                print(f"{email['bodyText'][:200]}...")
            
            if email.get('bodyHtml'):
                print(f"\nHTML Content available: Yes")
            
            if email.get('attachments'):
                print(f"\nAttachments:")
                for att in email['attachments']:
                    print(f"  - {att.get('filename', 'Unknown')} ({att.get('mimeType', 'Unknown type')})")
            
            return result
        elif response.status_code == 404:
            print("❌ Email not found")
            return None
        else:
            print(f"❌ Failed to get email: {response.json()}")
            return None

def main():
    """Main testing function"""
    print("🚀 Starting Supabase API Testing")
    print("=" * 50)
    
    tester = SupabaseAPITester()
    
    # Test health check first
    tester.health_check()
    
    # Test user login (skip signup since account exists)
    test_email = "somanivibbodh@gmail.com"
    test_password = "Test1234"
    
    print("ℹ️ Skipping signup - using existing account")
    
    # Test login
    login_result = tester.login(test_email, test_password)
    
    if login_result:
        # Test get profile
        profile_result = tester.get_profile()
        
        def attempt_email_sync():
            """Helper function to attempt email sync and handle re-auth"""
            print("\n" + "=" * 50)
            print("📧 TESTING EMAIL FUNCTIONALITY")
            print("=" * 50)
            
            # Try to sync emails
            sync_result = tester.sync_emails(max_results=10)
            
            # Check if sync failed due to auth issues
            if not sync_result:
                print("\n⚠️  Email sync failed - likely due to expired Gmail authorization.")
                print("🔄 Let's re-authorize your Gmail account...")
                
                # Get new OAuth URL for re-authorization
                google_url = tester.get_google_auth_url()
                if google_url:
                    code = input("\n🔑 Enter the OAuth code from the callback URL to re-authorize Gmail: ").strip()
                    if code:
                        callback_result = tester.google_callback(code)
                        if callback_result:
                            print("\n✅ Re-authorization successful! Trying email sync again...")
                            # Retry email sync with fresh tokens
                            sync_result = tester.sync_emails(max_results=10)
                        else:
                            print("❌ Re-authorization failed")
                            return False
                    else:
                        print("⏭️  Skipping re-authorization")
                        return False
                else:
                    print("❌ Failed to get OAuth URL")
                    return False
            
            # If we have successful sync result, proceed with email operations
            if sync_result and sync_result.get('count', 0) > 0:
                # Get emails list
                emails_result = tester.get_emails(page=1, limit=5)
                
                if emails_result and emails_result.get('emails'):
                    # Get the first email in detail
                    first_email = emails_result['emails'][0]
                    if first_email.get('id'):
                        print(f"\n📧 Getting detailed view of first email...")
                        tester.get_single_email(first_email['id'])
                    
                    # Ask user if they want to see another email
                    print(f"\nAvailable emails:")
                    for i, email in enumerate(emails_result['emails'][:5]):
                        print(f"{i+1}. {email.get('subject', 'No subject')} - {email.get('senderEmail', 'Unknown')}")
                    
                    choice = input(f"\nEnter number (1-{len(emails_result['emails'][:5])}) to view email detail (or press Enter to skip): ").strip()
                    
                    if choice.isdigit() and 1 <= int(choice) <= len(emails_result['emails'][:5]):
                        selected_email = emails_result['emails'][int(choice)-1]
                        if selected_email.get('id'):
                            tester.get_single_email(selected_email['id'])
                    return True
                else:
                    print("⚠️ No emails found after sync")
                    return False
            else:
                print("⚠️ No emails were synced after re-authorization attempt")
                return False
        
        # Check if Google is connected
        if profile_result and profile_result.get('googleConnected'):
            print("✅ Google account shows as connected. Attempting email functionality...")
            attempt_email_sync()
        else:
            print("⚠️ Google account not connected. Starting initial OAuth flow...")
            # Get OAuth URL for initial connection
            google_url = tester.get_google_auth_url()
            if google_url:
                code = input("\nEnter the OAuth code (or press Enter to skip): ").strip()
                if code:
                    callback_result = tester.google_callback(code)
                    if callback_result:
                        print("\n✅ Google account connected! Now testing email functionality...")
                        attempt_email_sync()

    print("\n" + "=" * 50)
    print("🏁 Testing completed!")

if __name__ == "__main__":
    main()