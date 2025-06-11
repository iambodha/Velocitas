"use client";

import { useState, useEffect } from 'react';
import LandingPage from '../components/LandingPage';
import DashboardPage from '../components/DashboardPage';

const API_BASE = 'http://localhost:8001'; // Updated to auth service port

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [darkMode, setDarkMode] = useState(false);
  const [authWindow, setAuthWindow] = useState<Window | null>(null);
  const [initialSyncComplete, setInitialSyncComplete] = useState(false);
  const [user, setUser] = useState<any>(null);

  // Function to trigger initial email sync
  const triggerInitialSync = async () => {
    try {
      console.log('Triggering initial email sync...');
      const token = localStorage.getItem('supabase_token');
      
      if (!token) {
        console.error('No token available for sync');
        return;
      }
      
      const response = await fetch(`http://localhost:8002/emails`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        console.log('Initial sync completed successfully');
        setInitialSyncComplete(true);
      } else {
        console.error('Initial sync failed:', response.status);
      }
    } catch (error) {
      console.error('Error triggering initial sync:', error);
    }
  };

  // Check authentication status on mount
  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('supabase_token');
      const refreshToken = localStorage.getItem('supabase_refresh_token');
      const userData = localStorage.getItem('user_data');
      
      if (token && userData) {
        try {
          // Verify token with auth service
          const response = await fetch(`${API_BASE}/verify`, {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          });
          
          if (response.ok) {
            const data = await response.json();
            setUser(data.user);
            setIsAuthenticated(true);
            console.log('User authenticated:', data.user);
            
            // Check if initial sync is needed
            setTimeout(() => {
              triggerInitialSync();
            }, 1000);
          } else if (refreshToken) {
            // Try to refresh token
            await refreshAuthToken(refreshToken);
          } else {
            // Clear invalid tokens
            localStorage.removeItem('supabase_token');
            localStorage.removeItem('supabase_refresh_token');
            localStorage.removeItem('user_data');
          }
        } catch (error) {
          console.error('Auth check failed:', error);
          // Clear tokens on error
          localStorage.removeItem('supabase_token');
          localStorage.removeItem('supabase_refresh_token');
          localStorage.removeItem('user_data');
        }
      }
      
      setIsLoading(false);
    };

    checkAuth();
  }, []);

  // Refresh token function
  const refreshAuthToken = async (refreshToken: string) => {
    try {
      const response = await fetch(`${API_BASE}/refresh`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ refresh_token: refreshToken })
      });

      if (response.ok) {
        const data = await response.json();
        localStorage.setItem('supabase_token', data.access_token);
        localStorage.setItem('supabase_refresh_token', data.refresh_token);
        localStorage.setItem('user_data', JSON.stringify(data.user));
        setUser(data.user);
        setIsAuthenticated(true);
        console.log('Token refreshed successfully');
      } else {
        // Clear invalid tokens
        localStorage.removeItem('supabase_token');
        localStorage.removeItem('supabase_refresh_token');
        localStorage.removeItem('user_data');
      }
    } catch (error) {
      console.error('Token refresh failed:', error);
    }
  };

  // Handle authentication
  const handleAuthentication = async () => {
    try {
      setIsLoading(true);
      
      // Check if user already has Supabase account, otherwise redirect to signup
      const signupUrl = `${window.location.origin}/signup`;
      
      // For now, let's get Google OAuth URL for Gmail access
      const response = await fetch(`${API_BASE}/auth/google`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('supabase_token')}`
        }
      });
      
      if (!response.ok) {
        // User needs to sign up/login first
        window.location.href = '/auth';
        return;
      }
      
      const data = await response.json();
      
      // Open popup for Google OAuth
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
    } finally {
      setIsLoading(false);
    }
  };

  // Listen for auth messages from popup
  useEffect(() => {
    const handleAuthMessage = (event: MessageEvent) => {
      // Accept messages from your domain and auth service
      if (event.origin !== window.location.origin && 
          event.origin !== 'http://localhost:8001') {
        return;
      }
      
      if (event.data.type === 'gmail_auth_success') {
        console.log('Gmail authentication successful!');
        
        if (authWindow && !authWindow.closed) {
          authWindow.close();
          setAuthWindow(null);
        }
        
        // Trigger initial sync
        setTimeout(() => {
          triggerInitialSync();
        }, 1000);
        
      } else if (event.data.type === 'gmail_auth_error') {
        console.error('Gmail authentication failed:', event.data.error);
        
        if (authWindow && !authWindow.closed) {
          authWindow.close();
          setAuthWindow(null);
        }
        
        alert(`Gmail authentication failed: ${event.data.error}`);
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

  // Show auth page if not authenticated
  if (!isAuthenticated) {
    return <AuthPage darkMode={darkMode} setDarkMode={setDarkMode} />;
  }

  // Show dashboard if authenticated
  return (
    <DashboardPage 
      darkMode={darkMode} 
      setDarkMode={setDarkMode}
      initialSyncComplete={initialSyncComplete}
      user={user}
    />
  );
}

// New Auth Page Component
function AuthPage({ darkMode, setDarkMode }: { darkMode: boolean; setDarkMode: (dark: boolean) => void }) {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const endpoint = isLogin ? '/signin' : '/signup';
      const body = isLogin 
        ? { email, password }
        : { email, password, name };

      const response = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(body)
      });

      if (response.ok) {
        const data = await response.json();
        
        // Check if email confirmation is required
        if (data.email_confirmation_required) {
          alert('Registration successful! Please check your email to confirm your account before signing in.');
          setIsLogin(true); // Switch to login mode
          setEmail(''); // Clear form
          setPassword('');
          setName('');
          return;
        }
        
        // Store tokens and user data (for successful login/signup without confirmation)
        if (data.access_token) {
          localStorage.setItem('supabase_token', data.access_token);
          localStorage.setItem('supabase_refresh_token', data.refresh_token);
          localStorage.setItem('user_data', JSON.stringify(data.user));
          
          // Reload page to trigger auth check
          window.location.reload();
        }
      } else {
        const error = await response.json();
        alert(error.detail || 'Authentication failed');
      }
    } catch (error) {
      console.error('Auth error:', error);
      alert('Authentication failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className={`min-h-screen flex items-center justify-center ${darkMode ? 'bg-gray-900' : 'bg-gray-50'}`}>
      <div className={`max-w-md w-full mx-4 p-8 rounded-lg shadow-lg ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold mb-2">Welcome to Velocitas</h1>
          <p className={`${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            {isLogin ? 'Sign in to your account' : 'Create your account'}
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          {!isLogin && (
            <div className="mb-4">
              <label className={`block text-sm font-medium mb-2 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                Name
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className={`w-full p-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-yellow-500 ${
                  darkMode ? 'bg-gray-700 border-gray-600 text-white' : 'bg-white border-gray-300'
                }`}
                required={!isLogin}
              />
            </div>
          )}

          <div className="mb-4">
            <label className={`block text-sm font-medium mb-2 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              Email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={`w-full p-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-yellow-500 ${
                darkMode ? 'bg-gray-700 border-gray-600 text-white' : 'bg-white border-gray-300'
              }`}
              required
            />
          </div>

          <div className="mb-6">
            <label className={`block text-sm font-medium mb-2 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={`w-full p-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-yellow-500 ${
                darkMode ? 'bg-gray-700 border-gray-600 text-white' : 'bg-white border-gray-300'
              }`}
              required
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-yellow-500 hover:bg-yellow-600 text-white font-semibold py-3 px-4 rounded-lg transition-colors disabled:opacity-50"
          >
            {isLoading ? 'Please wait...' : (isLogin ? 'Sign In' : 'Sign Up')}
          </button>
        </form>

        <div className="mt-6 text-center">
          <button
            onClick={() => setIsLogin(!isLogin)}
            className={`text-yellow-500 hover:text-yellow-600 font-medium`}
          >
            {isLogin ? "Don't have an account? Sign up" : "Already have an account? Sign in"}
          </button>
        </div>

        <div className="mt-4 text-center">
          <button
            onClick={() => setDarkMode(!darkMode)}
            className={`p-2 rounded-lg ${darkMode ? 'hover:bg-gray-700' : 'hover:bg-gray-100'}`}
          >
            {darkMode ? '☀️' : '🌙'}
          </button>
        </div>
      </div>
    </div>
  );
}
