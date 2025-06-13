"use client";

import { useState, useEffect } from 'react';
import { 
  Mail, 
  BrainCircuit, 
  Zap, 
  Shield, 
  Users, 
  ArrowRight,
  Check,
  Star,
  Moon,
  Sun,
  Sparkles,
  TrendingUp,
  Clock,
  ChevronDown
} from 'lucide-react';

interface LandingPageProps {
  onGetStarted: () => void;
  darkMode: boolean;
  setDarkMode: (dark: boolean) => void;
}

export default function LandingPage({ onGetStarted, darkMode, setDarkMode }: LandingPageProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [animatedStats, setAnimatedStats] = useState({ users: 0, emails: 0, time: 0 });

  // Animate stats on mount
  useEffect(() => {
    const duration = 2000;
    const steps = 60;
    const interval = duration / steps;
    let step = 0;

    const timer = setInterval(() => {
      step++;
      const progress = step / steps;
      setAnimatedStats({
        users: Math.floor(progress * 4), // Changed from 12000 to 4
        emails: Math.floor(progress * 998), // Changed from 2500000 to 1000
        time: Math.floor(progress * 89)
      });

      if (step >= steps) {
        clearInterval(timer);
      }
    }, interval);

    return () => clearInterval(timer);
  }, []);

  const handleGetStarted = async () => {
    setIsLoading(true);
    try {
      await onGetStarted();
    } catch (error) {
      console.error('Authentication failed:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const features = [
    {
      icon: <BrainCircuit className="w-8 h-8" />,
      title: "AI-Powered Intelligence",
      description: "Advanced machine learning algorithms that understand context, priority, and sentiment to organize your inbox intelligently.",
      gradient: "from-purple-500 to-pink-500"
    },
    {
      icon: <Zap className="w-8 h-8" />,
      title: "Lightning Performance",
      description: "Built with modern technology for instant search, real-time updates, and seamless interactions across all your devices.",
      gradient: "from-yellow-500 to-orange-500"
    },
    {
      icon: <Shield className="w-8 h-8" />,
      title: "Enterprise Security",
      description: "Bank-level encryption, zero-knowledge architecture, and GDPR compliance ensure your data stays private and secure.",
      gradient: "from-green-500 to-emerald-500"
    },
    {
      icon: <Users className="w-8 h-8" />,
      title: "Team Collaboration",
      description: "Share insights, delegate tasks, and collaborate seamlessly with advanced team features and real-time synchronization.",
      gradient: "from-blue-500 to-cyan-500"
    }
  ];

  const testimonials = [
    {
      name: "Sarah Chen",
      role: "VP of Product at TechCorp",
      content: "Velocitas has completely transformed how our team manages communication. The AI categorization is incredibly accurate and has saved us countless hours.",
      rating: 5,
      avatar: "SC",
      company: "TechCorp"
    },
    {
      name: "Alex Rodriguez",
      role: "Startup Founder",
      content: "Finally, an email solution that actually understands priority. The time I've saved with Velocitas has allowed me to focus on growing my business.",
      rating: 5,
      avatar: "AR",
      company: "StartupX"
    },
    {
      name: "Emily Watson",
      role: "Creative Director",
      content: "The interface is not just beautiful—it's intuitive and powerful. Email management has never felt this effortless and enjoyable.",
      rating: 5,
      avatar: "EW",
      company: "Design Studio"
    }
  ];

  const stats = [
    { label: "Active Users", value: animatedStats.users.toLocaleString() + "+", icon: <Users className="w-5 h-5" /> },
    { label: "Emails Processed", value: animatedStats.emails.toLocaleString() + "+", icon: <Mail className="w-5 h-5" /> },
    { label: "Time Saved (avg %)", value: animatedStats.time + "%", icon: <Clock className="w-5 h-5" /> }
  ];

  return (
    <div className={`min-h-screen ${darkMode ? 'bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900' : 'bg-gradient-to-br from-white via-gray-50 to-white'} transition-all duration-500`}>
      {/* Animated background elements */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-20 left-10 w-72 h-72 bg-yellow-500/10 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute bottom-20 right-10 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl animate-pulse delay-1000"></div>
        <div className="absolute top-1/2 left-1/2 w-64 h-64 bg-blue-500/10 rounded-full blur-3xl animate-pulse delay-2000"></div>
      </div>

      {/* Header */}
      <header className={`relative backdrop-blur-lg border-b ${darkMode ? 'border-gray-700/50 bg-gray-900/50' : 'border-gray-200/50 bg-white/50'} px-6 py-4 sticky top-0 z-50`}>
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="relative">
              <div className="w-10 h-10 bg-gradient-to-br from-yellow-400 to-yellow-600 rounded-xl flex items-center justify-center shadow-lg">
                <Mail className="w-6 h-6 text-white" />
              </div>
              <div className="absolute inset-0 bg-gradient-to-br from-yellow-400 to-yellow-600 rounded-xl blur-lg opacity-20 animate-pulse"></div>
            </div>
            <span className="text-2xl font-bold bg-gradient-to-r from-yellow-400 to-yellow-600 bg-clip-text text-transparent">Velocitas</span>
          </div>
          
          <div className="flex items-center gap-6">
            <nav className="hidden md:flex items-center gap-6">
              <a href="#features" className={`transition-colors hover:text-yellow-400 ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>Features</a>
              <a href="#testimonials" className={`transition-colors hover:text-yellow-400 ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>Reviews</a>
            </nav>
            
            <button
              onClick={() => setDarkMode(!darkMode)}
              className={`p-2 rounded-lg transition-all hover:scale-110 ${darkMode ? 'hover:bg-gray-700/50' : 'hover:bg-gray-100/50'}`}
            >
              {darkMode ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
            </button>
            
            <button
              onClick={handleGetStarted}
              disabled={isLoading}
              className="px-6 py-3 bg-gradient-to-r from-yellow-500 to-yellow-600 hover:from-yellow-600 hover:to-yellow-700 text-white rounded-xl font-semibold transition-all transform hover:scale-105 hover:shadow-xl disabled:opacity-50 disabled:transform-none flex items-center gap-2 shadow-lg"
            >
              {isLoading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  Connecting...
                </>
              ) : (
                'Get Started'
              )}
            </button>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative px-6 py-24 lg:py-32">
        <div className="max-w-7xl mx-auto">
          <div className="text-center max-w-4xl mx-auto">
            <div className="mb-8 animate-fade-in">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-gradient-to-r from-yellow-500/20 to-yellow-600/20 border border-yellow-500/30 mb-6">
                <Sparkles className="w-4 h-4 text-yellow-400" />
                <span className={`text-sm font-medium ${darkMode ? 'text-yellow-300' : 'text-yellow-700'}`}>AI-Powered Email Revolution</span>
              </div>
              
              <h1 className="text-6xl lg:text-7xl font-bold mb-8 leading-tight">
                <span className="bg-gradient-to-r from-white via-yellow-100 to-yellow-200 bg-clip-text text-transparent animate-gradient">
                  Email Management
                </span>
                <br />
                <span className="bg-gradient-to-r from-yellow-400 via-yellow-500 to-yellow-600 bg-clip-text text-transparent animate-gradient">
                  Reimagined
                </span>
              </h1>
              
              <p className={`text-xl lg:text-2xl mb-12 leading-relaxed ${darkMode ? 'text-gray-300' : 'text-gray-600'} animate-fade-in-delay`}>
                Transform your inbox into an intelligent workspace with AI-powered organization, 
                <br className="hidden lg:block" />
                lightning-fast performance, and seamless collaboration.
              </p>
            </div>
            
            <div className="flex flex-col sm:flex-row gap-6 justify-center mb-16 animate-fade-in-delay-2">
              <button
                onClick={handleGetStarted}
                disabled={isLoading}
                className="group px-8 py-4 bg-gradient-to-r from-yellow-500 to-yellow-600 hover:from-yellow-600 hover:to-yellow-700 text-white rounded-xl font-semibold text-lg transition-all transform hover:scale-105 hover:shadow-2xl disabled:opacity-50 disabled:transform-none flex items-center justify-center gap-3 shadow-xl"
              >
                {isLoading ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    Connecting...
                  </>
                ) : (
                  <>
                    <svg width="24" height="24" fill="currentColor" viewBox="0 0 24 24" className="transition-transform group-hover:scale-110">
                      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                    </svg>
                    Connect with Google
                    <ArrowRight className="w-5 h-5 transition-transform group-hover:translate-x-1" />
                  </>
                )}
              </button>
              
              <button className={`group px-8 py-4 border-2 rounded-xl font-semibold text-lg transition-all hover:scale-105 hover:shadow-xl backdrop-blur-sm ${darkMode ? 'border-gray-600 hover:border-gray-500 bg-gray-800/20 text-white' : 'border-gray-300 hover:border-gray-400 bg-white/20 text-gray-900'}`}>
                <span className="flex items-center gap-2">
                  <span className={darkMode ? 'text-white' : 'text-gray-900'}>Watch Demo</span>
                  <div className="w-8 h-8 bg-gradient-to-r from-yellow-500 to-yellow-600 rounded-full flex items-center justify-center group-hover:scale-110 transition-transform">
                    <div className="w-0 h-0 border-l-[6px] border-l-white border-t-[4px] border-t-transparent border-b-[4px] border-b-transparent ml-0.5"></div>
                  </div>
                </span>
              </button>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-16">
              {stats.map((stat, index) => (
                <div key={index} className={`p-6 rounded-2xl backdrop-blur-lg ${darkMode ? 'bg-white/5 border border-white/10' : 'bg-black/5 border border-black/10'} transition-all hover:scale-105 hover:shadow-xl`}>
                  <div className="flex items-center justify-center gap-3 mb-2">
                    <div className="text-yellow-400">
                      {stat.icon}
                    </div>
                    <div className="text-3xl font-bold bg-gradient-to-r from-yellow-400 to-yellow-600 bg-clip-text text-transparent">
                      {stat.value}
                    </div>
                  </div>
                  <p className={`text-sm font-medium ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>{stat.label}</p>
                </div>
              ))}
            </div>

            {/* Feature Preview */}
            <div className={`max-w-5xl mx-auto rounded-3xl overflow-hidden shadow-2xl transition-all hover:shadow-3xl ${darkMode ? 'bg-gray-800/50 border border-gray-700/50' : 'bg-gray-50/50 border border-gray-200/50'} backdrop-blur-lg`}>
              <div className={`px-6 py-4 border-b flex items-center gap-3 ${darkMode ? 'border-gray-700/50 bg-gray-900/50' : 'border-gray-200/50 bg-white/50'}`}>
                <div className="flex gap-2">
                  <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse"></div>
                  <div className="w-3 h-3 bg-yellow-500 rounded-full animate-pulse delay-100"></div>
                  <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse delay-200"></div>
                </div>
                <span className={`text-sm font-medium ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>Velocitas Dashboard</span>
              </div>
              <div className="p-8">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {[
                    { color: 'blue', title: 'Priority', count: 5, desc: 'Q4 Strategy Review', gradient: 'from-blue-500 to-blue-600' },
                    { color: 'green', title: 'Personal', count: 3, desc: 'Coffee meeting invite', gradient: 'from-green-500 to-green-600' },
                    { color: 'orange', title: 'Updates', count: 7, desc: 'Security alerts', gradient: 'from-orange-500 to-orange-600' }
                  ].map((item, index) => (
                    <div key={index} className={`p-6 rounded-2xl ${darkMode ? 'bg-gray-700/50' : 'bg-white/50'} backdrop-blur-sm shadow-lg hover:shadow-xl transition-all hover:scale-105 border ${darkMode ? 'border-gray-600/30' : 'border-gray-200/30'}`}>
                      <div className="flex items-center gap-3 mb-3">
                        <div className={`w-4 h-4 bg-gradient-to-r ${item.gradient} rounded-full shadow-lg`}></div>
                        <span className={`font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>{item.title}</span>
                        <span className={`text-xs px-2 py-1 rounded-full bg-gradient-to-r ${item.gradient} text-white font-medium`}>{item.count}</span>
                      </div>
                      <p className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>{item.desc}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Scroll indicator */}
        <div className="absolute bottom-8 left-1/2 transform -translate-x-1/2 animate-bounce">
          <ChevronDown className={`w-6 h-6 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`} />
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className={`relative px-6 py-24 ${darkMode ? 'bg-gray-800/30' : 'bg-gray-50/30'} backdrop-blur-sm`}>
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-20">
            <h2 className="text-5xl font-bold mb-6 bg-gradient-to-r from-yellow-400 to-yellow-600 bg-clip-text text-transparent">
              Powerful Features
            </h2>
            <p className={`text-xl ${darkMode ? 'text-gray-300' : 'text-gray-600'} max-w-3xl mx-auto leading-relaxed`}>
              Everything you need to transform your inbox into an intelligent workspace that adapts to your workflow.
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {features.map((feature, index) => (
              <div key={index} className={`group p-8 rounded-3xl ${darkMode ? 'bg-gray-800/50 border border-gray-700/50' : 'bg-white/50 border border-gray-200/50'} backdrop-blur-lg shadow-xl hover:shadow-2xl transition-all duration-500 hover:scale-105`}>
                <div className={`w-16 h-16 bg-gradient-to-r ${feature.gradient} rounded-2xl flex items-center justify-center mb-6 shadow-lg group-hover:scale-110 transition-transform duration-300`}>
                  <div className="text-white">
                    {feature.icon}
                  </div>
                </div>
                <h3 className={`text-2xl font-bold mb-4 group-hover:text-yellow-400 transition-colors ${darkMode ? 'text-white' : 'text-gray-900'}`}>{feature.title}</h3>
                <p className={`${darkMode ? 'text-gray-300' : 'text-gray-600'} leading-relaxed`}>{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Testimonials Section */}
      <section id="testimonials" className="px-6 py-24">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-20">
            <h2 className="text-5xl font-bold mb-6 bg-gradient-to-r from-yellow-400 to-yellow-600 bg-clip-text text-transparent">
              Loved by Professionals
            </h2>
            <p className={`text-xl ${darkMode ? 'text-gray-300' : 'text-gray-600'} max-w-3xl mx-auto leading-relaxed`}>
              Join thousands of professionals who have transformed their email experience and boosted their productivity.
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {testimonials.map((testimonial, index) => (
              <div key={index} className={`group p-8 rounded-3xl ${darkMode ? 'bg-gray-800/50 border border-gray-700/50' : 'bg-white/50 border border-gray-200/50'} backdrop-blur-lg shadow-xl hover:shadow-2xl transition-all duration-500 hover:scale-105`}>
                <div className="flex mb-6">
                  {[...Array(testimonial.rating)].map((_, i) => (
                    <Star key={i} className="w-5 h-5 text-yellow-400 fill-current" />
                  ))}
                </div>
                <p className={`mb-6 text-lg leading-relaxed ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>"{testimonial.content}"</p>
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-gradient-to-r from-yellow-400 to-yellow-600 rounded-full flex items-center justify-center text-white font-bold text-sm">
                    {testimonial.avatar}
                  </div>
                  <div>
                    <div className={`font-bold text-lg ${darkMode ? 'text-white' : 'text-gray-900'}`}>{testimonial.name}</div>
                    <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>{testimonial.role}</div>
                    <div className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>{testimonial.company}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className={`px-6 py-24 ${darkMode ? 'bg-gradient-to-r from-gray-800 to-gray-900' : 'bg-gradient-to-r from-gray-50 to-white'}`}>
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-5xl font-bold mb-6 bg-gradient-to-r from-yellow-400 to-yellow-600 bg-clip-text text-transparent">
            Ready to Transform Your Inbox?
          </h2>
          <p className={`text-xl mb-12 leading-relaxed ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
            Join thousands of professionals who have revolutionized their email workflow. 
            Start your journey to inbox zero today.
          </p>
          
          <button
            onClick={handleGetStarted}
            disabled={isLoading}
            className="group px-12 py-5 bg-gradient-to-r from-yellow-500 to-yellow-600 hover:from-yellow-600 hover:to-yellow-700 text-white rounded-2xl font-bold text-xl transition-all transform hover:scale-105 hover:shadow-2xl disabled:opacity-50 disabled:transform-none flex items-center justify-center gap-3 mx-auto shadow-xl"
          >
            {isLoading ? (
              <>
                <div className="w-6 h-6 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                Connecting...
              </>
            ) : (
              <>
                Start Free Today
                <ArrowRight className="w-6 h-6 transition-transform group-hover:translate-x-1" />
              </>
            )}
          </button>
          
          <p className={`mt-6 text-sm ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
            No credit card required • Setup in under 2 minutes • Cancel anytime
          </p>
        </div>
      </section>

      {/* Footer */}
      <footer className={`border-t ${darkMode ? 'border-gray-700/50 bg-gray-900/50' : 'border-gray-200/50 bg-white/50'} backdrop-blur-lg px-6 py-12`}>
        <div className="max-w-7xl mx-auto text-center">
          <div className="flex items-center justify-center gap-3 mb-6">
            <div className="w-10 h-10 bg-gradient-to-br from-yellow-400 to-yellow-600 rounded-xl flex items-center justify-center shadow-lg">
              <Mail className="w-6 h-6 text-white" />
            </div>
            <span className="text-2xl font-bold bg-gradient-to-r from-yellow-400 to-yellow-600 bg-clip-text text-transparent">Velocitas</span>
          </div>
          <p className={`${darkMode ? 'text-gray-400' : 'text-gray-600'} mb-6`}>
            © 2025 Velocitas. All rights reserved. Revolutionizing email management with AI.
          </p>
          <div className="flex justify-center gap-8 text-sm">
            <a href="#" className={`transition-colors hover:text-yellow-400 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>Privacy Policy</a>
            <a href="#" className={`transition-colors hover:text-yellow-400 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>Terms of Service</a>
            <a href="#" className={`transition-colors hover:text-yellow-400 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>Support</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
