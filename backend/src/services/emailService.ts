import dotenv from 'dotenv';
import { createClient } from '@supabase/supabase-js';
import { gmail_v1, gmail } from '@googleapis/gmail';
import { OAuth2Client } from 'google-auth-library';

// Load environment variables first
dotenv.config();

const supabase = createClient(
  process.env.SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
);

export interface EmailThread {
  id: string;
  gmailThreadId: string;
  subject: string;
  lastMessageAt: Date;
  messageCount: number;
  hasUnread: boolean;
  participants: string[];
  labels: string[];
  messages: EmailData[];
}

export interface EmailData {
  id: string;
  threadId: string;
  gmailMessageId: string;
  gmailThreadId: string;
  subject: string;
  senderEmail: string;
  senderName?: string;
  recipientEmails: string[];
  ccEmails?: string[];
  bccEmails?: string[];
  bodyHtml?: string;
  bodyText?: string;
  snippet?: string;
  receivedAt: Date;
  isRead: boolean;
  isStarred: boolean;
  labels: string[];
  hasAttachments: boolean;
  messageId?: string;
  inReplyTo?: string;
  references?: string;
  positionInThread: number;
  attachments?: EmailAttachment[];
}

export interface EmailAttachment {
  id: string;
  filename: string;
  mimeType?: string;
  sizeBytes?: number;
  gmailAttachmentId: string;
}

export class EmailService {
  private gmail: gmail_v1.Gmail;
  private auth: OAuth2Client;
  private userId: string;

  constructor(userId: string, tokens: { access_token: string; refresh_token: string; expires_at: number }) {
    this.userId = userId;
    
    this.auth = new OAuth2Client(
      process.env.GOOGLE_CLIENT_ID,
      process.env.GOOGLE_CLIENT_SECRET,
      process.env.GOOGLE_REDIRECT_URI
    );
    
    // Set both access and refresh tokens
    this.auth.setCredentials({
      access_token: tokens.access_token,
      refresh_token: tokens.refresh_token,
      expiry_date: tokens.expires_at,
    });

    // Fix for Gmail API initialization with type assertion
    this.gmail = gmail({ 
      version: 'v1', 
      auth: this.auth as any
    });
  }

  // Add a static factory method to create EmailService with tokens from DB
  static async create(userId: string): Promise<EmailService> {
    // Fetch tokens from database
    const { data: tokenData, error } = await supabase
      .from('user_google_tokens')
      .select('access_token, refresh_token, expires_at')
      .eq('user_id', userId)
      .single();

    if (error || !tokenData) {
      throw new Error('No Google tokens found for user. Please re-authorize Gmail access.');
    }

    return new EmailService(userId, {
      access_token: tokenData.access_token,
      refresh_token: tokenData.refresh_token,
      expires_at: tokenData.expires_at,
    });
  }

  async syncThreads(userId: string, maxResults: number = 50): Promise<EmailThread[]> {
    try {
      // Try to refresh the access token first
      await this.refreshAccessToken();

      // Get list of threads (not individual messages)
      const response = await this.gmail.users.threads.list({
        userId: 'me',
        maxResults,
        q: 'in:inbox',
      });

      const threads = response.data.threads || [];
      const threadsData: EmailThread[] = [];

      // Process each thread
      for (const thread of threads) {
        if (!thread.id) continue;

        const threadData = await this.fetchThreadDetails(thread.id, userId);
        if (threadData) {
          threadsData.push(threadData);
        }
      }

      // Store threads in database
      await this.storeThreads(userId, threadsData);

      return threadsData;
    } catch (error: any) {
      console.error('Error syncing threads:', error);
      
      // If it's an auth error, try refreshing token once more
      if (error?.status === 401 || error?.code === 401) {
        try {
          console.log('Attempting to refresh token due to auth error...');
          await this.refreshAccessToken();
          
          // Retry the request once
          const response = await this.gmail.users.threads.list({
            userId: 'me',
            maxResults,
            q: 'in:inbox',
          });

          const threads = response.data.threads || [];
          const threadsData: EmailThread[] = [];

          for (const thread of threads) {
            if (!thread.id) continue;
            const threadData = await this.fetchThreadDetails(thread.id, userId);
            if (threadData) {
              threadsData.push(threadData);
            }
          }

          await this.storeThreads(userId, threadsData);
          return threadsData;
        } catch (retryError: any) {
          console.error('Retry after token refresh failed:', retryError);
          throw new Error('Authentication failed. User needs to re-authorize Gmail access.');
        }
      }
      
      throw new Error('Failed to sync email threads from Gmail');
    }
  }

