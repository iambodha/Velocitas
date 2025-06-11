import express from 'express';
import { supabase } from '../auth/supabase';
import { authMiddleware, AuthRequest } from '../middleware/auth';

const router = express.Router();

// Get user profile
router.get('/profile', authMiddleware, async (req: AuthRequest, res) => {
  try {
    const userId = req.user?.id;

    // Get user data from auth.users (built-in Supabase table)
    const { data: userData, error: userError } = await supabase.auth.getUser();

    // Get Google connection status
    const { data: googleData, error: googleError } = await supabase
      .from('user_google_tokens')
      .select('google_email, google_id')
      .eq('user_id', userId)
      .single();

    res.json({
      user: req.user,
      googleConnected: !googleError && googleData !== null,
      googleEmail: googleData?.google_email || null
    });
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch user profile' });
  }
});

// Update user profile
router.put('/profile', authMiddleware, async (req: AuthRequest, res) => {
  try {
    const userId = req.user?.id;
    const { name, avatar_url } = req.body;

    // Update user metadata in Supabase Auth
    const { data, error } = await supabase.auth.updateUser({
      data: { name, avatar_url }
    });

    if (error) {
      return res.status(400).json({ error: error.message });
    }

    res.json({ message: 'Profile updated successfully', user: data.user });
  } catch (error) {
    res.status(500).json({ error: 'Failed to update profile' });
  }
});

// Disconnect Google account
router.delete('/google', authMiddleware, async (req: AuthRequest, res) => {
  try {
    const userId = req.user?.id;

    const { error } = await supabase
      .from('user_google_tokens')
      .delete()
      .eq('user_id', userId);

    if (error) {
      return res.status(400).json({ error: 'Failed to disconnect Google account' });
    }

    res.json({ message: 'Google account disconnected successfully' });
  } catch (error) {
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;