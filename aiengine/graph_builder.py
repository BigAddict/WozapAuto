"""
Graph building service for knowledge base visualization.

This module provides functionality to build interactive graph data from
knowledge base entries using vector similarity, content references, and
explicit relationships.
"""

import logging
from django.db.models import Q
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import networkx as nx
from .models import KnowledgeBase, DocumentRelationship, DocumentTag

logger = logging.getLogger('aiengine.graph_builder')


class KnowledgeGraphBuilder:
    """
    Builds graph data for knowledge base visualization.
    
    Combines multiple relationship types:
    - Vector similarity (using embeddings)
    - Content-based references (document name mentions)
    - Explicit relationships (manual links)
    - Shared tags
    """
    
    def __init__(self, user):
        self.user = user
    
    def build_graph_data(self, similarity_threshold=0.5, max_connections=10):
        """
        Build complete graph data with nodes and edges.
        
        Args:
            similarity_threshold: Minimum similarity score for vector connections (lowered to 0.5)
            max_connections: Maximum connections per node from similarity (increased to 10)
            
        Returns:
            dict: Graph data with nodes, edges, and metadata
        """
        try:
            # Get all documents for the user
            documents = KnowledgeBase.objects.filter(user=self.user)
            
            if not documents.exists():
                return {
                    'nodes': [],
                    'edges': [],
                    'total_nodes': 0,
                    'total_edges': 0,
                    'message': 'No documents found in knowledge base'
                }
            
            # Build nodes
            nodes = []
            for doc in documents:
                nodes.append({
                    'id': doc.id,
                    'name': doc.name,
                    'type': doc.file_type,
                    'content_preview': doc.content[:100] if doc.content else '',
                    'file_type': doc.file_type,
                    'created_at': doc.created_at.isoformat(),
                    'metadata': doc.metadata or {},
                    'original_filename': doc.original_filename or '',
                    'chunk_index': doc.chunk_index,
                    'parent_file_id': doc.parent_file_id or '',
                    'file_size': doc.file_size or 0
                })
            
            # Build edges from multiple sources
            edges = []
            
            # 1. Explicit relationships (only if models exist)
            try:
                explicit_edges = self._get_explicit_relationships(documents)
                edges.extend(explicit_edges)
                logger.info(f"Found {len(explicit_edges)} explicit relationships")
            except Exception as e:
                logger.warning(f"Could not get explicit relationships: {e}")
            
            # 2. Vector similarity edges
            try:
                similarity_edges = self._get_similarity_edges(documents, similarity_threshold, max_connections)
                edges.extend(similarity_edges)
                logger.info(f"Found {len(similarity_edges)} similarity edges")
            except Exception as e:
                logger.warning(f"Could not get similarity edges: {e}")
            
            # 3. Content-based links (like [[links]] in Obsidian)
            try:
                content_edges = self._get_content_based_links(documents)
                edges.extend(content_edges)
                logger.info(f"Found {len(content_edges)} content-based links")
            except Exception as e:
                logger.warning(f"Could not get content-based links: {e}")
            
            # 4. Shared tag relationships (only if models exist)
            try:
                tag_edges = self._get_shared_tag_edges(documents)
                edges.extend(tag_edges)
                logger.info(f"Found {len(tag_edges)} shared tag edges")
            except Exception as e:
                logger.warning(f"Could not get shared tag edges: {e}")
            
            return {
                'nodes': nodes,
                'edges': edges,
                'total_nodes': len(nodes),
                'total_edges': len(edges),
                'message': f'Found {len(nodes)} documents with {len(edges)} relationships'
            }
            
        except Exception as e:
            logger.error(f"Error building graph data: {e}")
            return {
                'nodes': [],
                'edges': [],
                'total_nodes': 0,
                'total_edges': 0,
                'error': str(e)
            }
    
    def _get_explicit_relationships(self, documents):
        """Get manually created relationships between documents."""
        relationships = DocumentRelationship.objects.filter(
            source__in=documents
        ).select_related('source', 'target')
        
        edges = []
        for rel in relationships:
            edges.append({
                'source': rel.source_id,
                'target': rel.target_id,
                'type': rel.relationship_type,
                'strength': rel.strength,
                'metadata': rel.metadata or {}
            })
        return edges
    
    def _get_similarity_edges(self, documents, threshold, max_connections):
        """Calculate vector similarity edges between documents."""
        if not documents:
            return []
        
        # Get embeddings
        doc_embeddings = []
        valid_docs = []
        
        for doc in documents:
            if doc.embedding is not None and len(doc.embedding) > 0:
                doc_embeddings.append(doc.embedding)
                valid_docs.append(doc)
        
        if len(doc_embeddings) < 2:
            return []  # Need at least 2 documents to create relationships
        
        try:
            # Calculate similarity matrix
            similarity_matrix = cosine_similarity(doc_embeddings)
            
            edges = []
            for i, doc1 in enumerate(valid_docs):
                # Get top similar documents
                similarities = list(enumerate(similarity_matrix[i]))
                # Remove self-similarity and sort
                similarities = [(j, sim) for j, sim in similarities if j != i]
                similarities.sort(key=lambda x: x[1], reverse=True)
                
                # Add top connections
                for j, sim in similarities[:max_connections]:
                    if sim > threshold:
                        doc2 = valid_docs[j]
                        edges.append({
                            'source': doc1.id,
                            'target': doc2.id,
                            'type': 'SIMILAR',
                            'strength': float(sim),
                            'metadata': {'similarity_score': float(sim)}
                        })
            
            return edges
            
        except Exception as e:
            logger.error(f"Error calculating similarity matrix: {e}")
            return []
    
    def _get_content_based_links(self, documents):
        """Find document name mentions in content (like Obsidian [[links]])."""
        edges = []
        doc_name_map = {doc.name.lower(): doc.id for doc in documents}
        
        for doc in documents:
            if not doc.content:
                continue
            
            content_lower = doc.content.lower()
            
            # Look for document names mentioned in content
            for target_name, target_id in doc_name_map.items():
                if target_name != doc.name.lower() and target_name in content_lower:
                    edges.append({
                        'source': doc.id,
                        'target': target_id,
                        'type': 'REFERENCE',
                        'strength': 0.8,
                        'metadata': {'mentioned_as': target_name}
                    })
        
        return edges
    
    def _get_shared_tag_edges(self, documents):
        """Create edges between documents that share tags."""
        edges = []
        
        # Get all tags for these documents
        tags = DocumentTag.objects.filter(knowledge_base__in=documents)
        
        # Group documents by tag
        tag_groups = {}
        for tag in tags:
            doc_id = tag.knowledge_base_id
            tag_name = tag.name
            if tag_name not in tag_groups:
                tag_groups[tag_name] = []
            tag_groups[tag_name].append(doc_id)
        
        # Create edges between documents in the same tag group
        for tag_name, doc_ids in tag_groups.items():
            if len(doc_ids) > 1:
                # Create edges between all pairs in the group
                for i, doc1_id in enumerate(doc_ids):
                    for doc2_id in doc_ids[i+1:]:
                        edges.append({
                            'source': doc1_id,
                            'target': doc2_id,
                            'type': 'TAG',
                            'strength': 0.9,
                            'metadata': {'shared_tag': tag_name}
                        })
        
        return edges
    
    def calculate_node_positions(self, nodes, edges):
        """
        Calculate 2D positions for visualization using force-directed layout.
        
        Args:
            nodes: List of node dictionaries
            edges: List of edge dictionaries
            
        Returns:
            List of nodes with x, y coordinates added
        """
        G = nx.Graph()
        
        # Add nodes
        for node in nodes:
            G.add_node(node['id'])
        
        # Add edges with weights
        for edge in edges:
            G.add_edge(edge['source'], edge['target'], weight=edge.get('strength', 1.0))
        
        # Use spring layout for force-directed positioning
        pos = nx.spring_layout(G, k=1, iterations=50)
        
        # Update nodes with positions
        for node in nodes:
            node_id = node['id']
            if node_id in pos:
                node['x'] = float(pos[node_id][0])
                node['y'] = float(pos[node_id][1])
            else:
                node['x'] = 0.0
                node['y'] = 0.0
        
        return nodes
