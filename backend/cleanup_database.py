#!/usr/bin/env python3
"""
Database Cleanup Script for Velocitas Email Application

This script provides various cleanup options for the database including:
- Clean all data (emails, attachments, users, sessions)
- Clean specific user data
- Clean expired sessions
- Clean orphaned attachments
- Reset database to fresh state
"""

import sys
import argparse
from datetime import datetime, timedelta
from models import Email, Attachment, User, Session as UserSession, DatabaseSession

def get_database_stats():
    """Get current database statistics"""
    session = DatabaseSession()
    try:
        user_count = session.query(User).count()
        email_count = session.query(Email).count()
        attachment_count = session.query(Attachment).count()
        session_count = session.query(UserSession).count()
        
        return {
            'users': user_count,
            'emails': email_count,
            'attachments': attachment_count,
            'sessions': session_count
        }
    finally:
        session.close()

def print_stats(stats, title="Database Statistics"):
    """Print database statistics in a nice format"""
    print(f"\n📊 {title}")
    print("=" * 40)
    print(f"Users:       {stats['users']:,}")
    print(f"Emails:      {stats['emails']:,}")
    print(f"Attachments: {stats['attachments']:,}")
    print(f"Sessions:    {stats['sessions']:,}")
    print("=" * 40)

def cleanup_expired_sessions(days_old=30):
    """Clean up expired sessions older than specified days"""
    session = DatabaseSession()
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        # Count expired sessions
        expired_count = session.query(UserSession).filter(
            UserSession.expires_at < datetime.utcnow()
        ).count()
        
        old_inactive_count = session.query(UserSession).filter(
            UserSession.created_at < cutoff_date,
            UserSession.is_active == False
        ).count()
        
        print(f"🧹 Found {expired_count} expired sessions")
        print(f"🧹 Found {old_inactive_count} old inactive sessions")
        
        if expired_count > 0 or old_inactive_count > 0:
            # Delete expired sessions
            deleted_expired = session.query(UserSession).filter(
                UserSession.expires_at < datetime.utcnow()
            ).delete()
            
            # Delete old inactive sessions
            deleted_old = session.query(UserSession).filter(
                UserSession.created_at < cutoff_date,
                UserSession.is_active == False
            ).delete()
            
            session.commit()
            total_deleted = deleted_expired + deleted_old
            print(f"✅ Deleted {total_deleted} expired/old sessions")
        else:
            print("✅ No expired sessions to clean up")
        
        return expired_count + old_inactive_count
            
    except Exception as e:
        session.rollback()
        print(f"❌ Error cleaning expired sessions: {e}")
        return 0
    finally:
        session.close()

def cleanup_orphaned_attachments():
    """Clean up attachments that don't have corresponding emails"""
    session = DatabaseSession()
    try:
        # Find orphaned attachments
        orphaned_attachments = session.query(Attachment).filter(
            ~Attachment.email_id.in_(
                session.query(Email.id).subquery()
            )
        )
        
        orphaned_count = orphaned_attachments.count()
        print(f"🧹 Found {orphaned_count} orphaned attachments")
        
        if orphaned_count > 0:
            orphaned_attachments.delete(synchronize_session=False)
            session.commit()
            print(f"✅ Deleted {orphaned_count} orphaned attachments")
        else:
            print("✅ No orphaned attachments found")
            
        return orphaned_count
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error cleaning orphaned attachments: {e}")
        return 0
    finally:
        session.close()

def cleanup_user_data(user_email):
    """Clean up all data for a specific user"""
    session = DatabaseSession()
    try:
        # Find user
        user = session.query(User).filter(User.email == user_email).first()
        if not user:
            print(f"❌ User {user_email} not found")
            return False
        
        user_id = user.id
        
        # Count user data
        email_count = session.query(Email).filter(Email.user_id == user_id).count()
        attachment_count = session.query(Attachment).filter(Attachment.user_id == user_id).count()
        session_count = session.query(UserSession).filter(UserSession.user_id == user_id).count()
        
        print(f"🧹 User {user_email} has:")
        print(f"   - {email_count} emails")
        print(f"   - {attachment_count} attachments")
        print(f"   - {session_count} sessions")
        
        # Delete user data (cascading should handle related data)
        session.query(Attachment).filter(Attachment.user_id == user_id).delete()
        session.query(Email).filter(Email.user_id == user_id).delete()
        session.query(UserSession).filter(UserSession.user_id == user_id).delete()
        session.delete(user)
        
        session.commit()
        print(f"✅ Deleted user {user_email} and all associated data")
        return True
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error deleting user data: {e}")
        return False
    finally:
        session.close()

