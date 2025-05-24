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
  BrainCircuit
} from 'lucide-react';

// Mock email data
const mockEmails = [
  {
    id: 1,
    sender: "Sarah Chen",
    email: "sarah.chen@company.com",
    subject: "Q4 Marketing Strategy Review",
    preview: "Hi team, I've attached the Q4 marketing strategy document for your review. Please let me know your thoughts by Friday...",
    time: "2:30 PM",
    isRead: false,
    isStarred: true,
    hasAttachment: true,
    label: "Work"
  },
  {
    id: 2,
    sender: "GitHub",
    email: "noreply@github.com",
    subject: "Security alert: New sign-in from Chrome on Windows",
    preview: "We noticed a new sign-in to your GitHub account from a device we don't recognize...",
    time: "1:15 PM",
    isRead: false,
    isStarred: false,
    hasAttachment: false,
    label: "Updates"
  },
  {
    id: 3,
    sender: "Alex Rodriguez",
    email: "alex.r@startup.io",
    subject: "Coffee catch-up next week?",
    preview: "Hey! Hope you're doing well. Would you be interested in grabbing coffee next week to discuss the new project...",
    time: "11:45 AM",
    isRead: true,
    isStarred: false,
    hasAttachment: false,
    label: "Personal"
  },
  {
    id: 4,
    sender: "Figma",
    email: "team@figma.com",
    subject: "Your design system is ready for review",
    preview: "The design system you've been working on has been updated and is ready for team review...",
    time: "10:20 AM",
    isRead: true,
    isStarred: true,
    hasAttachment: true,
    label: "Design"
  },
  {
    id: 5,
    sender: "LinkedIn",
    email: "notifications@linkedin.com",
    subject: "5 new profile views this week",
    preview: "Your LinkedIn profile has been viewed 5 times this week. See who's been checking out your profile...",
    time: "Yesterday",
    isRead: true,
    isStarred: false,
    hasAttachment: false,
    label: "Social"
  }
];

const sidebarItems = [
  { icon: Inbox, label: "Inbox", count: 12, active: true },
  { icon: Star, label: "Starred", count: 3 },
  { icon: FileText, label: "Drafts", count: 1 },
  { icon: Mail, label: "Sent" },
  { icon: Archive, label: "Archive" },
  { icon: AlertCircle, label: "Spam", count: 2 },
  { icon: Trash2, label: "Trash" },
];

// First, let's define our category colors in one place for consistency
const categoryColors = {
  Work: {
    bg: 'bg-blue-500',
    bgLight: 'bg-blue-100',
    text: 'text-blue-700',
    darkBg: 'bg-blue-800',
    darkText: 'text-blue-300',
    border: 'border-blue-200'
  },
  Personal: {
    bg: 'bg-green-500',
    bgLight: 'bg-green-100',
    text: 'text-green-700',
    darkBg: 'bg-green-800',
    darkText: 'text-green-300',
    border: 'border-green-200'
  },
  Finance: {
    bg: 'bg-purple-500',
    bgLight: 'bg-purple-100',
    text: 'text-purple-700',
    darkBg: 'bg-purple-800',
    darkText: 'text-purple-300',
    border: 'border-purple-200'
  },
  Updates: {
    bg: 'bg-orange-500',
    bgLight: 'bg-orange-100',
    text: 'text-orange-700',
    darkBg: 'bg-orange-800', 
    darkText: 'text-orange-300',
    border: 'border-orange-200'
  },
  Social: {
    bg: 'bg-pink-500',
    bgLight: 'bg-pink-100',
    text: 'text-pink-700',
    darkBg: 'bg-pink-800',
    darkText: 'text-pink-300',
    border: 'border-pink-200'
  },
  Design: {
    bg: 'bg-indigo-500',
    bgLight: 'bg-indigo-100',
    text: 'text-indigo-700',
    darkBg: 'bg-indigo-800',
    darkText: 'text-indigo-300',
    border: 'border-indigo-200'
  }
};

