import express from 'express';
import { supabase } from '../auth/supabase';
import { getGoogleAuthUrl, getGoogleTokens, getGoogleUserInfo } from '../auth/google-oauth';
import { authMiddleware, AuthRequest } from '../middleware/auth';

const router = express.Router();

// Create Supabase account
router.post('/signup', async (req, res) => {
  try {
    const { email, password, name } = req.body;

    if (!email || !password || !name) {
      return res.status(400).json({ error: 'Email, password, and name are required' });
    }

    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: {
          name
        }
      }
    });

    if (error) {
      return res.status(400).json({ error: error.message });
    }

    res.json({
      message: 'Account created successfully',
      user: data.user,
      needsGoogleAuth: true
    });
  } catch (error) {
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Login to Supabase
router.post('/login', async (req, res) => {
  try {
    const { email, password } = req.body;

    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password
    });

    if (error) {
      return res.status(400).json({ error: error.message });
    }

    res.json({
      message: 'Login successful',
      user: data.user,
      session: data.session
    });
  } catch (error) {
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get Google OAuth URL
router.get('/google/url', authMiddleware, (req: AuthRequest, res) => {
  try {
    const authUrl = getGoogleAuthUrl();
    res.json({ authUrl });
  } catch (error) {
    res.status(500).json({ error: 'Failed to generate Google auth URL' });
  }
});

// Handle Google OAuth callback
router.post('/google/callback', authMiddleware, async (req: AuthRequest, res) => {
  try {
    const { code } = req.body;
    const userId = req.user?.id;

    if (!code) {
      return res.status(400).json({ error: 'Authorization code is required' });
    }

    // Get tokens from Google
    const tokens = await getGoogleTokens(code);
    
    // Get user info from Google
    const googleUser = await getGoogleUserInfo(tokens.access_token!);

    // Store Google tokens in Supabase
    const { error } = await supabase
      .from('user_google_tokens')
      .upsert({
        user_id: userId,
        access_token: tokens.access_token,
        refresh_token: tokens.refresh_token,
        expires_at: tokens.expiry_date,
        google_email: googleUser.email,
        google_id: googleUser.id
      });

    if (error) {
      return res.status(500).json({ error: 'Failed to store Google tokens' });
    }

    res.json({
      message: 'Google account connected successfully',
      googleUser: {
        email: googleUser.email,
        name: googleUser.name,
        picture: googleUser.picture
      }
    });
  } catch (error) {
    res.status(500).json({ error: 'Failed to connect Google account' });
  }
});

// Logout
router.post('/logout', authMiddleware, async (req: AuthRequest, res) => {
  try {
    const { error } = await supabase.auth.signOut();
    
    if (error) {
      return res.status(400).json({ error: error.message });
    }

    res.json({ message: 'Logged out successfully' });
  } catch (error) {
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;