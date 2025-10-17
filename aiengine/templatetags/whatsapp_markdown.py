"""
WhatsApp markdown template filters for Django.
"""
import re
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def whatsapp_markdown(value):
    """
    Convert WhatsApp markdown to HTML.
    
    Supported formats:
    - *bold* -> <strong>bold</strong>
    - _italic_ -> <em>italic</em>
    - ~strikethrough~ -> <del>strikethrough</del>
    - `inline code` -> <code>inline code</code>
    - ```monospace``` -> <pre><code>monospace</code></pre>
    - > quote -> <blockquote>quote</blockquote>
    - * bullet list -> <ul><li>bullet list</li></ul>
    - - bullet list -> <ul><li>bullet list</li></ul>
    - 1. numbered list -> <ol><li>numbered list</li></ol>
    """
    if not value:
        return value
    
    text = str(value)
    
    # Handle monospace blocks (```text```) - must be done first
    text = re.sub(r'```([^`]+)```', r'<pre><code>\1</code></pre>', text, flags=re.DOTALL)
    
    # Handle inline code (`text`)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    
    # Handle quotes (> text)
    text = re.sub(r'^> (.+)$', r'<blockquote>\1</blockquote>', text, flags=re.MULTILINE)
    
    # Handle bullet lists (* text or - text)
    # First, find all lines that start with * or - followed by space
    lines = text.split('\n')
    processed_lines = []
    in_bullet_list = False
    bullet_items = []
    
    for line in lines:
        # Check if line starts with bullet
        bullet_match = re.match(r'^(\*|\-)\s+(.+)$', line.strip())
        if bullet_match:
            if not in_bullet_list:
                in_bullet_list = True
            bullet_items.append(bullet_match.group(2))
        else:
            # End of bullet list
            if in_bullet_list:
                if bullet_items:
                    bullet_html = '<ul>' + ''.join(f'<li>{item}</li>' for item in bullet_items) + '</ul>'
                    processed_lines.append(bullet_html)
                bullet_items = []
                in_bullet_list = False
            processed_lines.append(line)
    
    # Handle any remaining bullet list
    if in_bullet_list and bullet_items:
        bullet_html = '<ul>' + ''.join(f'<li>{item}</li>' for item in bullet_items) + '</ul>'
        processed_lines.append(bullet_html)
    
    text = '\n'.join(processed_lines)
    
    # Handle numbered lists (1. text, 2. text, etc.)
    lines = text.split('\n')
    processed_lines = []
    in_numbered_list = False
    numbered_items = []
    
    for line in lines:
        # Check if line starts with number
        numbered_match = re.match(r'^(\d+)\.\s+(.+)$', line.strip())
        if numbered_match:
            if not in_numbered_list:
                in_numbered_list = True
            numbered_items.append(numbered_match.group(2))
        else:
            # End of numbered list
            if in_numbered_list:
                if numbered_items:
                    numbered_html = '<ol>' + ''.join(f'<li>{item}</li>' for item in numbered_items) + '</ol>'
                    processed_lines.append(numbered_html)
                numbered_items = []
                in_numbered_list = False
            processed_lines.append(line)
    
    # Handle any remaining numbered list
    if in_numbered_list and numbered_items:
        numbered_html = '<ol>' + ''.join(f'<li>{item}</li>' for item in numbered_items) + '</ol>'
        processed_lines.append(numbered_html)
    
    text = '\n'.join(processed_lines)
    
    # Handle bold (*text*) - after lists to avoid conflicts
    text = re.sub(r'\*([^*]+)\*', r'<strong>\1</strong>', text)
    
    # Handle italic (_text_)
    text = re.sub(r'_([^_]+)_', r'<em>\1</em>', text)
    
    # Handle strikethrough (~text~)
    text = re.sub(r'~([^~]+)~', r'<del>\1</del>', text)
    
    # Convert line breaks to <br> tags
    text = text.replace('\n', '<br>')
    
    return mark_safe(text)

@register.filter
def whatsapp_markdown_preview(value):
    """
    Convert WhatsApp markdown to HTML with WhatsApp-like styling.
    """
    if not value:
        return value
    
    # First apply the basic markdown conversion
    html = whatsapp_markdown(value)
    
    # Add WhatsApp-specific styling classes
    html = html.replace('<strong>', '<span class="whatsapp-bold">')
    html = html.replace('</strong>', '</span>')
    html = html.replace('<em>', '<span class="whatsapp-italic">')
    html = html.replace('</em>', '</span>')
    html = html.replace('<del>', '<span class="whatsapp-strikethrough">')
    html = html.replace('</del>', '</span>')
    html = html.replace('<code>', '<span class="whatsapp-code">')
    html = html.replace('</code>', '</span>')
    html = html.replace('<pre><code>', '<div class="whatsapp-monospace">')
    html = html.replace('</code></pre>', '</div>')
    html = html.replace('<blockquote>', '<div class="whatsapp-quote">')
    html = html.replace('</blockquote>', '</div>')
    html = html.replace('<ul>', '<div class="whatsapp-bullet-list">')
    html = html.replace('</ul>', '</div>')
    html = html.replace('<ol>', '<div class="whatsapp-numbered-list">')
    html = html.replace('</ol>', '</div>')
    html = html.replace('<li>', '<div class="whatsapp-list-item">')
    html = html.replace('</li>', '</div>')
    
    return mark_safe(html)