export default function GmailInterface() {
  const [selectedEmail, setSelectedEmail] = useState(mockEmails[0]);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [showCompose, setShowCompose] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const [isMobileView, setIsMobileView] = useState(false);
  const [showEmailList, setShowEmailList] = useState(true);
  const [showEmailContent, setShowEmailContent] = useState(false);
  const [showAIOverview, setShowAIOverview] = useState(false);

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

  // Handle email selection in mobile view
  const handleEmailSelect = (email: typeof mockEmails[number]) => {
    setSelectedEmail(email);
    if (isMobileView) {
      setShowEmailList(false);
      setShowEmailContent(true);
    }
  };

  // Go back to email list in mobile view
  const handleBackToList = () => {
    setShowEmailList(true);
    setShowEmailContent(false);
  };

  return (
    <div className={`h-screen flex overflow-hidden ${darkMode ? 'dark bg-gray-900' : 'bg-white'}`}>
      {/* Sidebar - responsive */}
      <div className={`${sidebarOpen ? 'w-64' : 'w-16'} ${isMobileView && !sidebarOpen ? 'hidden' : ''} ${darkMode ? 'bg-gray-800 border-gray-700' : 'bg-gray-50 border-gray-200'} border-r transition-all duration-300 flex flex-col`}>
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
        
        {/* Settings - Fixed alignment */}
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
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header - with menu button removed */}
        <header className={`border-b px-4 md:px-6 py-4 flex items-center gap-3 md:gap-4 ${darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`}>
          <div className="flex-1 max-w-2xl flex items-center gap-3">
            <div className="relative flex-1">
              <Search className={`absolute left-3 top-1/2 transform -translate-y-1/2 ${darkMode ? 'text-gray-400' : 'text-gray-400'}`} size={18} />
              <input
                type="text"
                placeholder="Search mail"
                className={`w-full pl-10 pr-4 py-2 border-0 rounded-lg focus:outline-none focus:ring-2 focus:ring-yellow-500 transition-all ${
                  darkMode 
                    ? 'bg-gray-700 text-gray-200 placeholder-gray-400 focus:bg-gray-600' 
                    : 'bg-gray-100 focus:bg-white'
                }`}
              />
            </div>
            
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

          {/* Compose button */}
          <button 
            onClick={() => setShowCompose(true)}
            className="flex items-center gap-2 px-3 py-2 bg-yellow-500 hover:bg-yellow-600 text-white rounded-lg transition-all duration-200 shadow-sm"
          >
            <Plus size={16} />
            <span className="hidden sm:inline font-medium">Compose</span>
          </button>
          
          {/* Settings button */}
          <button 
            onClick={() => setShowSettings(true)}
            className={`p-2 rounded-lg transition-colors ${darkMode ? 'hover:bg-gray-700' : 'hover:bg-gray-100'}`}
          >
            <Settings size={20} className={darkMode ? 'text-gray-300' : ''} />
          </button>
        </header>

        <div className="flex-1 flex overflow-hidden">
          {/* Email List - with color coded categories and summarized content */}
          {showEmailList && (
            <div className={`${isMobileView ? 'w-full' : 'w-80 lg:w-96'} border-r flex flex-col ${darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`}>
              {/* List Header */}
              <div className={`px-4 py-3 border-b flex items-center justify-between ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
                <h2 className={`font-semibold ${darkMode ? 'text-gray-200' : 'text-gray-900'}`}>Inbox</h2>
                <div className="flex items-center gap-2">
                  <button className={`p-1 rounded ${darkMode ? 'hover:bg-gray-700' : 'hover:bg-gray-100'}`}>
                    <ChevronLeft size={16} className={darkMode ? 'text-gray-400' : ''} />
                  </button>
                  <span className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>1-50 of 1,234</span>
                  <button className={`p-1 rounded ${darkMode ? 'hover:bg-gray-700' : 'hover:bg-gray-100'}`}>
                    <ChevronRight size={16} className={darkMode ? 'text-gray-400' : ''} />
                  </button>
                </div>
              </div>

              {/* Email Items */}
              <div className="flex-1 overflow-y-auto">
                {mockEmails.map((email) => {
                  // Get the color theme for this email's category
                  const colorSet = categoryColors[email.label as keyof typeof categoryColors] || {
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
                        selectedEmail.id === email.id 
                          ? `bg-yellow-50 border-yellow-200 ${darkMode ? 'dark:bg-yellow-900/20 dark:border-yellow-800' : ''}` 
                          : `border-gray-100 ${darkMode ? 'hover:bg-gray-700 border-gray-700' : 'hover:bg-gray-50'}`
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        <div className="flex items-center gap-2 mt-1">
                          <Star 
                            size={16} 
                            className={`cursor-pointer ${email.isStarred ? 'fill-yellow-400 text-yellow-400' : `${darkMode ? 'text-gray-500 hover:text-yellow-400' : 'text-gray-300 hover:text-yellow-400'}`}`} 
                          />
                        </div>
                        
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between mb-1">
                            <span className={`text-sm truncate ${!email.isRead ? `font-semibold ${darkMode ? 'text-gray-200' : 'text-gray-900'}` : `${darkMode ? 'text-gray-400' : 'text-gray-700'}`}`}>
                              {email.sender}
                            </span>
                            <div className="flex items-center gap-1">
                              {email.hasAttachment && <Paperclip size={14} className={darkMode ? 'text-gray-500' : 'text-gray-400'} />}
                              <span className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>{email.time}</span>
                            </div>
                          </div>
                          
                          {/* Summarized content with colored left border - kept the border but removed category label */}
                          <div 
                            className={`text-sm line-clamp-3 pl-2 border-l-2 ${colorSet.border} ${
                              !email.isRead 
                                ? `${darkMode ? 'text-gray-300' : 'text-gray-700'}` 
                                : `${darkMode ? 'text-gray-400' : 'text-gray-600'}`
                            }`}
                          >
                            <span className={!email.isRead ? "font-medium" : ""}>
                              {email.subject}:{" "}
                            </span>
                            {email.preview}
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Email Content */}
          {showEmailContent && (
            <div className={`flex-1 flex flex-col overflow-hidden ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
              {selectedEmail && (
                <>
                  {/* Email Header - with back button for mobile */}
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
                          {/* Add category label here */}
                          <div className="flex items-center mt-1">
                            {(() => {
                              const colorSet = categoryColors[selectedEmail.label as keyof typeof categoryColors] || {
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
                                  {selectedEmail.label}
                                </span>
                              );
                            })()}
                          </div>
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
                        {selectedEmail.sender.charAt(0)}
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className={`font-medium ${darkMode ? 'text-gray-200' : 'text-gray-900'}`}>{selectedEmail.sender}</span>
                          <span className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>&lt;{selectedEmail.email}&gt;</span>
                        </div>
                        <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                          to me • {selectedEmail.time}
                        </div>
                      </div>
                      <Star 
                        size={20} 
                        className={`cursor-pointer ${selectedEmail.isStarred ? 'fill-yellow-400 text-yellow-400' : `${darkMode ? 'text-gray-500 hover:text-yellow-400' : 'text-gray-300 hover:text-yellow-400'}`}`} 
                      />
                    </div>
                  </div>

                  {/* Email Body */}
                  <div className="flex-1 px-4 md:px-6 py-6 overflow-y-auto">
                    <div className="prose max-w-none">
                      <p className={`leading-relaxed mb-4 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                        {selectedEmail.preview}
                      </p>
                      <p className={`leading-relaxed mb-4 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                        Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.
                      </p>
                      <p className={`leading-relaxed mb-6 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                        Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.
                      </p>
                      
                      {selectedEmail.hasAttachment && (
                        <div className={`border rounded-lg p-4 mb-6 ${darkMode ? 'border-gray-600' : 'border-gray-200'}`}>
                          <div className="flex items-center gap-3">
                            <Paperclip size={20} className={darkMode ? 'text-gray-400' : 'text-gray-400'} />
                            <div>
                              <div className={`font-medium ${darkMode ? 'text-gray-200' : 'text-gray-900'}`}>Q4_Marketing_Strategy.pdf</div>
                              <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>2.4 MB</div>
                            </div>
                          </div>
                        </div>
                      )}
                      
                      <p className={`leading-relaxed ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                        Best regards,<br />
                        {selectedEmail.sender}
                      </p>
                    </div>
                  </div>

                  {/* Reply Actions */}
                  <div className={`px-4 md:px-6 py-4 border-t flex items-center gap-2 md:gap-3 ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
                    <button className="flex items-center gap-1 md:gap-2 px-3 md:px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 transition-colors">
                      <Reply size={16} />
                      <span className="hidden sm:inline">Reply</span>
                    </button>
                    <button className={`flex items-center gap-1 md:gap-2 px-3 md:px-4 py-2 border rounded-lg transition-colors ${darkMode ? 'border-gray-600 text-gray-300 hover:bg-gray-700' : 'border-gray-300 text-gray-700 hover:bg-gray-50'}`}>
                      <ReplyAll size={16} />
                      <span className="hidden sm:inline">Reply All</span>
                    </button>
                    <button className={`flex items-center gap-1 md:gap-2 px-3 md:px-4 py-2 border rounded-lg transition-colors ${darkMode ? 'border-gray-600 text-gray-300 hover:bg-gray-700' : 'border-gray-300 text-gray-700 hover:bg-gray-50'}`}>
                      <Forward size={16} />
                      <span className="hidden sm:inline">Forward</span>
                    </button>
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Settings Modal */}
      {showSettings && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className={`rounded-lg shadow-xl w-full max-w-md mx-4 ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
            <div className={`flex items-center justify-between px-6 py-4 border-b ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
              <h3 className={`font-semibold ${darkMode ? 'text-gray-200' : 'text-gray-900'}`}>Settings</h3>
              <button 
                onClick={() => setShowSettings(false)}
                className={`rounded-lg p-1 transition-colors ${darkMode ? 'text-gray-400 hover:text-gray-200 hover:bg-gray-700' : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100'}`}
              >
                <X size={20} />
              </button>
            </div>
            
            <div className="p-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {darkMode ? <Moon size={20} className="text-gray-400" /> : <Sun size={20} className="text-gray-600" />}
                  <div>
                    <div className={`font-medium ${darkMode ? 'text-gray-200' : 'text-gray-900'}`}>Dark Mode</div>
                    <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>Toggle dark mode theme</div>
                  </div>
                </div>
                <button
                  onClick={() => setDarkMode(!darkMode)}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${darkMode ? 'bg-yellow-500' : 'bg-gray-300'}`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${darkMode ? 'translate-x-6' : 'translate-x-1'}`}
                  />
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Compose Modal */}
      {showCompose && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className={`rounded-lg shadow-xl w-full max-w-2xl mx-4 ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
            <div className={`flex items-center justify-between px-6 py-4 border-b ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
              <h3 className={`font-semibold ${darkMode ? 'text-gray-200' : 'text-gray-900'}`}>New Message</h3>
              <button 
                onClick={() => setShowCompose(false)}
                className={`rounded-lg p-1 transition-colors ${darkMode ? 'text-gray-400 hover:text-gray-200 hover:bg-gray-700' : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100'}`}
              >
                <X size={20} />
              </button>
            </div>
            
            <div className="p-6 space-y-4">
              <div>
                <input
                  type="email"
                  placeholder="To"
                  className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-yellow-500 ${darkMode ? 'bg-gray-700 border-gray-600 text-gray-200 placeholder-gray-400' : 'border-gray-300'}`}
                />
              </div>
              <div>
                <input
                  type="text"
                  placeholder="Subject"
                  className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-yellow-500 ${darkMode ? 'bg-gray-700 border-gray-600 text-gray-200 placeholder-gray-400' : 'border-gray-300'}`}
                />
              </div>
              <div>
                <textarea
                  rows={12}
                  placeholder="Compose your message..."
                  className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-yellow-500 resize-none ${darkMode ? 'bg-gray-700 border-gray-600 text-gray-200 placeholder-gray-400' : 'border-gray-300'}`}
                />
              </div>
            </div>
            
            <div className={`flex items-center justify-between px-6 py-4 border-t ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
              <div className="flex items-center gap-3">
                <button className="flex items-center gap-2 px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 transition-colors">
                  <Send size={16} />
                  Send
                </button>
                <button className={`p-2 transition-colors ${darkMode ? 'text-gray-400 hover:text-gray-200' : 'text-gray-400 hover:text-gray-600'}`}>
                  <Paperclip size={18} />
                </button>
              </div>
              <button 
                onClick={() => setShowCompose(false)}
                className={`px-4 py-2 transition-colors ${darkMode ? 'text-gray-400 hover:text-gray-200' : 'text-gray-600 hover:text-gray-800'}`}
              >
                Discard
              </button>
            </div>
          </div>
        </div>
      )}

      {/* AI Overview Modal */}
      {showAIOverview && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className={`rounded-lg shadow-xl w-full max-w-2xl mx-4 ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
            <div className={`flex items-center justify-between px-6 py-4 border-b ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
              <h3 className={`font-semibold flex items-center gap-2 ${darkMode ? 'text-gray-200' : 'text-gray-900'}`}>
                <BrainCircuit size={20} className={darkMode ? 'text-yellow-400' : 'text-yellow-600'} />
                Email AI Overview
              </h3>
              <button 
                onClick={() => setShowAIOverview(false)}
                className={`rounded-lg p-1 transition-colors ${darkMode ? 'text-gray-400 hover:text-gray-200 hover:bg-gray-700' : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100'}`}
              >
                <X size={20} />
              </button>
            </div>
            
            <div className="p-6 space-y-6 max-h-[70vh] overflow-y-auto">
              {/* Summary Section */}
              <div>
                <h4 className={`text-lg font-medium mb-3 ${darkMode ? 'text-gray-200' : 'text-gray-900'}`}>
                  Today's Summary
                </h4>
                <div className={`p-4 rounded-lg ${darkMode ? 'bg-gray-700' : 'bg-gray-50'}`}>
                  <p className={`${darkMode ? 'text-gray-300' : 'text-gray-700'} mb-3`}>
                    You have <span className="font-medium">2 unread emails</span> and <span className="font-medium">1 email</span> requiring your response today.
                  </p>
                  <div className="flex flex-wrap gap-2">
                    <span className={`text-xs px-2 py-1 rounded-full ${darkMode ? 'bg-blue-800 text-blue-200' : 'bg-blue-100 text-blue-800'}`}>
                      2 Work emails
                    </span>
                    <span className={`text-xs px-2 py-1 rounded-full ${darkMode ? 'bg-green-800 text-green-200' : 'bg-green-100 text-green-800'}`}>
                      1 Personal email
                    </span>
                    <span className={`text-xs px-2 py-1 rounded-full ${darkMode ? 'bg-orange-800 text-orange-200' : 'bg-orange-100 text-orange-800'}`}>
                      2 Update notifications
                    </span>
                  </div>
                </div>
              </div>
              
              {/* Priority Emails */}
              <div>
                <h4 className={`text-lg font-medium mb-3 ${darkMode ? 'text-gray-200' : 'text-gray-900'}`}>
                  Priority Emails
                </h4>
                <div className={`space-y-3`}>
                  <div className={`p-4 rounded-lg border-l-4 border-yellow-500 ${darkMode ? 'bg-gray-700' : 'bg-gray-50'}`}>
                    <div className="flex justify-between mb-1">
                      <span className={`font-medium ${darkMode ? 'text-gray-200' : 'text-gray-900'}`}>Q4 Marketing Strategy Review</span>
                      <span className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>2:30 PM</span>
                    </div>
                    <p className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                      Sarah Chen needs your review on the marketing documents by Friday.
                    </p>
                  </div>
                  
                  <div className={`p-4 rounded-lg border-l-4 border-red-500 ${darkMode ? 'bg-gray-700' : 'bg-gray-50'}`}>
                    <div className="flex justify-between mb-1">
                      <span className={`font-medium ${darkMode ? 'text-gray-200' : 'text-gray-900'}`}>Security alert</span>
                      <span className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>1:15 PM</span>
                    </div>
                    <p className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                      GitHub detected a new sign-in to your account. Verify this was you.
                    </p>
                  </div>
                </div>
              </div>
              
              {/* Recent Activity */}
              <div>
                <h4 className={`text-lg font-medium mb-3 ${darkMode ? 'text-gray-200' : 'text-gray-900'}`}>
                  Recent Activity
                </h4>
                <div className={`space-y-1 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                  <div className="flex items-center gap-2 py-2">
                    <div className={`w-2 h-2 rounded-full bg-blue-500`}></div>
                    <span>Three work emails received in the last 24 hours</span>
                  </div>
                  <div className="flex items-center gap-2 py-2">
                    <div className={`w-2 h-2 rounded-full bg-green-500`}></div>
                    <span>Alex Rodriguez is waiting for your reply about the coffee meeting</span>
                  </div>
                  <div className="flex items-center gap-2 py-2">
                    <div className={`w-2 h-2 rounded-full bg-indigo-500`}></div>
                    <span>Design system from Figma is ready for your review</span>
                  </div>
                </div>
              </div>
              
              {/* Smart Actions */}
              <div>
                <h4 className={`text-lg font-medium mb-3 ${darkMode ? 'text-gray-200' : 'text-gray-900'}`}>
                  Suggested Actions
                </h4>
                <div className="flex flex-wrap gap-2">
                  <button className={`px-3 py-2 rounded-lg transition-colors ${darkMode ? 'bg-gray-700 hover:bg-gray-600 text-gray-200' : 'bg-gray-100 hover:bg-gray-200 text-gray-800'}`}>
                    Review Q4 strategy
                  </button>
                  <button className={`px-3 py-2 rounded-lg transition-colors ${darkMode ? 'bg-gray-700 hover:bg-gray-600 text-gray-200' : 'bg-gray-100 hover:bg-gray-200 text-gray-800'}`}>
                    Respond to Alex
                  </button>
                  <button className={`px-3 py-2 rounded-lg transition-colors ${darkMode ? 'bg-gray-700 hover:bg-gray-600 text-gray-200' : 'bg-gray-100 hover:bg-gray-200 text-gray-800'}`}>
                    Check security alert
                  </button>
                </div>
              </div>
            </div>
            
            <div className={`flex items-center justify-end gap-3 px-6 py-4 border-t ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
              <button 
                onClick={() => setShowAIOverview(false)}
                className={`px-4 py-2 rounded-lg ${darkMode ? 'text-gray-300 hover:bg-gray-700' : 'text-gray-600 hover:bg-gray-100'}`}
              >
                Close
              </button>
              <button className={`px-4 py-2 rounded-lg bg-yellow-500 hover:bg-yellow-600 text-white`}>
                Process All
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}