  private async refreshAccessToken(): Promise<void> {
    try {
      // Get fresh tokens
      const { credentials } = await this.auth.refreshAccessToken();
      
      // Update the auth client with new tokens
      this.auth.setCredentials(credentials);

      // Update the database with new access token if we got one
      if (credentials.access_token) {
        await supabase
          .from('user_google_tokens')
          .update({
            access_token: credentials.access_token,
            expires_at: credentials.expiry_date,
            updated_at: new Date().toISOString()
          })
          .eq('user_id', this.userId);
      }
    } catch (error: any) {
      console.error('Error refreshing access token:', error);
      throw new Error('Failed to refresh Google access token. User may need to re-authorize.');
    }
  }

  private async fetchThreadDetails(threadId: string, userId: string): Promise<EmailThread | null> {
    try {
      const response = await this.gmail.users.threads.get({
        userId: 'me',
        id: threadId,
        format: 'full',
      });

      const thread = response.data;
      if (!thread.messages || thread.messages.length === 0) return null;

      const messages: EmailData[] = [];
      const participants = new Set<string>();
      let hasUnread = false;
      let lastMessageAt = new Date(0);
      const allLabels = new Set<string>();

      // Process each message in the thread
      for (let i = 0; i < thread.messages.length; i++) {
        const message = thread.messages[i];
        if (!message.payload) continue;

        const emailData = await this.parseMessage(message, threadId, i, userId);
        if (emailData) {
          messages.push(emailData);
          
          // Update thread metadata
          participants.add(emailData.senderEmail);
          emailData.recipientEmails.forEach(email => participants.add(email));
          
          if (!emailData.isRead) hasUnread = true;
          if (emailData.receivedAt > lastMessageAt) lastMessageAt = emailData.receivedAt;
          
          emailData.labels.forEach(label => allLabels.add(label));
        }
      }

      if (messages.length === 0) return null;

      // Use the subject from the first message
      const subject = messages[0]?.subject || '(no subject)';

      const threadData: EmailThread = {
        id: '', // Will be generated by database
        gmailThreadId: threadId,
        subject,
        lastMessageAt,
        messageCount: messages.length,
        hasUnread,
        participants: Array.from(participants),
        labels: Array.from(allLabels),
        messages,
      };

      return threadData;
    } catch (error) {
      console.error(`Error fetching thread details for ${threadId}:`, error);
      return null;
    }
  }

