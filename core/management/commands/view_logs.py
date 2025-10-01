"""
Django management command to view application logs
"""
from django.core.management.base import BaseCommand
import os
from pathlib import Path


class Command(BaseCommand):
    help = 'View application logs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--log-type',
            type=str,
            default='errors',
            choices=['general', 'errors', 'connections', 'evolution_api'],
            help='Type of log to view (default: errors)'
        )
        parser.add_argument(
            '--lines',
            type=int,
            default=50,
            help='Number of lines to show (default: 50)'
        )
        parser.add_argument(
            '--follow',
            action='store_true',
            help='Follow log file in real-time'
        )

    def handle(self, *args, **options):
        log_type = options['log_type']
        lines = options['lines']
        follow = options['follow']
        
        # Get the logs directory
        base_dir = Path(__file__).resolve().parent.parent.parent.parent
        logs_dir = base_dir / 'logs'
        log_file = logs_dir / f'{log_type}.log'
        
        if not log_file.exists():
            self.stdout.write(
                self.style.ERROR(f'Log file {log_file} does not exist')
            )
            return
        
        # Build tail command
        if follow:
            cmd = f'tail -f -n {lines} "{log_file}"'
        else:
            cmd = f'tail -n {lines} "{log_file}"'
        
        self.stdout.write(
            self.style.SUCCESS(f'Showing last {lines} lines from {log_type}.log:')
        )
        self.stdout.write('=' * 80)
        
        # Execute the command
        os.system(cmd)
