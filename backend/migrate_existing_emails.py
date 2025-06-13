"""
Script to migrate existing emails and populate the new fields based on their Gmail labels
Run this after adding the new columns to update existing data
"""

from models import Email, DatabaseSession
from gmailDownload import parse_gmail_labels

def migrate_existing_emails():
    """Update all existing emails to populate the new fields from their Gmail labels"""
    print("🔄 Starting migration of existing emails...")
    
    session = DatabaseSession()
    try:
        # Get all emails that need migration
        emails = session.query(Email).all()
        print(f"📧 Found {len(emails)} emails to migrate")
        
        updated_count = 0
        for email in emails:
            try:
                # Parse the existing label_ids
                if email.label_ids:
                    labels = email.label_ids.split(',')
                    label_info = parse_gmail_labels(labels)
                    
                    # Update the new fields
                    email.is_starred = label_info['is_starred']
                    email.is_read = label_info['is_read']
                    email.category = label_info['category']
                    email.urgency = label_info['urgency']
                    
                    updated_count += 1
                    
                    if updated_count % 100 == 0:
                        print(f"📧 Migrated {updated_count} emails...")
                        session.commit()  # Commit in batches
                
            except Exception as e:
                print(f"❌ Error migrating email {email.id}: {e}")
                continue
        
        # Final commit
        session.commit()
        print(f"✅ Successfully migrated {updated_count} emails!")
        
        # Show some statistics
        stats = session.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN is_starred THEN 1 END) as starred,
                COUNT(CASE WHEN is_read THEN 1 END) as read,
                COUNT(CASE WHEN NOT is_read THEN 1 END) as unread
            FROM emails
        """).fetchone()
        
        print(f"📊 Migration Statistics:")
        print(f"   Total emails: {stats[0]}")
        print(f"   Starred: {stats[1]}")
        print(f"   Read: {stats[2]}")
        print(f"   Unread: {stats[3]}")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    migrate_existing_emails()