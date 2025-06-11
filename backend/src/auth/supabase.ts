import { createClient } from '@supabase/supabase-js';
import dotenv from 'dotenv';

// Load environment variables
dotenv.config();

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_ANON_KEY;
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

if (!supabaseUrl) {
  throw new Error('SUPABASE_URL is required in environment variables');
}

if (!supabaseKey) {
  throw new Error('SUPABASE_ANON_KEY is required in environment variables');
}

if (!supabaseServiceKey) {
  throw new Error('SUPABASE_SERVICE_ROLE_KEY is required in environment variables');
}

export const supabase = createClient(supabaseUrl, supabaseKey);

export const supabaseAdmin = createClient(supabaseUrl, supabaseServiceKey);