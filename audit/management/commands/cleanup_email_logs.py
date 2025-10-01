"""
Management command to clean up old email logs for maintenance.
Exports logs to Excel before deletion for audit purposes.
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import models
from datetime import timedelta
from audit.models import EmailLog
import pandas as pd
import os
from django.conf import settings


class Command(BaseCommand):
    help = 'Clean up old email logs to maintain database performance'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Number of days to keep email logs (default: 90)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )
        parser.add_argument(
            '--status',
            choices=['sent', 'failed', 'pending'],
            help='Only delete logs with specific status',
        )
        parser.add_argument(
            '--email-type',
            choices=['welcome', 'password_reset', 'password_change', 'connection_success', 'system', 'other'],
            help='Only delete logs of specific email type',
        )
        parser.add_argument(
            '--export-dir',
            type=str,
            default='exports',
            help='Directory to save Excel export (default: exports)',
        )
        parser.add_argument(
            '--skip-export',
            action='store_true',
            help='Skip Excel export and directly delete logs',
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        status = options.get('status')
        email_type = options.get('email_type')
        export_dir = options['export_dir']
        skip_export = options['skip_export']

        # Calculate cutoff date
        cutoff_date = timezone.now() - timedelta(days=days)

        # Build query
        query = EmailLog.objects.filter(created_at__lt=cutoff_date)

        if status:
            query = query.filter(status=status)

        if email_type:
            query = query.filter(email_type=email_type)

        # Get count of records to be deleted
        count = query.count()

        if count == 0:
            self.stdout.write(
                self.style.SUCCESS('No email logs found to delete.')
            )
            return

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'DRY RUN: Would delete {count} email log(s) older than {days} days'
                )
            )
            
            # Show breakdown by status
            status_breakdown = query.values('status').annotate(
                count=models.Count('id')
            ).order_by('status')
            
            for item in status_breakdown:
                self.stdout.write(f'  - {item["status"]}: {item["count"]} logs')
            
            # Show breakdown by email type
            type_breakdown = query.values('email_type').annotate(
                count=models.Count('id')
            ).order_by('email_type')
            
            self.stdout.write('\nBreakdown by email type:')
            for item in type_breakdown:
                self.stdout.write(f'  - {item["email_type"]}: {item["count"]} logs')
            
            return

        # Export to Excel before deletion (unless skipped)
        if not skip_export:
            try:
                export_file = self.export_to_excel(query, export_dir)
                self.stdout.write(
                    self.style.SUCCESS(f'Email logs exported to: {export_file}')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Failed to export to Excel: {str(e)}')
                )
                if not self.confirm_continue_without_export():
                    self.stdout.write(
                        self.style.WARNING('Operation cancelled.')
                    )
                    return

        # Confirm deletion
        if not self.confirm_deletion(count, days):
            self.stdout.write(
                self.style.WARNING('Deletion cancelled.')
            )
            return

        # Perform deletion
        try:
            deleted_count, _ = query.delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully deleted {deleted_count} email log(s) older than {days} days.'
                )
            )
        except Exception as e:
            raise CommandError(f'Error deleting email logs: {str(e)}')

    def export_to_excel(self, query, export_dir):
        """Export email logs to Excel file"""
        # Create export directory if it doesn't exist
        export_path = os.path.join(settings.BASE_DIR, export_dir)
        os.makedirs(export_path, exist_ok=True)
        
        # Get date range for filename
        logs = query.order_by('created_at')
        if logs.exists():
            start_date = logs.first().created_at.strftime('%Y-%m-%d')
            end_date = logs.last().created_at.strftime('%Y-%m-%d')
        else:
            start_date = end_date = timezone.now().strftime('%Y-%m-%d')
        
        # Create filename with date range
        filename = f"{start_date}_to_{end_date}_email_logs.xlsx"
        filepath = os.path.join(export_path, filename)
        
        # Prepare data for export
        data = []
        for log in logs:
            data.append({
                'ID': log.id,
                'Email Type': log.get_email_type_display(),
                'Recipient Email': log.recipient_email,
                'Recipient User': log.recipient_user.username if log.recipient_user else 'N/A',
                'Subject': log.subject,
                'Status': log.get_status_display(),
                'Template Used': log.template_used,
                'Created At': log.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'Sent At': log.sent_at.strftime('%Y-%m-%d %H:%M:%S') if log.sent_at else 'N/A',
                'Failed At': log.failed_at.strftime('%Y-%m-%d %H:%M:%S') if log.failed_at else 'N/A',
                'Error Message': log.error_message if log.error_message else 'N/A',
                'IP Address': log.ip_address if log.ip_address else 'N/A',
                'User Agent': log.user_agent if log.user_agent else 'N/A',
                'Context Data': str(log.context_data) if log.context_data else 'N/A',
                'Updated At': log.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
            })
        
        # Create DataFrame and export to Excel
        df = pd.DataFrame(data)
        
        # Create Excel writer with formatting
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Email Logs', index=False)
            
            # Get the workbook and worksheet
            workbook = writer.book
            worksheet = writer.sheets['Email Logs']
            
            # Auto-adjust column widths
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)  # Cap at 50 characters
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        return filepath

    def confirm_continue_without_export(self):
        """Ask for confirmation to continue without export"""
        self.stdout.write(
            self.style.WARNING(
                'Excel export failed. Do you want to continue with deletion without export?'
            )
        )
        
        while True:
            response = input('Continue without export? (yes/no): ').lower()
            if response in ['yes', 'y']:
                return True
            elif response in ['no', 'n']:
                return False
            else:
                self.stdout.write('Please answer "yes" or "no".')

    def confirm_deletion(self, count, days):
        """Ask for confirmation before deletion"""
        self.stdout.write(
            self.style.WARNING(
                f'This will delete {count} email log(s) older than {days} days.'
            )
        )
        
        while True:
            response = input('Are you sure you want to continue? (yes/no): ').lower()
            if response in ['yes', 'y']:
                return True
            elif response in ['no', 'n']:
                return False
            else:
                self.stdout.write('Please answer "yes" or "no".')
