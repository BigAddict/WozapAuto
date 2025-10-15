from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import models, transaction
from aiengine.models import Agent


class Command(BaseCommand):
    help = 'Clean up duplicate agents per user, keeping the most recent active one'

    def handle(self, *args, **options):
        self.stdout.write('Starting cleanup of duplicate agents...')
        
        # Get all users who have multiple agents
        users_with_multiple_agents = User.objects.filter(
            owned_agents__isnull=False
        ).annotate(
            agent_count=models.Count('owned_agents')
        ).filter(agent_count__gt=1)
        
        cleaned_count = 0
        
        for user in users_with_multiple_agents:
            with transaction.atomic():
                # Get all agents for this user, ordered by active status and creation date
                agents = Agent.objects.filter(user=user).order_by('-is_active', '-created_at')
                
                if agents.count() > 1:
                    # Keep the first one (most recent active, or most recent if none active)
                    keep_agent = agents.first()
                    
                    # Delete the rest
                    agents_to_delete = agents[1:]
                    delete_count = agents_to_delete.count()
                    
                    for agent in agents_to_delete:
                        agent.delete()
                    
                    cleaned_count += delete_count
                    self.stdout.write(
                        f'Cleaned up {delete_count} duplicate agents for user {user.username}, '
                        f'kept agent "{keep_agent.name}" (ID: {keep_agent.id})'
                    )
        
        self.stdout.write(
            self.style.SUCCESS(f'Cleanup complete! Removed {cleaned_count} duplicate agents.')
        )
