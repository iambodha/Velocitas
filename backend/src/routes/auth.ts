import express from 'express';
import { supabase } from '../auth/supabase';
import { getGoogleAuthUrl, getGoogleTokens, getGoogleUserInfo } from '../auth/google-oauth';
import { authMiddleware, AuthRequest } from '../middleware/auth';
import { OAuth2Client } from 'google-auth-library';
import { google } from 'googleapis';

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

// Handle Google OAuth callback (GET route for browser redirect)
router.get('/google/callback', async (req, res) => {
  try {
    const { code, state } = req.query;

    if (!code) {
      return res.status(400).send('Authorization code not provided');
    }

    // For now, just display the code - you'll need to handle this properly
    res.send(`
      <html>
        <body>
          <h2>OAuth Success!</h2>
          <p>Authorization code received:</p>
          <code>${code}</code>
          <br><br>
          <p>Copy this code and use it in your application.</p>
          <script>
            // Auto-copy code to clipboard
            navigator.clipboard.writeText('${code}');
            alert('Code copied to clipboard!');
          </script>
        </body>
      </html>
    `);
  } catch (error) {
    res.status(500).send('Error processing OAuth callback');
  }
});

// Handle Google OAuth callback (POST route for API)
router.post('/google/callback', authMiddleware, async (req: AuthRequest, res) => {
  try {
    const { code } = req.body;
    const userId = req.user?.id;

    if (!userId) {
      return res.status(401).json({ error: 'User not authenticated' });
    }

    if (!code) {
      return res.status(400).json({ error: 'Authorization code is required' });
    }

    // Exchange code for tokens
    const auth = new OAuth2Client(
      process.env.GOOGLE_CLIENT_ID,
      process.env.GOOGLE_CLIENT_SECRET,
      process.env.GOOGLE_REDIRECT_URI
    );

    const { tokens } = await auth.getToken(code);
    
    console.log('Received tokens from Google:', {
      hasAccessToken: !!tokens.access_token,
      hasRefreshToken: !!tokens.refresh_token,
      expiryDate: tokens.expiry_date
    });
    
    if (!tokens.refresh_token) {
      return res.status(400).json({ 
        error: 'No refresh token received. User may need to revoke access and re-authorize.' 
      });
    }

    // Get user info from Google
    auth.setCredentials(tokens);
    const oauth2 = google.oauth2({ version: 'v2', auth });
    const { data: googleUser } = await oauth2.userinfo.get();

    // Save/update tokens in user_google_tokens table
    const tokenData = {
      user_id: userId,
      access_token: tokens.access_token!,
      refresh_token: tokens.refresh_token,
      expires_at: tokens.expiry_date!, // Keep as number, don't convert to ISO string
      google_email: googleUser.email,
      google_id: googleUser.id,
      updated_at: new Date().toISOString()
    };

    console.log('Saving token data:', {
      user_id: tokenData.user_id,
      hasAccessToken: !!tokenData.access_token,
      hasRefreshToken: !!tokenData.refresh_token,
      expires_at: tokenData.expires_at,
      expires_at_readable: new Date(tokenData.expires_at).toISOString(), // For debugging
      google_email: tokenData.google_email
    });

    const { data: savedTokens, error: tokenError } = await supabase
      .from('user_google_tokens')
      .upsert(tokenData, {
        onConflict: 'user_id'
      })
      .select();

    if (tokenError) {
      console.error('Error saving Google tokens:', tokenError);
      return res.status(500).json({ error: 'Failed to save Google tokens' });
    }

    console.log('Tokens saved successfully:', savedTokens);

    // Verify tokens were saved by reading them back
    const { data: verifyTokens, error: verifyError } = await supabase
      .from('user_google_tokens')
      .select('*')
      .eq('user_id', userId)
      .single();

    if (verifyError) {
      console.error('Error verifying saved tokens:', verifyError);
    } else {
      console.log('Verified saved tokens:', {
        hasAccessToken: !!verifyTokens.access_token,
        hasRefreshToken: !!verifyTokens.refresh_token,
        expires_at: verifyTokens.expires_at
      });
    }

    // Update user profile with Google info
    const { error: profileError } = await supabase
      .from('profiles')
      .update({
        google_email: googleUser.email,
        google_name: googleUser.name,
        google_picture: googleUser.picture,
        updated_at: new Date().toISOString()
      })
      .eq('id', userId);

    if (profileError) {
      console.error('Error updating profile:', profileError);
    }

    console.log('Google authorization completed successfully for user:', userId);

    res.json({
      message: 'Google account connected successfully',
      googleUser: {
        email: googleUser.email,
        name: googleUser.name,
        picture: googleUser.picture
      }
    });

  } catch (error) {
    console.error('Google callback error:', error);
    res.status(500).json({ error: 'Failed to process Google authorization' });
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