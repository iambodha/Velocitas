"use client";

import { useState, useEffect } from 'react';
import { 
  Search, 
  Menu, 
  Settings, 
  Star, 
  Archive, 
  Trash2, 
  Reply, 
  ReplyAll, 
  Forward,
  MoreHorizontal,
  Paperclip,
  Send,
  Plus,
  Inbox,
  Mail,
  FileText,
  Users,
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  Moon,
  Sun,
  X,
  ArrowLeft,
  BrainCircuit,
  RefreshCw
} from 'lucide-react';

const API_BASE = 'http://localhost:8002'; // Email service port

// Email interface
interface Email {
  id: string;
  subject: string;
  sender: string;
  recipient: string;
  date: string;
  snippet: string;
  body_text?: string;
  body_html?: string;
  is_read: boolean;
  is_starred: boolean;
  category?: string;
  urgency?: number;
  stored_at?: string;
  source?: string;
}

interface DashboardPageProps {
  darkMode: boolean;
  setDarkMode: (dark: boolean) => void;
  initialSyncComplete?: boolean;
  user?: any;
}

const sidebarItems = [
  { icon: Inbox, label: "Inbox", count: 12, active: true },
  { icon: Star, label: "Starred", count: 3 },
  { icon: FileText, label: "Drafts", count: 1 },
  { icon: Mail, label: "Sent" },
  { icon: Archive, label: "Archive" },
  { icon: Trash2, label: "Trash" },
  { icon: AlertCircle, label: "Spam" }
];

// Define color sets for different categories
const categoryColors = {
  "Work": {
    bg: "bg-blue-500",
    bgLight: "bg-blue-100",
    text: "text-blue-700",
    darkBg: "bg-blue-700",
    darkText: "text-blue-300",
    border: "border-blue-200"
  },
  "Personal": {
    bg: "bg-purple-500",
    bgLight: "bg-purple-100",
    text: "text-purple-700",
    darkBg: "bg-purple-700",
    darkText: "text-purple-300",
    border: "border-purple-200"
  },
  "Finance": {
    bg: "bg-green-500",
    bgLight: "bg-green-100",
    text: "text-green-700",
    darkBg: "bg-green-700",
    darkText: "text-green-300",
    border: "border-green-200"
  },
  "Updates": {
    bg: "bg-yellow-500",
    bgLight: "bg-yellow-100",
    text: "text-yellow-700",
    darkBg: "bg-yellow-700",
    darkText: "text-yellow-300",
    border: "border-yellow-200"
  },
  "Social": {
    bg: "bg-red-500",
    bgLight: "bg-red-100",
    text: "text-red-700",
    darkBg: "bg-red-700",
    darkText: "text-red-300",
    border: "border-red-200"
  }
};

