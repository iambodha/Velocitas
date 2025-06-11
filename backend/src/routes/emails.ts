import express, { Router } from 'express';
import { EmailService } from '../services/emailService';
import { authMiddleware, AuthRequest } from '../middleware/auth';
import { createClient } from '@supabase/supabase-js';

const router = express.Router();

const supabase = createClient(
  process.env.SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
);

// Sync emails from Gmail
router.post('/sync', authMiddleware, async (req: AuthRequest, res) => {
  try {
    const userId = req.user?.id;
    
    if (!userId) {
      return res.status(401).json({ error: 'User not authenticated' });
    }

    const { maxResults = 50 } = req.body;

    // Get user's Gmail refresh token from user_google_tokens table
    const { data: tokenData, error } = await supabase
      .from('user_google_tokens')
      .select('refresh_token, access_token, expires_at')
      .eq('user_id', userId)
      .single();

    if (error || !tokenData?.refresh_token) {
      return res.status(400).json({ 
        error: 'Gmail not connected. Please connect your Gmail account first.' 
      });
    }

    // Check if access token is expired
    const now = Date.now();
    const isExpired = tokenData.expires_at && now >= tokenData.expires_at;
    
    if (isExpired) {
      console.log('Access token expired, EmailService will refresh it automatically');
    }

    const emailService = await EmailService.create(userId);
    const emails = await emailService.syncThreads(userId, maxResults);

    res.json({ 
      message: 'Emails synced successfully', 
      count: emails.length,
      emails 
    });
  } catch (error: any) {
    console.error('Error syncing emails:', error);
    
    if (error?.message?.includes('re-authorize')) {
      res.status(401).json({ 
        error: 'Gmail authorization expired. Please reconnect your Gmail account.',
        needsReauth: true 
      });
    } else {
      res.status(500).json({ error: 'Failed to sync emails' });
    }
  }
});

// Get emails with pagination
router.get('/', authMiddleware, async (req: AuthRequest, res) => {
  try {
    const userId = req.user?.id;
    
    if (!userId) {
      return res.status(401).json({ error: 'User not authenticated' });
    }

    const page = parseInt(req.query.page as string) || 1;
    const limit = parseInt(req.query.limit as string) || 20;

    // Get user's Gmail refresh token from user_google_tokens table
    const { data: tokenData, error } = await supabase
      .from('user_google_tokens')
      .select('refresh_token, access_token, expires_at')
      .eq('user_id', userId)
      .single();

    if (error || !tokenData?.refresh_token) {
      return res.status(400).json({ 
        error: 'Gmail not connected. Please connect your Gmail account first.' 
      });
    }

    const emailService = await EmailService.create(userId);
    const emails = await emailService.getThreads(userId, page, limit);

    res.json({ emails, page, limit });
  } catch (error: any) {
    console.error('Error fetching emails:', error);
    res.status(500).json({ error: 'Failed to fetch emails' });
  }
});

// Get single email by ID
router.get('/:id', authMiddleware, async (req: AuthRequest, res) => {
  try {
    const userId = req.user?.id;
    
    if (!userId) {
      return res.status(401).json({ error: 'User not authenticated' });
    }

    const emailId = req.params.id;

    const { data: email, error } = await supabase
      .from('emails')
      .select(`
        *,
        email_attachments (*)
      `)
      .eq('id', emailId)
      .eq('user_id', userId)
      .single();

    if (error || !email) {
      return res.status(404).json({ error: 'Email not found' });
    }

    res.json({ email });
  } catch (error: any) {
    console.error('Error fetching email:', error);
    res.status(500).json({ error: 'Failed to fetch email' });
  }
});

export default router;