def cleanup_all_data(confirm=True):
    """Delete all data from database"""
    if confirm:
        response = input("⚠️  This will delete ALL data including users! Type 'DELETE ALL' to confirm: ")
        if response != "DELETE ALL":
            print("❌ Cleanup cancelled")
            return False
    
    session = DatabaseSession()
    try:
        # Get counts before deletion
        stats = get_database_stats()
        print_stats(stats, "Data to be deleted")
        
        # Delete in order (foreign key constraints)
        print("\n🧹 Starting cleanup...")
        
        # Delete attachments first
        deleted_attachments = session.query(Attachment).delete()
        print(f"✅ Deleted {deleted_attachments} attachments")
        
        # Delete emails
        deleted_emails = session.query(Email).delete()
        print(f"✅ Deleted {deleted_emails} emails")
        
        # Delete sessions
        deleted_sessions = session.query(UserSession).delete()
        print(f"✅ Deleted {deleted_sessions} sessions")
        
        # Delete users
        deleted_users = session.query(User).delete()
        print(f"✅ Deleted {deleted_users} users")
        
        session.commit()
        print("\n🎉 Database completely cleaned!")
        
        # Show final stats
        final_stats = get_database_stats()
        print_stats(final_stats, "Final Database State")
        
        return True
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error during cleanup: {e}")
        return False
    finally:
        session.close()

def cleanup_old_emails(days_old=365):
    """Clean up emails older than specified days"""
    session = DatabaseSession()
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        # Find old emails
        old_emails = session.query(Email).filter(Email.internal_date < cutoff_date)
        old_count = old_emails.count()
        
        print(f"🧹 Found {old_count} emails older than {days_old} days")
        
        if old_count > 0:
            # Get email IDs for attachment cleanup
            old_email_ids = [email.id for email in old_emails]
            
            # Delete associated attachments first
            deleted_attachments = session.query(Attachment).filter(
                Attachment.email_id.in_(old_email_ids)
            ).delete(synchronize_session=False)
            
            # Delete old emails
            deleted_emails = old_emails.delete(synchronize_session=False)
            
            session.commit()
            print(f"✅ Deleted {deleted_emails} old emails and {deleted_attachments} attachments")
        else:
            print("✅ No old emails to clean up")
            
        return old_count
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error cleaning old emails: {e}")
        return 0
    finally:
        session.close()

def list_users():
    """List all users in the database"""
    session = DatabaseSession()
    try:
        users = session.query(User).all()
        
        if not users:
            print("📭 No users found in database")
            return
        
        print(f"\n👥 Found {len(users)} users:")
        print("=" * 80)
        for user in users:
            email_count = session.query(Email).filter(Email.user_id == user.id).count()
            session_count = session.query(UserSession).filter(UserSession.user_id == user.id).count()
            
            status = "🟢 Active" if user.is_active else "🔴 Inactive"
            last_login = user.last_login.strftime("%Y-%m-%d %H:%M") if user.last_login else "Never"
            
            print(f"Email: {user.email}")
            print(f"Name:  {user.name}")
            print(f"Status: {status}")
            print(f"Created: {user.created_at.strftime('%Y-%m-%d %H:%M')}")
            print(f"Last Login: {last_login}")
            print(f"Emails: {email_count}, Sessions: {session_count}")
            print("-" * 80)
            
    finally:
        session.close()

def main():
    parser = argparse.ArgumentParser(description="Velocitas Database Cleanup Tool")
    parser.add_argument('--stats', action='store_true', help='Show database statistics')
    parser.add_argument('--list-users', action='store_true', help='List all users')
    parser.add_argument('--cleanup-sessions', type=int, metavar='DAYS', 
                       help='Clean up expired sessions older than DAYS (default: 30)')
    parser.add_argument('--cleanup-orphaned', action='store_true', 
                       help='Clean up orphaned attachments')
    parser.add_argument('--cleanup-old-emails', type=int, metavar='DAYS',
                       help='Clean up emails older than DAYS')
    parser.add_argument('--cleanup-user', metavar='EMAIL', 
                       help='Delete specific user and all their data')
    parser.add_argument('--cleanup-all', action='store_true', 
                       help='Delete ALL data (requires confirmation)')
    parser.add_argument('--force', action='store_true', 
                       help='Skip confirmation prompts (use with caution!)')
    
    args = parser.parse_args()
    
    # Show stats by default or when requested
    if not any(vars(args).values()) or args.stats:
        stats = get_database_stats()
        print_stats(stats)
        if not any(vars(args).values()):
            print("\nUse --help to see cleanup options")
        return
    
    print("🧹 Velocitas Database Cleanup Tool")
    print("=" * 40)
    
    if args.list_users:
        list_users()
    
    if args.cleanup_sessions is not None:
        days = args.cleanup_sessions if args.cleanup_sessions > 0 else 30
        cleanup_expired_sessions(days)
    
    if args.cleanup_orphaned:
        cleanup_orphaned_attachments()
    
    if args.cleanup_old_emails is not None:
        if args.cleanup_old_emails <= 0:
            print("❌ Days must be positive")
            return
        cleanup_old_emails(args.cleanup_old_emails)
    
    if args.cleanup_user:
        cleanup_user_data(args.cleanup_user)
    
    if args.cleanup_all:
        cleanup_all_data(confirm=not args.force)
    
    # Show final stats if any cleanup was performed
    if any([args.cleanup_sessions is not None, args.cleanup_orphaned, 
            args.cleanup_old_emails is not None, args.cleanup_user, args.cleanup_all]):
        print("\n📊 Final Statistics:")
        final_stats = get_database_stats()
        print_stats(final_stats)

if __name__ == '__main__':
    main()