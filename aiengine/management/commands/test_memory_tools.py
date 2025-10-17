"""
Django management command to test memory tools functionality.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from aiengine.models import Agent, ConversationThread, ConversationMessage
from aiengine.memory_service import MemoryService
from aiengine.memory_tools import MemorySearchTool
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Test memory tools functionality'

    def handle(self, *args, **options):
        self.stdout.write('Testing memory tools...')
        
        try:
            # Get or create a test user
            user, created = User.objects.get_or_create(
                username='testuser',
                defaults={'email': 'test@example.com'}
            )
            
            # Get or create a test agent
            agent, created = Agent.objects.get_or_create(
                user=user,
                defaults={
                    'name': 'Test Agent',
                    'system_prompt': 'You are a test assistant',
                    'is_active': True
                }
            )
            
            # Get or create a test thread
            thread, created = ConversationThread.objects.get_or_create(
                thread_id="test_memory_tools",
                defaults={
                    'user': user,
                    'agent': agent,
                    'remote_jid': 'test@whatsapp.com'
                }
            )
            
            # Create some test messages
            test_messages = [
                ("human", "I'm working on a Python project"),
                ("ai", "That sounds interesting! What kind of Python project?"),
                ("human", "It's a web scraping tool for e-commerce sites"),
                ("ai", "Web scraping can be tricky. Are you using any specific libraries?"),
                ("human", "Yes, I'm using BeautifulSoup and requests"),
                ("ai", "Great choices! Those are excellent libraries for web scraping."),
                ("human", "I'm having trouble with dynamic content loading"),
                ("ai", "For dynamic content, you might need Selenium or Playwright"),
            ]
            
            # Add messages to the thread
            memory_service = MemoryService(thread)
            for msg_type, content in test_messages:
                memory_service.add_message(msg_type, content)
            
            self.stdout.write(f'✓ Added {len(test_messages)} test messages')
            
            # Test memory tools
            memory_tools = MemorySearchTool(memory_service)
            
            # Test search_memory
            self.stdout.write('\nTesting search_memory tool...')
            search_result = memory_tools.search_memory("Python project", limit=3)
            self.stdout.write(f'Search result: {search_result[:200]}...')
            
            # Test get_conversation_summary
            self.stdout.write('\nTesting get_conversation_summary tool...')
            summary_result = memory_tools.get_conversation_summary()
            self.stdout.write(f'Summary result: {summary_result}')
            
            # Test tool creation
            self.stdout.write('\nTesting tool creation...')
            tools = memory_tools.get_tools()
            self.stdout.write(f'✓ Created {len(tools)} tools')
            
            for tool in tools:
                self.stdout.write(f'  - Tool: {tool.name}')
            
            self.stdout.write(
                self.style.SUCCESS('\n✓ Memory tools test completed successfully!')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Memory tools test failed: {e}')
            )
            logger.error(f"Memory tools test error: {e}")