  private async parseMessage(
    message: gmail_v1.Schema$Message, 
    gmailThreadId: string, 
    positionInThread: number,
    userId: string
  ): Promise<EmailData | null> {
    try {
      if (!message.payload) return null;

      const headers = message.payload.headers || [];
      
      // Extract all the email data (same as before)
      const subject = this.getHeader(headers, 'subject') || '(no subject)';
      const fromHeader = this.getHeader(headers, 'from') || '';
      const toHeader = this.getHeader(headers, 'to') || '';
      const ccHeader = this.getHeader(headers, 'cc');
      const bccHeader = this.getHeader(headers, 'bcc');
      const dateHeader = this.getHeader(headers, 'date');
      const messageId = this.getHeader(headers, 'message-id');
      const inReplyTo = this.getHeader(headers, 'in-reply-to');
      const references = this.getHeader(headers, 'references');

      // Parse sender
      const senderMatch = fromHeader.match(/^(.*?)\s*<(.+?)>$/) || [null, fromHeader, fromHeader];
      const senderName = senderMatch[1]?.trim().replace(/"/g, '') || undefined;
      const senderEmail = senderMatch[2]?.trim() || fromHeader;

      // Parse recipients
      const recipientEmails = this.parseEmailAddresses(toHeader);
      const ccEmails = ccHeader ? this.parseEmailAddresses(ccHeader) : [];
      const bccEmails = bccHeader ? this.parseEmailAddresses(bccHeader) : [];

      // Extract body content
      const { bodyHtml, bodyText } = this.extractBody(message.payload);

      // Check for attachments
      const attachments = this.extractAttachments(message.payload);

      const emailData: EmailData = {
        id: '', // Will be generated by database
        threadId: '', // Will be set when storing
        gmailMessageId: message.id || '',
        gmailThreadId,
        subject,
        senderEmail,
        senderName,
        recipientEmails,
        ccEmails,
        bccEmails,
        bodyHtml,
        bodyText,
        snippet: message.snippet || '',
        receivedAt: dateHeader ? new Date(dateHeader) : new Date(),
        isRead: !message.labelIds?.includes('UNREAD'),
        isStarred: message.labelIds?.includes('STARRED') || false,
        labels: message.labelIds || [],
        hasAttachments: attachments.length > 0,
        messageId,
        inReplyTo,
        references,
        positionInThread,
        attachments,
      };

      return emailData;
    } catch (error) {
      console.error(`Error parsing message:`, error);
      return null;
    }
  }

  private async storeThreads(userId: string, threads: EmailThread[]): Promise<void> {
    for (const thread of threads) {
      // Check if thread already exists
      const { data: existingThread } = await supabase
        .from('email_threads')
        .select('id')
        .eq('user_id', userId)
        .eq('gmail_thread_id', thread.gmailThreadId)
        .single();

      let threadDbId: string;

      if (existingThread) {
        // Update existing thread
        const { data: updatedThread, error } = await supabase
          .from('email_threads')
          .update({
            subject: thread.subject,
            last_message_at: thread.lastMessageAt.toISOString(),
            message_count: thread.messageCount,
            has_unread: thread.hasUnread,
            participants: thread.participants,
            labels: thread.labels,
            updated_at: new Date().toISOString(),
          })
          .eq('id', existingThread.id)
          .select()
          .single();

        if (error) {
          console.error('Error updating thread:', error);
          continue;
        }
        threadDbId = existingThread.id;
      } else {
        // Insert new thread
        const { data: insertedThread, error } = await supabase
          .from('email_threads')
          .insert({
            user_id: userId,
            gmail_thread_id: thread.gmailThreadId,
            subject: thread.subject,
            last_message_at: thread.lastMessageAt.toISOString(),
            message_count: thread.messageCount,
            has_unread: thread.hasUnread,
            participants: thread.participants,
            labels: thread.labels,
          })
          .select()
          .single();

        if (error) {
          console.error('Error inserting thread:', error);
          continue;
        }
        threadDbId = insertedThread.id;
      }

      // Store messages for this thread
      await this.storeMessages(userId, threadDbId, thread.messages);
    }
  }

  private async storeMessages(userId: string, threadDbId: string, messages: EmailData[]): Promise<void> {
    for (const message of messages) {
      // Check if message already exists
      const { data: existingMessage } = await supabase
        .from('emails')
        .select('id')
        .eq('user_id', userId)
        .eq('gmail_message_id', message.gmailMessageId)
        .single();

      if (existingMessage) continue; // Skip if already exists

      // Insert message
      const { data: insertedMessage, error: messageError } = await supabase
        .from('emails')
        .insert({
          user_id: userId,
          thread_id: threadDbId,
          gmail_message_id: message.gmailMessageId,
          gmail_thread_id: message.gmailThreadId,
          subject: message.subject,
          sender_email: message.senderEmail,
          sender_name: message.senderName,
          recipient_emails: message.recipientEmails,
          cc_emails: message.ccEmails,
          bcc_emails: message.bccEmails,
          body_html: message.bodyHtml,
          body_text: message.bodyText,
          snippet: message.snippet,
          received_at: message.receivedAt.toISOString(),
          is_read: message.isRead,
          is_starred: message.isStarred,
          labels: message.labels,
          has_attachments: message.hasAttachments,
          message_id: message.messageId,
          in_reply_to: message.inReplyTo,
          references: message.references,
          position_in_thread: message.positionInThread,
        })
        .select()
        .single();

      if (messageError) {
        console.error('Error inserting message:', messageError);
        continue;
      }

      // Insert attachments if any
      if (message.attachments && message.attachments.length > 0) {
        const attachmentsData = message.attachments.map(attachment => ({
          email_id: insertedMessage.id,
          filename: attachment.filename,
          mime_type: attachment.mimeType,
          size_bytes: attachment.sizeBytes,
          gmail_attachment_id: attachment.gmailAttachmentId,
        }));

        const { error: attachmentError } = await supabase
          .from('email_attachments')
          .insert(attachmentsData);

        if (attachmentError) {
          console.error('Error inserting attachments:', attachmentError);
        }
      }
    }
  }

  async getThreads(userId: string, page: number = 1, limit: number = 20): Promise<EmailThread[]> {
    const offset = (page - 1) * limit;

    const { data, error } = await supabase
      .from('email_threads')
      .select(`
        *,
        emails (
          *,
          email_attachments (*)
        )
      `)
      .eq('user_id', userId)
      .order('last_message_at', { ascending: false })
      .range(offset, offset + limit - 1);

    if (error) {
      throw new Error('Failed to fetch email threads from database');
    }

    return data.map(thread => ({
      id: thread.id,
      gmailThreadId: thread.gmail_thread_id,
      subject: thread.subject,
      lastMessageAt: new Date(thread.last_message_at),
      messageCount: thread.message_count,
      hasUnread: thread.has_unread,
      participants: thread.participants,
      labels: thread.labels,
      messages: thread.emails
        .sort((a: any, b: any) => a.position_in_thread - b.position_in_thread)
        .map((email: any) => ({
          id: email.id,
          threadId: email.thread_id,
          gmailMessageId: email.gmail_message_id,
          gmailThreadId: email.gmail_thread_id,
          subject: email.subject,
          senderEmail: email.sender_email,
          senderName: email.sender_name,
          recipientEmails: email.recipient_emails,
          ccEmails: email.cc_emails,
          bccEmails: email.bcc_emails,
          bodyHtml: email.body_html,
          bodyText: email.body_text,
          snippet: email.snippet,
          receivedAt: new Date(email.received_at),
          isRead: email.is_read,
          isStarred: email.is_starred,
          labels: email.labels,
          hasAttachments: email.has_attachments,
          messageId: email.message_id,
          inReplyTo: email.in_reply_to,
          references: email.references,
          positionInThread: email.position_in_thread,
          attachments: email.email_attachments,
        })),
    }));
  }

  private getHeader(headers: gmail_v1.Schema$MessagePartHeader[], name: string): string | undefined {
    const header = headers.find(h => h.name?.toLowerCase() === name.toLowerCase());
    return header?.value || undefined; // Fix null handling
  }

  private parseEmailAddresses(headerValue: string): string[] {
    return headerValue
      .split(',')
      .map(email => {
        const match = email.match(/<(.+?)>/) || [null, email];
        return match[1]?.trim() || email.trim();
      })
      .filter(email => email.length > 0);
  }

  private extractBody(payload: gmail_v1.Schema$MessagePart): { bodyHtml?: string; bodyText?: string } {
    let bodyHtml: string | undefined;
    let bodyText: string | undefined;

    if (payload.parts) {
      for (const part of payload.parts) {
        if (part.mimeType === 'text/html' && part.body?.data) {
          bodyHtml = this.decodeBase64(part.body.data);
        } else if (part.mimeType === 'text/plain' && part.body?.data) {
          bodyText = this.decodeBase64(part.body.data);
        }
      }
    } else if (payload.body?.data) {
      if (payload.mimeType === 'text/html') {
        bodyHtml = this.decodeBase64(payload.body.data);
      } else if (payload.mimeType === 'text/plain') {
        bodyText = this.decodeBase64(payload.body.data);
      }
    }

    return { bodyHtml, bodyText };
  }

  private extractAttachments(payload: gmail_v1.Schema$MessagePart): EmailAttachment[] {
    const attachments: EmailAttachment[] = [];

    const findAttachments = (parts: gmail_v1.Schema$MessagePart[]) => {
      for (const part of parts) {
        if (part.filename && part.filename.length > 0 && part.body?.attachmentId) {
          attachments.push({
            id: '', // Will be generated by database
            filename: part.filename,
            mimeType: part.mimeType || undefined, // Fix null handling
            sizeBytes: part.body.size || undefined, // Fix null handling
            gmailAttachmentId: part.body.attachmentId,
          });
        }
        
        if (part.parts) {
          findAttachments(part.parts);
        }
      }
    };

    if (payload.parts) {
      findAttachments(payload.parts);
    }

    return attachments;
  }

  private decodeBase64(data: string): string {
    return Buffer.from(data, 'base64').toString('utf-8');
  }
}