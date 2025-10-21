"""
Django management command to cleanup old conversation messages.
This helps prevent timeout issues with long conversations.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from aiengine.models import ConversationMessage, ConversationThread
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Cleanup old conversation messages to prevent timeout issues'

    def add_arguments(self, parser):
        parser.add_argument(
            '--keep-recent',
            type=int,
            default=50,
            help='Number of recent messages to keep per thread (default: 50)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )
        parser.add_argument(
            '--thread-id',
            type=str,
            help='Cleanup specific thread ID only'
        )

    def handle(self, *args, **options):
        keep_recent = options['keep_recent']
        dry_run = options['dry_run']
        thread_id = options.get('thread_id')
        
        self.stdout.write(f"Starting conversation cleanup (keep_recent={keep_recent}, dry_run={dry_run})")
        
        # Get threads to process
        if thread_id:
            threads = ConversationThread.objects.filter(thread_id=thread_id)
        else:
            threads = ConversationThread.objects.all()
        
        total_deleted = 0
        
        for thread in threads:
            # Get all messages for this thread, ordered by creation time
            messages = ConversationMessage.objects.filter(thread=thread).order_by('created_at')
            total_messages = messages.count()
            
            if total_messages <= keep_recent:
                self.stdout.write(f"Thread {thread.thread_id}: {total_messages} messages (no cleanup needed)")
                continue
            
            # Calculate how many to delete
            to_delete_count = total_messages - keep_recent
            messages_to_delete = messages[:to_delete_count]
            
            self.stdout.write(
                f"Thread {thread.thread_id}: {total_messages} messages, "
                f"will delete {to_delete_count} oldest messages"
            )
            
            if not dry_run:
                try:
                    with transaction.atomic():
                        # Delete the oldest messages one by one to avoid limit/offset issues
                        deleted_count = 0
                        for message in messages_to_delete:
                            message.delete()
                            deleted_count += 1
                        total_deleted += deleted_count
                        self.stdout.write(f"  Deleted {deleted_count} messages")
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"  Error deleting messages for thread {thread.thread_id}: {e}")
                    )
            else:
                total_deleted += to_delete_count
                self.stdout.write(f"  Would delete {to_delete_count} messages (dry run)")
        
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f"Dry run complete. Would delete {total_deleted} messages total.")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Cleanup complete. Deleted {total_deleted} messages total.")
            )
