export interface User {
  id: string;
  email: string;
  name: string;
  avatar_url?: string;
  created_at: string;
  updated_at: string;
}

export interface GoogleTokens {
  user_id: string;
  access_token: string;
  refresh_token?: string;
  expires_at?: number;
  google_email: string;
  google_id: string;
}

export interface AuthResponse {
  message: string;
  user?: any;
  session?: any;
  needsGoogleAuth?: boolean;
}