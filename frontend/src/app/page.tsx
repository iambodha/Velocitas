"use client";

import { useState, useEffect } from 'react';
import LandingPage from '../components/LandingPage';
import DashboardPage from '../components/DashboardPage';

const API_BASE = 'http://localhost:8080'; // Updated to gateway port

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [darkMode, setDarkMode] = useState(false);
  const [authWindow, setAuthWindow] = useState<Window | null>(null);
  const [initialSyncComplete, setInitialSyncComplete] = useState(false);

  // Function to trigger initial email sync
  const triggerInitialSync = async () => {
    try {
      console.log('Triggering initial email sync...');
      const token = localStorage.getItem('gmail_token');
      
      const response = await fetch(`${API_BASE}/emails/sync`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        console.log('Initial sync started successfully');
      } else {
        console.error('Initial sync failed:', response.status);
      }
    } catch (error) {
      console.error('Error triggering initial sync:', error);
    } finally {
      setInitialSyncComplete(true);
    }
  };

  // Check authentication status on mount
  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('gmail_token');
      const email = localStorage.getItem('user_email');
      
      console.log('Checking auth - Token exists:', !!token, 'Email:', email);
      
      if (token && email) {
        // Verify token is still valid
        try {
          const response = await fetch(`http://localhost:8080/status`, {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          });
          
          if (response.ok) {
            const data = await response.json();
            if (data.authenticated) {
              setIsAuthenticated(true);
              console.log('Authentication verified');
            } else {
              console.log('Token invalid, clearing storage');
              localStorage.removeItem('gmail_token');
              localStorage.removeItem('user_email');
              localStorage.removeItem('user_id');
            }
          } else {
            console.log('Auth check failed:', response.status);
            localStorage.removeItem('gmail_token');
            localStorage.removeItem('user_email');
            localStorage.removeItem('user_id');
          }
        } catch (error) {
          console.error('Auth check failed:', error);
          localStorage.removeItem('gmail_token');
          localStorage.removeItem('user_email');
          localStorage.removeItem('user_id');
        }
      }
      
      setIsLoading(false);
    };

    // Only check auth if we're not in the middle of handling a callback
    const urlParams = new URLSearchParams(window.location.search);
    if (!urlParams.get('code')) {
      checkAuth();
    } else {
      setIsLoading(false);
    }
  }, []);

  // Handle authentication
  const handleAuthentication = async () => {
    try {
      // Call the gateway auth endpoint
      const response = await fetch('http://localhost:8080/auth'); // Use gateway port
    
      if (!response.ok) {
        throw new Error('Failed to get authorization URL');
      }
    
      const data = await response.json();
    
      // Open popup for authentication
      const popup = window.open(
        data.authorization_url,
        'gmail_auth',
        'width=500,height=600,scrollbars=yes,resizable=yes,location=yes'
      );
    
      if (!popup) {
        throw new Error('Popup blocked. Please allow popups for this site.');
      }
    
      setAuthWindow(popup);
    
      const checkClosed = setInterval(() => {
        if (popup.closed) {
          clearInterval(checkClosed);
          setAuthWindow(null);
          console.log('Authentication popup was closed');
        }
      }, 1000);
    
    } catch (error) {
      console.error('Authentication error:', error);
      alert(`Authentication failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  // Listen for auth messages from popup
  useEffect(() => {
    const handleAuthMessage = (event: MessageEvent) => {
      // Accept messages from your domain and localhost
      if (event.origin !== window.location.origin && 
          event.origin !== 'http://localhost:8080') { // Change to gateway port
        return;
      }
      
      if (event.data.type === 'GMAIL_AUTH_SUCCESS') {
        localStorage.setItem('gmail_token', event.data.token);
        localStorage.setItem('user_email', event.data.user_email);
        localStorage.setItem('user_id', event.data.user_id);
        
        setIsAuthenticated(true);
        
        // Trigger initial sync after successful authentication
        setTimeout(() => {
          triggerInitialSync();
        }, 1000);
        
        if (authWindow && !authWindow.closed) {
          authWindow.close();
          setAuthWindow(null);
        }
        
        console.log('Authentication successful!');
      } else if (event.data.type === 'GMAIL_AUTH_ERROR') {
        console.error('Authentication failed:', event.data.error);
        
        if (authWindow && !authWindow.closed) {
          authWindow.close();
          setAuthWindow(null);
        }
        
        alert(`Authentication failed: ${event.data.error}`);
      }
    };

    window.addEventListener('message', handleAuthMessage);
    
    return () => {
      window.removeEventListener('message', handleAuthMessage);
    };
  }, [authWindow]);

  // Handle authentication callback
  useEffect(() => {
    const handleAuthCallback = async () => {
      const urlParams = new URLSearchParams(window.location.search);
      const code = urlParams.get('code');
      const state = urlParams.get('state');
      
      if (code && state) {
        try {
          console.log('Handling OAuth callback...');
          
          // Call the gateway's callback endpoint
          const response = await fetch(`http://localhost:8080/callback?${urlParams.toString()}`);
          
          if (response.ok) {
            const data = await response.json();
            console.log('Callback response:', data);
            
            // Store the token and user info
            if (data.access_token && data.email) {
              localStorage.setItem('gmail_token', data.access_token);
              localStorage.setItem('user_email', data.email);
              localStorage.setItem('user_id', data.email);
              setIsAuthenticated(true);
              
              console.log('Token stored:', data.access_token.substring(0, 20) + '...');
              
              // Trigger initial sync after successful callback
              setTimeout(() => {
                triggerInitialSync();
              }, 1000);
              
              // Clear URL params
              window.history.replaceState({}, document.title, window.location.pathname);
            } else {
              console.error('Missing token or email in callback response:', data);
            }
          } else {
            console.error('Callback request failed:', response.status, await response.text());
          }
        } catch (error) {
          console.error('Callback handling failed:', error);
        }
      }
    };

    handleAuthCallback();
  }, []);

  // Show loading spinner while checking auth
  if (isLoading) {
    return (
      <div className={`h-screen flex items-center justify-center ${darkMode ? 'bg-gray-900' : 'bg-white'}`}>
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-yellow-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className={`${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>Loading...</p>
        </div>
      </div>
    );
  }

  // Show landing page if not authenticated
  if (!isAuthenticated) {
    return (
      <LandingPage 
        onGetStarted={handleAuthentication}
        darkMode={darkMode}
        setDarkMode={setDarkMode}
      />
    );
  }

  // Show dashboard if authenticated
  return (
    <DashboardPage 
      darkMode={darkMode} 
      setDarkMode={setDarkMode}
      initialSyncComplete={initialSyncComplete}
    />
  );
}
