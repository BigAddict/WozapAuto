"""
Django management command to cleanup duplicate webhook data.
This helps prevent double responses by removing duplicate message_ids.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from aiengine.models import WebhookData
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Cleanup duplicate webhook data to prevent double responses'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )
        parser.add_argument(
            '--keep-latest',
            action='store_true',
            help='Keep the latest duplicate instead of the oldest'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        keep_latest = options['keep_latest']
        
        self.stdout.write("Starting duplicate webhook cleanup...")
        
        # Find duplicates by message_id
        duplicates = defaultdict(list)
        
        for webhook in WebhookData.objects.all():
            duplicates[webhook.message_id].append(webhook)
        
        # Filter to only message_ids with duplicates
        actual_duplicates = {msg_id: webhooks for msg_id, webhooks in duplicates.items() if len(webhooks) > 1}
        
        if not actual_duplicates:
            self.stdout.write("No duplicate webhook data found.")
            return
        
        self.stdout.write(f"Found {len(actual_duplicates)} message_ids with duplicates:")
        
        total_to_delete = 0
        
        for message_id, webhooks in actual_duplicates.items():
            self.stdout.write(f"\nMessage ID: {message_id}")
            self.stdout.write(f"  Found {len(webhooks)} duplicates:")
            
            # Sort by date_time
            webhooks.sort(key=lambda x: x.date_time, reverse=keep_latest)
            
            # Keep the first one (latest if keep_latest=True, oldest if False)
            to_keep = webhooks[0]
            to_delete = webhooks[1:]
            
            self.stdout.write(f"  Keeping: {to_keep.id} (processed: {to_keep.is_processed}, date: {to_keep.date_time})")
            
            for webhook in to_delete:
                self.stdout.write(f"  Will delete: {webhook.id} (processed: {webhook.is_processed}, date: {webhook.date_time})")
                total_to_delete += 1
        
        if dry_run:
            self.stdout.write(f"\nDry run complete. Would delete {total_to_delete} duplicate webhook records.")
            return
        
        # Actually delete the duplicates
        deleted_count = 0
        for message_id, webhooks in actual_duplicates.items():
            webhooks.sort(key=lambda x: x.date_time, reverse=keep_latest)
            to_delete = webhooks[1:]
            
            try:
                with transaction.atomic():
                    for webhook in to_delete:
                        webhook.delete()
                        deleted_count += 1
                        self.stdout.write(f"Deleted webhook {webhook.id} for message_id {message_id}")
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error deleting duplicates for message_id {message_id}: {e}")
                )
        
        self.stdout.write(
            self.style.SUCCESS(f"Cleanup complete. Deleted {deleted_count} duplicate webhook records.")
        )
