"use client";

import { useState, useEffect } from 'react';
import LandingPage from '../components/LandingPage';
import DashboardPage from '../components/DashboardPage';

const API_BASE = 'http://localhost:8080';

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [darkMode, setDarkMode] = useState(false);
  const [authWindow, setAuthWindow] = useState<Window | null>(null);

  // Check authentication status on mount
  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('gmail_token');
      const email = localStorage.getItem('user_email');
      
      if (token && email) {
        // Verify token is still valid
        try {
          const response = await fetch(`${API_BASE}/status`, {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          });
          
          if (response.ok) {
            const data = await response.json();
            if (data.authenticated) {
              setIsAuthenticated(true);
            } else {
              localStorage.removeItem('gmail_token');
              localStorage.removeItem('user_email');
            }
          } else {
            localStorage.removeItem('gmail_token');
            localStorage.removeItem('user_email');
          }
        } catch (error) {
          console.error('Auth check failed:', error);
          localStorage.removeItem('gmail_token');
          localStorage.removeItem('user_email');
        }
      }
      
      setIsLoading(false);
    };

    checkAuth();
  }, []);

  // Handle authentication
  const handleAuthentication = async () => {
    try {
      const response = await fetch(`${API_BASE}/auth`);
      
      if (!response.ok) {
        throw new Error(`Auth request failed: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (!data.authorization_url) {
        throw new Error('No authorization URL received from server');
      }
      
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
      if (event.origin !== window.location.origin && event.origin !== 'http://localhost:8080') {
        return;
      }

      if (event.data.type === 'GMAIL_AUTH_SUCCESS') {
        localStorage.setItem('gmail_token', event.data.token);
        localStorage.setItem('user_email', event.data.user_email);
        localStorage.setItem('user_id', event.data.user_id);
        
        setIsAuthenticated(true);
        
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
  return <DashboardPage darkMode={darkMode} setDarkMode={setDarkMode} />;
}