export default function DashboardPage({ darkMode, setDarkMode, initialSyncComplete = false, user }: DashboardPageProps) {
  const [emails, setEmails] = useState<Email[]>([]);
  const [selectedEmail, setSelectedEmail] = useState<Email | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [showCompose, setShowCompose] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [isMobileView, setIsMobileView] = useState(false);
  const [showEmailList, setShowEmailList] = useState(true);
  const [showEmailContent, setShowEmailContent] = useState(false);
  const [showAIOverview, setShowAIOverview] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filteredEmails, setFilteredEmails] = useState<Email[]>([]);
  const [syncing, setSyncing] = useState(false);
  const [showSyncStatus, setShowSyncStatus] = useState(false);

  // Helper function to get auth headers
  const getAuthHeaders = () => {
    const token = localStorage.getItem('supabase_token');
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    };
  };

  // Fetch emails from API
  const fetchEmails = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_BASE}/emails?max_results=50`, {
        headers: getAuthHeaders()
      });

      if (!response.ok) {
        if (response.status === 403) {
          // Gmail access not granted
          setError('Gmail access required. Please connect your Google account.');
          checkGmailAccess();
          return;
        }
        throw new Error(`Failed to fetch emails: ${response.statusText}`);
      }

      const data = await response.json();
      const emailList = data.emails || [];
      
      setEmails(emailList);
      setFilteredEmails(emailList);
      
      // Set first email as selected if none selected
      if (emailList.length > 0 && !selectedEmail) {
        setSelectedEmail(emailList[0]);
      }
    } catch (err) {
      console.error('Error fetching emails:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch emails');
    } finally {
      setLoading(false);
    }
  };

  // Fetch detailed email content
  const fetchEmailDetails = async (emailId: string): Promise<Email | null> => {
    try {
      const response = await fetch(`${API_BASE}/email/${emailId}`, {
        headers: getAuthHeaders()
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch email details: ${response.statusText}`);
      }

      return await response.json();
    } catch (err) {
      console.error('Error fetching email details:', err);
      return null;
    }
  };

  // Mark email as read
  const markEmailAsRead = async (emailId: string, isRead: boolean = true) => {
    try {
      await fetch(`${API_BASE}/email/${emailId}/read?is_read=${isRead}`, {
        method: 'PUT',
        headers: getAuthHeaders()
      });

      // Update local state
      setEmails(prev => prev.map(email => 
        email.id === emailId ? { ...email, is_read: isRead } : email
      ));
      setFilteredEmails(prev => prev.map(email => 
        email.id === emailId ? { ...email, is_read: isRead } : email
      ));
    } catch (err) {
      console.error('Error marking email as read:', err);
    }
  };

  // Toggle email star
  const toggleEmailStar = async (emailId: string, isStarred: boolean) => {
    try {
      await fetch(`${API_BASE}/email/${emailId}/star?is_starred=${isStarred}`, {
        method: 'PUT',
        headers: getAuthHeaders()
      });

      // Update local state
      setEmails(prev => prev.map(email => 
        email.id === emailId ? { ...email, is_starred: isStarred } : email
      ));
      setFilteredEmails(prev => prev.map(email => 
        email.id === emailId ? { ...email, is_starred: isStarred } : email
      ));
      
      if (selectedEmail?.id === emailId) {
        setSelectedEmail(prev => prev ? { ...prev, is_starred: isStarred } : null);
      }
    } catch (err) {
      console.error('Error toggling email star:', err);
    }
  };

  // Sync emails from Gmail
  const syncEmails = async () => {
    try {
      setSyncing(true);
      const response = await fetch(`${API_BASE}/emails/sync`, {
        method: 'POST',
        headers: getAuthHeaders()
      });

      if (response.ok) {
        // Refresh emails after sync
        await fetchEmails();
      }
    } catch (error) {
      console.error('Error syncing emails:', error);
    } finally {
      setSyncing(false);
    }
  };

  // Search emails
  const searchEmails = async (query: string) => {
    if (!query.trim()) {
      setFilteredEmails(emails);
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/emails/search?q=${encodeURIComponent(query)}&limit=50`, {
        headers: getAuthHeaders()
      });

      if (response.ok) {
        const data = await response.json();
        setFilteredEmails(data.emails || []);
      } else {
        // Fallback to local search
        const filtered = emails.filter(email => 
          email.subject?.toLowerCase().includes(query.toLowerCase()) ||
          email.sender?.toLowerCase().includes(query.toLowerCase()) ||
          email.snippet?.toLowerCase().includes(query.toLowerCase())
        );
        setFilteredEmails(filtered);
      }
    } catch (err) {
      console.error('Error searching emails:', err);
      // Fallback to local search
      const filtered = emails.filter(email => 
        email.subject?.toLowerCase().includes(query.toLowerCase()) ||
        email.sender?.toLowerCase().includes(query.toLowerCase()) ||
        email.snippet?.toLowerCase().includes(query.toLowerCase())
      );
      setFilteredEmails(filtered);
    }
  };

  // Handle search input
  const handleSearch = (value: string) => {
    setSearchTerm(value);
    searchEmails(value);
  };

  // Handle email selection
  const handleEmailSelect = async (email: Email) => {
    // Mark email as read if it's not already read
    if (!email.is_read) {
      await markEmailAsRead(email.id, true);
    }

    // Fetch detailed email content if needed
    const detailedEmail = await fetchEmailDetails(email.id);
    const emailToSelect = detailedEmail || email;

    setSelectedEmail(emailToSelect);

    // Handle mobile view navigation
    if (isMobileView) {
      setShowEmailList(false);
      setShowEmailContent(true);
    }
  };

  // Handle back to email list (for mobile)
  const handleBackToList = () => {
    if (isMobileView) {
      setShowEmailList(true);
      setShowEmailContent(false);
    }
  };

  // Check window size on mount and resize
  useEffect(() => {
    const handleResize = () => {
      setIsMobileView(window.innerWidth < 768);
      
      // Auto-collapse sidebar on smaller screens
      if (window.innerWidth < 1024) {
        setSidebarOpen(false);
      } else {
        setSidebarOpen(true);
      }
      
      // In mobile view, show either email list or content, not both
      if (window.innerWidth < 768) {
        setShowEmailList(true);
        setShowEmailContent(false);
      } else {
        setShowEmailList(true);
        setShowEmailContent(true);
      }
    };

    // Initial check
    handleResize();

    // Add event listener
    window.addEventListener('resize', handleResize);
    
    // Clean up
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Show sync status message when initial sync is happening
  useEffect(() => {
    if (!initialSyncComplete) {
      setShowSyncStatus(true);
      
      // Hide sync status after 10 seconds if sync doesn't complete
      const timer = setTimeout(() => {
        setShowSyncStatus(false);
      }, 10000);
      
      return () => clearTimeout(timer);
    } else {
      setShowSyncStatus(false);
    }
  }, [initialSyncComplete]);

  // Fetch emails on component mount and when initial sync completes
  useEffect(() => {
    if (user) {
      fetchEmails();
      checkGmailAccess();
    }
  }, [user]);

  // Inject email-specific CSS styles for Gmail-like rendering
  useEffect(() => {
    const emailStyles = `
      <style id="email-content-styles">
        .email-content.gmail-style {
          font-family: Roboto, RobotoDraft, Helvetica, Arial, sans-serif !important;
          font-size: 14px !important;
          line-height: 1.6 !important;
          color: ${darkMode ? '#e4e6ea' : '#202124'} !important;
          background: transparent !important;
          word-wrap: break-word !important;
          overflow-wrap: break-word !important;
        }
        
        .gmail-email-wrapper * {
          max-width: 100% !important;
          word-wrap: break-word !important;
          overflow-wrap: break-word !important;
        }
        
        .gmail-email-wrapper a {
          color: ${darkMode ? '#8ab4f8' : '#1a73e8'} !important;
          text-decoration: none !important;
          word-break: break-word !important;
        }
        
        .gmail-email-wrapper a:hover {
          text-decoration: underline !important;
          color: ${darkMode ? '#aecbfa' : '#174ea6'} !important;
        }
        
        .gmail-email-wrapper p {
          margin: 0 0 12px 0 !important;
          line-height: 1.6 !important;
          font-size: 14px !important;
        }
        
        .gmail-email-wrapper div {
          line-height: 1.6 !important;
          font-size: 14px !important;
        }
        
        .gmail-email-wrapper table {
          border-collapse: collapse !important;
          max-width: 100% !important;
          table-layout: fixed !important;
          font-size: 14px !important;
        }
        
        .gmail-email-wrapper td, .gmail-email-wrapper th {
          padding: 8px !important;
          vertical-align: top !important;
          word-wrap: break-word !important;
          font-size: 14px !important;
          border: ${darkMode ? '1px solid #3c4043' : '1px solid #dadce0'} !important;
        }
        
        .gmail-email-wrapper img {
          max-width: 100% !important;
          height: auto !important;
          display: block !important;
          margin: 8px 0 !important;
        }
        
        .gmail-email-wrapper blockquote {
          border-left: 4px solid ${darkMode ? '#5f6368' : '#dadce0'} !important;
          margin: 16px 0 !important;
          padding-left: 16px !important;
          color: ${darkMode ? '#9aa0a6' : '#5f6368'} !important;
          font-style: italic !important;
        }
        
        .gmail-email-wrapper h1, .gmail-email-wrapper h2, .gmail-email-wrapper h3, 
        .gmail-email-wrapper h4, .gmail-email-wrapper h5, .gmail-email-wrapper h6 {
          margin: 16px 0 8px 0 !important;
          line-height: 1.3 !important;
          color: ${darkMode ? '#e4e6ea' : '#202124'} !important;
          font-weight: 500 !important;
        }
        
        .gmail-email-wrapper ul, .gmail-email-wrapper ol {
          margin: 8px 0 !important;
          padding-left: 20px !important;
        }
        
        .gmail-email-wrapper li {
          margin: 4px 0 !important;
          line-height: 1.6 !important;
        }
        
        .gmail-email-wrapper pre {
          font-family: 'Roboto Mono', monospace !important;
          background: ${darkMode ? '#2d3134' : '#f8f9fa'} !important;
          padding: 12px !important;
          border-radius: 4px !important;
          overflow-x: auto !important;
          white-space: pre-wrap !important;
          word-wrap: break-word !important;
          font-size: 13px !important;
        }
        
        .gmail-email-wrapper code {
          font-family: 'Roboto Mono', monospace !important;
          background: ${darkMode ? '#2d3134' : '#f1f3f4'} !important;
          padding: 2px 4px !important;
          border-radius: 3px !important;
          font-size: 13px !important;
        }
        
        /* Gmail signature styling */
        .gmail-email-wrapper .gmail_signature,
        .gmail-email-wrapper div[data-smartmail="gmail_signature"] {
          margin-top: 16px !important;
          padding-top: 16px !important;
          border-top: 1px solid ${darkMode ? '#3c4043' : '#dadce0'} !important;
          color: ${darkMode ? '#9aa0a6' : '#5f6368'} !important;
          font-size: 13px !important;
        }
        
        /* Gmail quote styling */
        .gmail-email-wrapper .gmail_quote {
          margin: 16px 0 !important;
          padding-left: 16px !important;
          border-left: 4px solid ${darkMode ? '#5f6368' : '#dadce0'} !important;
          color: ${darkMode ? '#9aa0a6' : '#5f6368'} !important;
        }
        
        /* Remove unwanted styles that might interfere */
        .gmail-email-wrapper * {
          background: transparent !important;
          box-shadow: none !important;
          text-shadow: none !important;
        }
        
        /* Preserve table backgrounds for better readability */
        .gmail-email-wrapper table,
        .gmail-email-wrapper td,
        .gmail-email-wrapper th {
          background: ${darkMode ? '#1f1f1f' : '#ffffff'} !important;
        }
        
        /* Mobile responsiveness */
        @media screen and (max-width: 600px) {
          .gmail-email-wrapper {
            font-size: 16px !important;
          }
          
          .gmail-email-wrapper table {
            width: 100% !important;
            display: block !important;
            overflow-x: auto !important;
          }
          
          .gmail-email-wrapper img {
            max-width: 100% !important;
            width: auto !important;
          }
        }
      </style>
    `;

    // Remove existing styles and add new ones
    const existingStyles = document.getElementById('email-content-styles');
    if (existingStyles) {
      existingStyles.remove();
    }
    
    document.head.insertAdjacentHTML('beforeend', emailStyles);

    // Cleanup function
    return () => {
      const styles = document.getElementById('email-content-styles');
      if (styles) {
        styles.remove();
      }
    };
  }, [darkMode]);

  // Update the formatEmailBody function to better handle HTML content
  const formatEmailBody = (email: Email) => {
    if (email.body_html) {
      // Enhanced HTML sanitization and styling for Gmail-like appearance
      let htmlContent = email.body_html;
      
      // Remove dangerous scripts and elements
      htmlContent = htmlContent.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '');
      htmlContent = htmlContent.replace(/<iframe\b[^<]*(?:(?!<\/iframe>)<[^<]*)*<\/iframe>/gi, '');
      htmlContent = htmlContent.replace(/<object\b[^<]*(?:(?!<\/object>)<[^<]*)*<\/object>/gi, '');
      htmlContent = htmlContent.replace(/<embed\b[^<]*(?:(?!<\/embed>)<[^<]*)*<\/embed>/gi, '');
      htmlContent = htmlContent.replace(/javascript:/gi, '');
      htmlContent = htmlContent.replace(/on\w+\s*=/gi, '');
      
      // Fix relative URLs to prevent broken links
      htmlContent = htmlContent.replace(/href="\/([^"]*)/gi, 'href="#"');
      htmlContent = htmlContent.replace(/src="\/([^"]*)/gi, 'src="#"');
      
      // Make sure all links open in new tab for security
      htmlContent = htmlContent.replace(/<a\s+/gi, '<a target="_blank" rel="noopener noreferrer" ');
      
      // Wrap in Gmail-like container with proper styling
      const gmailWrapper = `
        <div class="gmail-email-wrapper" style="
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif;
          font-size: 14px;
          line-height: 1.6;
          color: ${darkMode ? '#e4e6ea' : '#202124'};
          background-color: transparent;
          word-wrap: break-word;
          overflow-wrap: break-word;
          max-width: 100%;
        ">
          ${htmlContent}
        </div>
      `;
      
      return (
        <div 
          className="email-content gmail-style"
          dangerouslySetInnerHTML={{ __html: gmailWrapper }}
          style={{
            fontFamily: 'inherit',
            lineHeight: '1.6',
            color: darkMode ? '#e4e6ea' : '#202124',
            maxWidth: '100%',
            wordWrap: 'break-word',
            fontSize: '14px'
          }}
        />
      );
    } else if (email.body_text) {
      // Convert plain text URLs to clickable links and preserve formatting
      const textWithLinks = email.body_text
        .replace(/(https?:\/\/[^\s]+)/g, 
          `<a href="$1" target="_blank" rel="noopener noreferrer" style="color: ${darkMode ? '#8ab4f8' : '#1a73e8'}; text-decoration: none;">$1</a>`
        )
        .replace(/\n/g, '<br>'); // Preserve line breaks    
      
      return (
        <div 
          className="gmail-plain-text"
          style={{
            fontFamily: 'Roboto, RobotoDraft, Helvetica, Arial, sans-serif',
            fontSize: '14px',
            lineHeight: '1.6',
            color: darkMode ? '#e4e6ea' : '#202124',
            whiteSpace: 'pre-wrap',
            wordWrap: 'break-word'
          }}
          dangerouslySetInnerHTML={{ __html: textWithLinks }}
        />
      );
    } else {
      return (
        <div className={`${darkMode ? 'text-gray-400' : 'text-gray-500'} italic`}>
          {email.snippet || 'No content available'}
        </div>
      );
    }
  };

  // Format date
  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffHours = diffMs / (1000 * 60 * 60);
      const diffDays = diffMs / (1000 * 60 * 60 * 24);

      if (diffHours < 24) {
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      } else if (diffDays < 7) {
        return date.toLocaleDateString([], { weekday: 'short' });
      } else {
        return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
      }
    } catch {
      return dateString;
    }
  };

  // Handle logout
  const handleLogout = async () => {
    try {
      // Call logout endpoint
      await fetch('http://localhost:8001/signout', {
        method: 'POST',
        headers: getAuthHeaders()
      });
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // Clear local storage
      localStorage.removeItem('supabase_token');
      localStorage.removeItem('supabase_refresh_token');
      localStorage.removeItem('user_data');
      
      // Reload page to trigger auth check
      window.location.reload();
    }
  };

  // Check Gmail access status
  const checkGmailAccess = async () => {
    try {
      const response = await fetch('http://localhost:8001/gmail/status', {
        headers: getAuthHeaders()
      });
      
      if (response.ok) {
        const data = await response.json();
        if (!data.gmail_access) {
          // Show Gmail auth flow
          showGmailAuthFlow();
        }
      }
    } catch (error) {
      console.error('Gmail access check failed:', error);
    }
  };

  // Show Gmail authentication flow
  const showGmailAuthFlow = async () => {
    try {
      const response = await fetch('http://localhost:8001/auth/google', {
        headers: getAuthHeaders()
      });
      
      if (response.ok) {
        const data = await response.json();
        
        const popup = window.open(
          data.authorization_url,
          'gmail_auth',
          'width=500,height=600,scrollbars=yes,resizable=yes,location=yes'
        );
        
        if (popup) {
          const checkClosed = setInterval(() => {
            if (popup.closed) {
              clearInterval(checkClosed);
              // Refresh emails after Gmail auth
              fetchEmails();
            }
          }, 1000);
        }
      }
    } catch (error) {
      console.error('Gmail auth flow error:', error);
    }
  };

  // Initial load
  useEffect(() => {
    if (user) {
      fetchEmails();
      checkGmailAccess();
    }
  }, [user]);

  return (
    <div className={`h-screen flex overflow-hidden ${darkMode ? 'dark bg-gray-900' : 'bg-white'}`}>
      {/* Sync Status Banner */}
      {showSyncStatus && !initialSyncComplete && (
        <div className={`fixed top-0 left-0 right-0 z-40 p-3 text-center ${darkMode ? 'bg-yellow-800 text-yellow-200' : 'bg-yellow-100 text-yellow-800'} border-b`}>
          <div className="flex items-center justify-center gap-2">
            <RefreshCw size={16} className="animate-spin" />
            <span className="text-sm font-medium">
              Syncing your emails from Gmail...
            </span>
          </div>
        </div>
      )}

      {/* Sidebar - responsive */}
      <div className={`${sidebarOpen ? 'w-64' : 'w-16'} ${isMobileView && !sidebarOpen ? 'hidden' : ''} ${darkMode ? 'bg-gray-800 border-gray-700' : 'bg-gray-50 border-gray-200'} border-r transition-all duration-300 flex flex-col ${showSyncStatus && !initialSyncComplete ? 'mt-12' : ''}`}>
        {/* Menu button - moved to top of sidebar */}
        <div className={`px-4 py-4 flex ${sidebarOpen ? 'justify-between' : 'justify-center'} items-center border-b ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
          {sidebarOpen && (
            <div className="flex items-center">
              <span className={`text-lg font-semibold ${darkMode ? 'text-gray-200' : 'text-gray-900'}`}>
                Velocitas
              </span>
            </div>
          )}
          <button 
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className={`p-2 rounded-lg transition-colors ${darkMode ? 'text-gray-300 hover:bg-gray-700' : 'text-gray-700 hover:bg-gray-100'}`}
          >
            <Menu size={20} />
          </button>
        </div>

        {/* Navigation Items */}
        <nav className="flex-1 px-2 pt-4">
          {sidebarItems.map((item, index) => (
            <div
              key={index}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer transition-colors mb-1 ${
                item.active 
                  ? `bg-yellow-100 text-yellow-700 ${darkMode ? 'dark:bg-yellow-900 dark:text-yellow-300' : ''}` 
                  : `hover:bg-gray-100 ${darkMode ? 'text-gray-300 hover:bg-gray-700' : 'text-gray-700'}`
              }`}
            >
              <item.icon size={20} className={!sidebarOpen ? 'm-auto' : ''} />
              {sidebarOpen && (
                <>
                  <span className="flex-1 text-sm font-medium">{item.label}</span>
                  {item.count && (
                    <span className={`text-xs px-2 py-1 rounded-full ${darkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-200 text-gray-600'}`}>
                      {item.count}
                    </span>
                  )}
                </>
              )}
            </div>
          ))}
          
          {/* Categories/Labels Section */}
          <div className={`mt-6 mb-2 ${sidebarOpen ? 'px-3' : 'text-center'}`}>
            <span className={`text-xs uppercase font-medium ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
              {sidebarOpen ? 'Categories' : '•••'}
            </span>
          </div>
          
          {/* Category items with colored labels */}
          {[
            { label: 'Work', count: 5 },
            { label: 'Personal', count: 3 },
            { label: 'Finance', count: 2 },
            { label: 'Updates', count: 7 },
            { label: 'Social', count: 4 }
          ].map((category, index) => {
            const colorSet = categoryColors[category.label as keyof typeof categoryColors] || {
              bg: 'bg-gray-500',
              bgLight: 'bg-gray-100',
              text: 'text-gray-700',
              darkBg: 'bg-gray-700',
              darkText: 'text-gray-300',
              border: 'border-gray-200'
            };
            
            return (
              <div
                key={`category-${index}`}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer transition-colors mb-1 ${
                  darkMode ? 'hover:bg-gray-700' : 'hover:bg-gray-50'
                }`}
              >
                <div className={`w-3 h-3 rounded-full ${colorSet.bg} ${!sidebarOpen ? 'mx-auto' : ''}`}></div>
                {sidebarOpen && (
                  <>
                    <span className={`flex-1 text-sm ${darkMode ? colorSet.darkText : colorSet.text}`}>
                      {category.label}
                    </span>
                    <span className={`text-xs px-2 py-1 rounded-full ${
                      darkMode ? `${colorSet.darkBg} text-gray-200` : `${colorSet.bgLight} ${colorSet.text}`
                    }`}>
                      {category.count}
                    </span>
                  </>
                )}
              </div>
            );
          })}
        </nav>
        
        {/* Settings */}
        <div className={`p-4 border-t ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
          <div 
            onClick={() => setShowSettings(true)}
            className={`flex ${!sidebarOpen ? 'justify-center' : ''} items-center gap-3 px-3 py-2 rounded-lg cursor-pointer transition-colors ${darkMode ? 'hover:bg-gray-700 text-gray-300' : 'hover:bg-gray-100 text-gray-700'}`}
          >
            <Settings size={20} className={!sidebarOpen ? 'm-auto' : ''} />
            {sidebarOpen && <span className="text-sm font-medium">Settings</span>}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className={`flex-1 flex flex-col overflow-hidden ${showSyncStatus && !initialSyncComplete ? 'mt-12' : ''}`}>
        {/* Header */}
        <header className={`border-b px-4 md:px-6 py-4 flex items-center gap-3 md:gap-4 ${darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`}>
          <div className="flex-1 max-w-2xl flex items-center gap-3">
            <div className="relative flex-1">
              <Search className={`absolute left-3 top-1/2 transform -translate-y-1/2 ${darkMode ? 'text-gray-400' : 'text-gray-400'}`} size={18} />
              <input
                type="text"
                placeholder="Search mail"
                value={searchTerm}
                onChange={(e) => handleSearch(e.target.value)}
                className={`w-full pl-10 pr-4 py-2 border-0 rounded-lg focus:outline-none focus:ring-2 focus:ring-yellow-500 transition-all ${
                  darkMode 
                    ? 'bg-gray-700 text-gray-200 placeholder-gray-400 focus:bg-gray-600' 
                    : 'bg-gray-100 focus:bg-white'
                }`}
              />
            </div>
            
            {/* Refresh Button */}
            <button 
              onClick={fetchEmails}
              disabled={loading}
              className={`p-2 rounded-lg transition-colors ${
                darkMode ? 'hover:bg-gray-700' : 'hover:bg-gray-100'
              } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              <RefreshCw size={18} className={`${loading ? 'animate-spin' : ''} ${darkMode ? 'text-gray-300' : 'text-gray-600'}`} />
            </button>
            
            {/* Sync Button */}
            <button 
              onClick={syncEmails}
              disabled={syncing}
              className={`p-2 rounded-lg transition-colors ${
                darkMode ? 'hover:bg-gray-700 text-gray-300' : 'hover:bg-gray-100 text-gray-600'
              } ${syncing ? 'opacity-50 cursor-not-allowed' : ''}`}
              title="Sync from Gmail"
            >
              <RefreshCw size={18} className={`${syncing ? 'animate-spin' : ''}`} />
              {!isMobileView && <span className="ml-1 text-sm">Sync Gmail</span>}
            </button>
            
            {/* AI Overview Button */}
            <button 
              onClick={() => setShowAIOverview(true)}
              className={`p-2 rounded-lg flex items-center gap-2 ${
                darkMode 
                  ? 'bg-yellow-600 hover:bg-yellow-700 text-white' 
                  : 'bg-yellow-100 hover:bg-yellow-200 text-yellow-700'
              } transition-colors`}
            >
              <BrainCircuit size={18} />
              <span className="hidden md:inline text-sm font-medium">AI Overview</span>
            </button>
          </div>

          <button 
            onClick={() => setShowCompose(true)}
            className="flex items-center gap-2 px-3 py-2 bg-yellow-500 hover:bg-yellow-600 text-white rounded-lg transition-all duration-200 shadow-sm"
          >
            <Plus size={16} />
            <span className="hidden sm:inline font-medium">Compose</span>
          </button>
          
          <button 
            onClick={() => setShowSettings(true)}
            className={`p-2 rounded-lg transition-colors ${darkMode ? 'hover:bg-gray-700' : 'hover:bg-gray-100'}`}
          >
            <Settings size={20} className={darkMode ? 'text-gray-300' : ''} />
          </button>
        </header>

        <div className="flex-1 flex overflow-hidden">
          {/* Email List */}
          {showEmailList && (
            <div className={`${isMobileView ? 'w-full' : 'w-80 lg:w-96'} border-r flex flex-col ${darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`}>
              <div className={`px-4 py-3 border-b flex items-center justify-between ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
                <h2 className={`font-semibold ${darkMode ? 'text-gray-200' : 'text-gray-900'}`}>
                  Inbox {loading && <span className="text-sm font-normal">(Loading...)</span>}
                </h2>
                <div className="flex items-center gap-2">
                  <span className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                    {filteredEmails.length} emails
                  </span>
                </div>
              </div>

              <div className="flex-1 overflow-y-auto">
                {error ? (
                  <div className="p-4 text-center">
                    <div className={`text-red-500 mb-2`}>Error: {error}</div>
                    <button 
                      onClick={fetchEmails}
                      className="px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600"
                    >
                      Retry
                    </button>
                  </div>
                ) : loading ? (
                  <div className="p-4 text-center">
                    <div className={`${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>Loading emails...</div>
                  </div>
                ) : filteredEmails.length === 0 ? (
                  <div className="p-4 text-center">
                    <div className={`${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                      {searchTerm ? 'No emails found matching your search.' : 'No emails found.'}
                    </div>
                  </div>
                ) : (
                  filteredEmails.map((email) => {
                    const colorSet = categoryColors[email.category as keyof typeof categoryColors] || {
                      bg: 'bg-gray-500',
                      bgLight: 'bg-gray-100',
                      text: 'text-gray-700',
                      darkBg: 'bg-gray-700',
                      darkText: 'text-gray-300',
                      border: 'border-gray-200'
                    };
                    
                    return (
                      <div
                        key={email.id}
                        onClick={() => handleEmailSelect(email)}
                        className={`px-4 py-3 border-b cursor-pointer transition-colors ${
                          selectedEmail?.id === email.id 
                            ? `bg-yellow-50 border-yellow-200 ${darkMode ? 'dark:bg-yellow-900/20 dark:border-yellow-800' : ''}` 
                            : `border-gray-100 ${darkMode ? 'hover:bg-gray-700 border-gray-700' : 'hover:bg-gray-50'}`
                        }`}
                      >
                        <div className="flex items-start gap-3">
                          <div className="flex items-center gap-2 mt-1">
                            <Star 
                              size={16} 
                              onClick={(e) => {
                                e.stopPropagation();
                                toggleEmailStar(email.id, !email.is_starred);
                              }}
                              className={`cursor-pointer ${email.is_starred ? 'fill-yellow-400 text-yellow-400' : `${darkMode ? 'text-gray-500 hover:text-yellow-400' : 'text-gray-300 hover:text-yellow-400'}`}`} 
                            />
                          </div>
                          
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between mb-1">
                              <span className={`text-sm truncate ${!email.is_read ? `font-semibold ${darkMode ? 'text-gray-200' : 'text-gray-900'}` : `${darkMode ? 'text-gray-400' : 'text-gray-700'}`}`}>
                                {email.sender}
                              </span>
                              <div className="flex items-center gap-1">
                                <span className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>
                                  {formatDate(email.date)}
                                </span>
                              </div>
                            </div>
                            
                            <div 
                              className={`text-sm line-clamp-3 pl-2 border-l-2 ${colorSet.border} ${
                                !email.is_read 
                                  ? `${darkMode ? 'text-gray-300' : 'text-gray-700'}` 
                                  : `${darkMode ? 'text-gray-400' : 'text-gray-600'}`
                              }`}
                            >
                              <span className={!email.is_read ? "font-medium" : ""}>
                                {email.subject}:{" "}
                              </span>
                              {email.snippet}
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          )}

          {/* Email Content */}
          {showEmailContent && selectedEmail && (
            <div className={`flex-1 flex flex-col overflow-hidden ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
              <div className={`px-4 md:px-6 py-4 border-b ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    {isMobileView && (
                      <button 
                        onClick={handleBackToList}
                        className={`p-2 rounded-lg mr-1 ${darkMode ? 'text-gray-300 hover:bg-gray-700' : 'text-gray-600 hover:bg-gray-100'}`}
                      >
                        <ArrowLeft size={18} />
                      </button>
                    )}
                    <div>
                      <h1 className={`text-lg md:text-xl font-semibold ${darkMode ? 'text-gray-200' : 'text-gray-900'}`}>
                        {selectedEmail.subject}
                      </h1>
                      {selectedEmail.category && (
                        <div className="flex items-center mt-1">
                          {(() => {
                            const colorSet = categoryColors[selectedEmail.category as keyof typeof categoryColors] || {
                              bg: 'bg-gray-500',
                              bgLight: 'bg-gray-100',
                              text: 'text-gray-700',
                              darkBg: 'bg-gray-700',
                              darkText: 'text-gray-300'
                            };
                            return (
                              <span className={`text-xs px-2 py-0.5 rounded-full ${
                                darkMode 
                                  ? `${colorSet.darkBg} text-gray-200` 
                                  : `${colorSet.bgLight} ${colorSet.text}`
                              }`}>
                                {selectedEmail.category}
                              </span>
                            );
                          })()}
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-1 md:gap-2">
                    <button className={`p-2 rounded-lg transition-colors ${darkMode ? 'hover:bg-gray-700' : 'hover:bg-gray-100'}`}>
                      <Archive size={18} className={darkMode ? 'text-gray-400' : ''} />
                    </button>
                    <button className={`p-2 rounded-lg transition-colors ${darkMode ? 'hover:bg-gray-700' : 'hover:bg-gray-100'}`}>
                      <Trash2 size={18} className={darkMode ? 'text-gray-400' : ''} />
                    </button>
                    <button className={`p-2 rounded-lg transition-colors ${darkMode ? 'hover:bg-gray-700' : 'hover:bg-gray-100'}`}>
                      <MoreHorizontal size={18} className={darkMode ? 'text-gray-400' : ''} />
                    </button>
                  </div>
                </div>
                
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-yellow-500 rounded-full flex items-center justify-center text-white font-semibold">
                    {selectedEmail.sender.charAt(0).toUpperCase()}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className={`font-medium ${darkMode ? 'text-gray-200' : 'text-gray-900'}`}>
                        {selectedEmail.sender}
                      </span>
                    </div>
                    <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                      to {selectedEmail.recipient} • {formatDate(selectedEmail.date)}
                    </div>
                  </div>
                  <Star 
                    size={20}
                    onClick={() => toggleEmailStar(selectedEmail.id, !selectedEmail.is_starred)}
                    className={`cursor-pointer ${selectedEmail.is_starred ? 'fill-yellow-400 text-yellow-400' : `${darkMode ? 'text-gray-500 hover:text-yellow-400' : 'text-gray-300 hover:text-yellow-400'}`}`} 
                  />
                </div>
              </div>

              <div className="flex-1 p-4 md:p-6 overflow-y-auto">
                {formatEmailBody(selectedEmail)}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Compose Email Modal */}
      {showCompose && (
        <div className={`fixed inset-0 z-50 flex items-center justify-center p-4 ${darkMode ? 'bg-black/80' : 'bg-white/80'}`}>
          <div className={`w-full max-w-2xl bg-white rounded-lg shadow-lg overflow-hidden ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
            <div className={`px-4 py-3 border-b ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
              <h3 className={`text-lg font-semibold ${darkMode ? 'text-gray-200' : 'text-gray-900'}`}>
                {selectedEmail ? 'Reply' : 'Compose'} Email
              </h3>
            </div>
            
            <div className="p-4">
              <div className="mb-4">
                <label className={`block text-sm font-medium ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                  To
                </label>
                <input
                  type="text"
                  value={selectedEmail ? selectedEmail.sender : ''}
                  readOnly={!!selectedEmail}
                  className={`mt-1 w-full p-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-yellow-500 transition-all ${
                    darkMode 
                      ? 'bg-gray-700 text-gray-200 placeholder-gray-400 focus:bg-gray-600' 
                      : 'bg-gray-100 focus:bg-white'
                  }`}
                />
              </div>

              <div className="mb-4">
                <label className={`block text-sm font-medium ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                  Subject
                </label>
                <input
                  type="text"
                  placeholder="Enter subject"
                  className={`mt-1 w-full p-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-yellow-500 transition-all ${
                    darkMode 
                      ? 'bg-gray-700 text-gray-200 placeholder-gray-400 focus:bg-gray-600' 
                      : 'bg-gray-100 focus:bg-white'
                  }`}
                />
              </div>

              <div className="mb-4">
                <label className={`block text-sm font-medium ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                  Message
                </label>
                <div className={`mt-1 p-3 border rounded-lg ${darkMode ? 'bg-gray-700 text-gray-200' : 'bg-gray-50 text-gray-700'}`}>
                  <div className="min-h-[150px] max-h-[300px] overflow-auto">
                    <p className="text-gray-400 text-sm italic">
                      Start typing your message here...
                    </p>
                  </div>
                </div>
              </div>

              <div className="flex flex-col sm:flex-row gap-4">
                <button 
                  onClick={() => setShowCompose(false)}
                  className={`flex-1 px-4 py-2 rounded-lg font-semibold transition-all flex items-center justify-center gap-2 ${
                    darkMode 
                      ? 'bg-gray-700 text-gray-300 hover:bg-gray-600' 
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  <X size={18} />
                  Cancel
                </button>
                
                <button 
                  className={`flex-1 px-4 py-2 rounded-lg font-semibold transition-all flex items-center justify-center gap-2 ${
                    darkMode 
                      ? 'bg-yellow-600 text-white hover:bg-yellow-500' 
                      : 'bg-yellow-100 text-yellow-700 hover:bg-yellow-200'
                  }`}
                >
                  <Send size={18} />
                  Send
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Settings Modal */}
      {showSettings && (
        <div className={`fixed inset-0 z-50 flex items-center justify-center p-4 ${darkMode ? 'bg-black/80' : 'bg-white/80'}`}>
          <div className={`w-full max-w-md bg-white rounded-lg shadow-lg overflow-hidden ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
            <div className={`px-4 py-3 border-b ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
              <h3 className={`text-lg font-semibold ${darkMode ? 'text-gray-200' : 'text-gray-900'}`}>
                Settings
              </h3>
            </div>
            
            <div className="p-4">
              <div className="mb-6">
                <h4 className={`text-md font-semibold ${darkMode ? 'text-gray-200' : 'text-gray-800'} mb-3`}>
                  Appearance
                </h4>
                <label className="flex items-center cursor-pointer">
                  <div className="relative">
                    <input
                      type="checkbox"
                      className="sr-only"
                      checked={darkMode}
                      onChange={() => setDarkMode(!darkMode)}
                    />
                    <div className={`block w-10 h-6 rounded-full ${darkMode ? 'bg-yellow-500' : 'bg-gray-200'}`}></div>
                    <div className={`dot absolute left-1 top-1 bg-white w-4 h-4 rounded-full transition-transform ${darkMode ? 'translate-x-full' : ''}`}></div>
                  </div>
                  <span className={`ml-3 text-sm font-medium ${darkMode ? 'text-gray-200' : 'text-gray-700'}`}>
                    Dark Mode
                  </span>
                </label>
              </div>

              <div className="mb-4">
                <h4 className={`text-md font-semibold ${darkMode ? 'text-gray-200' : 'text-gray-800'}`}>
                  Account
                </h4>
                <div className={`mt-2 ${darkMode ? 'bg-gray-700' : 'bg-gray-50'} p-3 rounded-lg border`}>
                  <div className="flex items-center justify-between mb-2">
                    <span className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                      Name
                    </span>
                    <span className={`text-sm font-semibold ${darkMode ? 'text-gray-200' : 'text-gray-800'}`}>
                      {user?.name || 'Not set'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                      Email
                    </span>
                    <span className={`text-sm font-semibold ${darkMode ? 'text-gray-200' : 'text-gray-800'}`}>
                      {user?.email}
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex flex-col gap-2">
                <button 
                  onClick={() => setShowSettings(false)}
                  className={`px-4 py-2 rounded-lg font-semibold transition-all ${
                    darkMode 
                      ? 'bg-yellow-600 text-white hover:bg-yellow-500' 
                      : 'bg-yellow-100 text-yellow-700 hover:bg-yellow-200'
                  }`}
                >
                  Close
                </button>
                
                <button 
                  onClick={handleLogout}
                  className={`px-4 py-2 rounded-lg font-semibold transition-all ${
                    darkMode 
                      ? 'bg-red-600 text-white hover:bg-red-500' 
                      : 'bg-red-100 text-red-700 hover:bg-red-200'
                  }`}
                >
                  Logout
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* AI Overview Modal */}
      {showAIOverview && (
        <div className={`fixed inset-0 z-50 flex items-center justify-center p-4 ${darkMode ? 'bg-black/80' : 'bg-white/80'}`}>
          <div className={`w-full max-w-3xl bg-white rounded-lg shadow-lg overflow-hidden ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
            <div className={`px-4 py-3 border-b ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
              <h3 className={`text-lg font-semibold ${darkMode ? 'text-gray-200' : 'text-gray-900'}`}>
                AI Overview
              </h3>
            </div>
            
            <div className="p-4">
              <div className={`mb-4 p-4 rounded-lg border ${darkMode ? 'bg-gray-700 border-gray-600' : 'bg-gray-50 border-gray-200'}`}>
                <h4 className={`text-md font-semibold ${darkMode ? 'text-gray-200' : 'text-gray-800'}`}>
                  Summary
                </h4>
                <p className={`mt-2 text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                  Velocitas is an innovative email client that enhances your productivity with AI-driven insights and a sleek, modern interface.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className={`p-4 rounded-lg border ${darkMode ? 'bg-gray-700 border-gray-600' : 'bg-gray-50 border-gray-200'}`}>
                  <h5 className={`font-semibold ${darkMode ? 'text-gray-200' : 'text-gray-800'}`}>
                    AI-Powered Insights
                  </h5>
                  <p className={`mt-2 text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                    Get intelligent insights about your emails, including sentiment analysis, urgency detection, and more.
                  </p>
                </div>

                <div className={`p-4 rounded-lg border ${darkMode ? 'bg-gray-700 border-gray-600' : 'bg-gray-50 border-gray-200'}`}>
                  <h5 className={`font-semibold ${darkMode ? 'text-gray-200' : 'text-gray-800'}`}>
                    Smart Compose
                  </h5>
                  <p className={`mt-2 text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                    Let our AI assist you in composing emails faster with smart suggestions and auto-completion.
                  </p>
                </div>

                <div className={`p-4 rounded-lg border ${darkMode ? 'bg-gray-700 border-gray-600' : 'bg-gray-50 border-gray-200'}`}>
                  <h5 className={`font-semibold ${darkMode ? 'text-gray-200' : 'text-gray-800'}`}>
                    Meeting Scheduler
                  </h5>
                  <p className={`mt-2 text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                    Easily schedule meetings by finding common availability with your contacts.
                  </p>
                </div>

                <div className={`p-4 rounded-lg border ${darkMode ? 'bg-gray-700 border-gray-600' : 'bg-gray-50 border-gray-200'}`}>
                  <h5 className={`font-semibold ${darkMode ? 'text-gray-200' : 'text-gray-800'}`}>
                    Task Automation
                  </h5>
                  <p className={`mt-2 text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                    Automate repetitive tasks like sorting emails, setting reminders, and more.
                  </p>
                </div>
              </div>

              <div className="mt-6 flex justify-center">
                <button 
                  onClick={() => setShowAIOverview(false)}
                  className={`px-4 py-2 rounded-lg font-semibold transition-all flex items-center justify-center gap-2 ${
                    darkMode 
                      ? 'bg-yellow-600 text-white hover:bg-yellow-500' 
                      : 'bg-yellow-100 text-yellow-700 hover:bg-yellow-200'
                  }`}
                >
                  Got it!
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
