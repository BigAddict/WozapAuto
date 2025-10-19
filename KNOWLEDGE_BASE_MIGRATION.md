# Knowledge Base System Migration Guide

## Overview

The knowledge base system has been upgraded to use full 3072-dimensional Google Gemini embeddings for significantly better retrieval quality. This migration includes configurable settings, improved similarity thresholds, and automated migration tools.

## 🚀 Quick Migration (Recommended)

For a complete, automated migration:

```bash
python manage.py update_kb_system
```

This single command will:
1. **Backup** all existing data
2. **Clean** the knowledge base table
3. **Migrate** the database schema
4. **Restore** all documents with new embeddings
5. **Report** the results

## 📋 Migration Options

### Complete Migration
```bash
# Full migration with backup
python manage.py update_kb_system

# Dry run to see what would happen
python manage.py update_kb_system --dry-run

# Custom backup location
python manage.py update_kb_system --backup-dir /tmp/kb_backup

# Keep backup files after migration
python manage.py update_kb_system --keep-backups
```

### Manual Steps (Alternative)
```bash
# 1. Check current status
python manage.py migrate_embeddings --check

# 2. Run complete migration
python manage.py update_kb_system

# 3. Verify results
python manage.py migrate_embeddings --check
```

## 🔧 What's New

### Enhanced Retrieval Quality
- **3072-dimensional embeddings** (up from 768)
- **Lower similarity threshold** (0.5 instead of 0.7)
- **Better semantic understanding**

### Configurable Settings
All parameters are now configurable via admin dashboard:
- Embedding dimensions (128-3072)
- Similarity threshold (0.0-1.0)
- Chunk size and overlap
- Max chunks in context
- Top K results

### User-Friendly Interface
- **Reprocessing interface**: `/knowledgebase/reprocess/`
- **Progress indicators** during reprocessing
- **Status badges** for document health
- **Bulk operations** for multiple documents

### Admin Tools
- **Settings management** with help text
- **Bulk regeneration** actions
- **Embedding statistics** display
- **User-specific configurations**

## 📊 Migration Process Details

### Phase 1: Backup
- Exports all KnowledgeBase records to JSON
- Preserves user ownership and file metadata
- Creates file integrity manifest
- Compresses backup for efficiency

### Phase 2: Clean
- Deletes all KnowledgeBase records
- Preserves original PDF files in `media/knowledge_base/`
- Verifies file integrity before deletion

### Phase 3: Migrate
- Runs Django migrations
- Creates KnowledgeBaseSettings table
- Updates embedding field to 3072 dimensions
- Creates default settings for all users

### Phase 4: Restore
- Re-uploads all PDFs using new system
- Generates 3072-dimensional embeddings
- Preserves original metadata and ownership
- Handles errors gracefully

### Phase 5: Cleanup
- Generates migration report
- Optionally removes backup files
- Shows final statistics and next steps

## 🛡️ Safety Features

### Backup & Recovery
- **Complete backup** before any changes
- **File integrity checks** throughout process
- **Rollback capability** if needed
- **Detailed logging** for debugging

### Error Handling
- **Graceful failure** with detailed error messages
- **Resume functionality** for interrupted migrations
- **File verification** before and after operations
- **Transaction safety** for database operations

### Validation
- **Missing file detection** with warnings
- **User existence verification**
- **Settings validation** with helpful error messages
- **Progress tracking** with clear status updates

## 📈 Performance Impact

### Storage Requirements
- **4x more storage** for embeddings (768 → 3072 dimensions)
- **Better compression** with pgvector
- **Efficient indexing** for fast retrieval

### API Costs
- **Google Gemini API** charges per embedding call
- **One-time cost** for migration
- **Ongoing costs** for new uploads

### Retrieval Quality
- **Significantly better** semantic understanding
- **More relevant results** with lower threshold
- **Improved context** for AI responses

## 🔍 Troubleshooting

### Common Issues

#### Migration Fails
```bash
# Check current status
python manage.py migrate_embeddings --check

# Run with force flag
python manage.py update_kb_system --force
```

#### Missing PDF Files
```bash
# Check file integrity
python manage.py update_kb_system --dry-run

# The system will warn about missing files
```

#### API Key Issues
```bash
# Verify Google API key in settings
python manage.py shell
>>> from django.conf import settings
>>> print(settings.GOOGLE_API_KEY)
```

### Recovery Options

#### Restore from Backup
```bash
# If migration fails, restore from backup
# (Backup files are preserved by default)
```

#### Manual Reprocessing
```bash
# Users can reprocess individual documents via web interface
# Visit: /knowledgebase/reprocess/
```

## 📚 Usage After Migration

### For Users
1. **Upload new documents** - automatically use 3072 dimensions
2. **Reprocess documents** - via `/knowledgebase/reprocess/`
3. **Search knowledge base** - improved results with lower threshold

### For Administrators
1. **Configure settings** - via admin dashboard
2. **Monitor usage** - check embedding statistics
3. **Bulk operations** - regenerate embeddings for multiple users

### For Developers
1. **Use new service** - `KnowledgeBaseService(user=user)`
2. **Access settings** - `service.settings.similarity_threshold`
3. **Customize parameters** - all settings are configurable

## 🎯 Next Steps

After successful migration:

1. **Test knowledge base search** - verify improved results
2. **Adjust settings** - fine-tune parameters via admin
3. **Monitor performance** - check API usage and storage
4. **Train users** - show them the new reprocessing interface

## 📞 Support

If you encounter issues:

1. **Check logs** - detailed logging in Django logs
2. **Run dry-run** - `python manage.py update_kb_system --dry-run`
3. **Verify files** - ensure PDF files exist in `media/knowledge_base/`
4. **Check API key** - verify Google Gemini API configuration

The migration system is designed to be safe, automated, and recoverable. The complete process typically takes a few minutes depending on the number of documents and API response times.
