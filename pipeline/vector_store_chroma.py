"""
Vector Store Module using ChromaDB.

This module provides functionality to store and query vector embeddings
in ChromaDB vector database. ChromaDB is better for this use case as it
doesn't have namespace limitations like Pinecone.
"""

import logging
from typing import List, Dict, Any, Optional
import os
import sys

# Add global Python path for ChromaDB
sys.path.append('/opt/homebrew/lib/python3.13/site-packages')

import chromadb
from chromadb.config import Settings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChromaVectorStore:
    """
    Vector store interface for ChromaDB.
    
    Handles upserting vectors, querying, and managing the ChromaDB collection.
    Uses collections instead of namespaces for topic organization.
    """
    
    def __init__(
        self,
        collection_name: str = "financial-concepts",
        dimension: int = 3072,
        distance_metric: str = "cosine",
        persist_directory: str = "./data/chroma_db"
    ) -> None:
        """
        Initialize ChromaVectorStore.
        
        Args:
            collection_name: Name of the ChromaDB collection
            dimension: Embedding dimension (3072 for text-embedding-3-large)
            distance_metric: Distance metric (cosine, l2, ip)
            persist_directory: Directory to persist the database
        """
        self.collection_name = collection_name
        self.dimension = dimension
        self.distance_metric = distance_metric
        self.persist_directory = persist_directory
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Get or create collection
        self.collection = self._get_or_create_collection()
        
        logger.info(
            f"ChromaVectorStore initialized: "
            f"collection={collection_name}, dimension={dimension}, metric={distance_metric}"
        )
    
    def _get_or_create_collection(self):
        """Get existing collection or create new one."""
        try:
            # Try to get existing collection
            collection = self.client.get_collection(name=self.collection_name)
            logger.info(f"Using existing collection: {self.collection_name}")
            return collection
        except Exception:
            # Create new collection
            collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": self.distance_metric}
            )
            logger.info(f"Created new collection: {self.collection_name}")
            return collection
    
    def upsert_vectors(
        self,
        chunks: List[Dict[str, Any]],
        batch_size: int = 100,
        collection_name: str = None
    ) -> Dict[str, Any]:
        """
        Upsert vectors to ChromaDB collection.
        
        Args:
            chunks: List of chunk dictionaries with embeddings
            batch_size: Number of vectors to process per batch
            collection_name: Override collection name (uses topic as collection)
            
        Returns:
            Dictionary with upsert results
        """
        if not chunks:
            logger.warning("No chunks provided for upsert")
            return {"upserted_count": 0}
        
        # Group chunks by topic for collection organization
        chunks_by_topic = {}
        for chunk in chunks:
            if "embedding" not in chunk:
                logger.warning(f"Skipping chunk {chunk.get('chunk_id', 'unknown')}: no embedding")
                continue
            
            topic = chunk.get('topic', 'default')
            if topic not in chunks_by_topic:
                chunks_by_topic[topic] = []
            chunks_by_topic[topic].append(chunk)
        
        total_upserted = 0
        
        # Process each topic as a separate collection
        for topic, topic_chunks in chunks_by_topic.items():
            if not topic_chunks:
                continue
                
            # Create topic-specific collection name
            topic_collection_name = f"{self.collection_name}_{topic.replace('-', '_')}"
            
            try:
                # Get or create topic collection
                try:
                    topic_collection = self.client.get_collection(name=topic_collection_name)
                except Exception:
                    topic_collection = self.client.create_collection(
                        name=topic_collection_name,
                        metadata={"hnsw:space": self.distance_metric}
                    )
                
                # Prepare data for ChromaDB
                ids = []
                embeddings = []
                metadatas = []
                documents = []
                
                for chunk in topic_chunks:
                    ids.append(chunk["chunk_id"])
                    embeddings.append(chunk["embedding"])
                    documents.append(chunk.get("chunk_text", ""))
                    
                    # Prepare metadata (exclude embedding and large text fields)
                    metadata = {
                        k: v for k, v in chunk.items()
                        if k not in ["embedding", "chunk_text"] and not isinstance(v, list)
                    }
                    
                    # Add topic to metadata
                    metadata["topic"] = topic
                    metadata["source"] = chunk.get("source_file", "unknown")
                    
                    # Truncate long text fields
                    if "chunk_text" in chunk and len(chunk["chunk_text"]) > 1000:
                        metadata["text_preview"] = chunk["chunk_text"][:1000] + "..."
                    
                    metadatas.append(metadata)
                
                # Upsert in batches
                for i in range(0, len(ids), batch_size):
                    batch_ids = ids[i:i + batch_size]
                    batch_embeddings = embeddings[i:i + batch_size]
                    batch_metadatas = metadatas[i:i + batch_size]
                    batch_documents = documents[i:i + batch_size]
                    
                    topic_collection.upsert(
                        ids=batch_ids,
                        embeddings=batch_embeddings,
                        metadatas=batch_metadatas,
                        documents=batch_documents
                    )
                
                upserted_count = len(ids)
                total_upserted += upserted_count
                
                logger.info(
                    f"Topic '{topic}': Upserted {upserted_count} vectors "
                    f"to collection '{topic_collection_name}'"
                )
                
            except Exception as e:
                logger.error(f"Error upserting topic '{topic}': {e}")
                raise
        
        logger.info(f"✅ Total upserted: {total_upserted} vectors across {len(chunks_by_topic)} topics")
        
        return {
            "upserted_count": total_upserted,
            "collection_name": self.collection_name,
            "topics_processed": len(chunks_by_topic)
        }
    
    def query_vectors(
        self,
        query_vector: List[float],
        top_k: int = 5,
        topic: str = None,
        filter_dict: Optional[Dict[str, Any]] = None,
        include_metadata: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Query vectors from ChromaDB across all collections.
        
        Args:
            query_vector: Query embedding vector
            top_k: Number of results to return
            topic: Specific topic to search (None for all topics)
            filter_dict: Metadata filters
            include_metadata: Whether to include metadata in results
            
        Returns:
            List of query results
        """
        try:
            if topic:
                # Query specific topic collection
                topic_collection_name = f"{self.collection_name}_{topic.replace('-', '_')}"
                try:
                    collection = self.client.get_collection(name=topic_collection_name)
                    return self._query_single_collection(collection, query_vector, top_k, filter_dict, include_metadata)
                except Exception:
                    logger.warning(f"Topic collection '{topic_collection_name}' not found")
                    return []
            else:
                # Query ALL collections and combine results
                return self._query_all_collections(query_vector, top_k, filter_dict, include_metadata)
                
        except Exception as e:
            logger.error(f"Error querying vectors: {e}")
            return []
    
    def _query_single_collection(self, collection, query_vector: List[float], top_k: int, 
                                filter_dict: Optional[Dict[str, Any]], include_metadata: bool) -> List[Dict[str, Any]]:
        """Query a single collection."""
        # Prepare where clause for filtering
        where_clause = {}
        if filter_dict:
            where_clause.update(filter_dict)
        
        # Query the collection
        results = collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            where=where_clause if where_clause else None,
            include=["metadatas", "documents", "distances"] if include_metadata else ["distances"]
        )
        
        # Format results
        formatted_results = []
        if results["ids"] and results["ids"][0]:
            for i, chunk_id in enumerate(results["ids"][0]):
                result = {
                    "id": chunk_id,
                    "score": 1 - results["distances"][0][i]  # Convert distance to similarity
                }
                
                if include_metadata:
                    if results.get("metadatas") and results["metadatas"][0]:
                        result["metadata"] = results["metadatas"][0][i]
                    if results.get("documents") and results["documents"][0]:
                        result["document"] = results["documents"][0][i]
                
                formatted_results.append(result)
        
        return formatted_results
    
    def _query_all_collections(self, query_vector: List[float], top_k: int, 
                              filter_dict: Optional[Dict[str, Any]], include_metadata: bool) -> List[Dict[str, Any]]:
        """Query all collections and combine results."""
        all_results = []
        
        # Get all collections
        collections = self.client.list_collections()
        
        for collection_info in collections:
            collection_name = collection_info.name
            try:
                collection = self.client.get_collection(name=collection_name)
                
                # Query this collection
                results = self._query_single_collection(collection, query_vector, top_k, filter_dict, include_metadata)
                
                # Add collection info to results
                for result in results:
                    result["collection"] = collection_name
                
                all_results.extend(results)
                
            except Exception as e:
                logger.warning(f"Error querying collection {collection_name}: {e}")
                continue
        
        # Sort by score (higher is better) and return top_k
        all_results.sort(key=lambda x: x.get("score", 0.0), reverse=True)
        logger.info(f"Query returned {len(all_results[:top_k])} results from {len(collections)} collections")
        return all_results[:top_k]
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get collection statistics.
        
        Returns:
            Dictionary with collection statistics
        """
        try:
            # Get all collections
            collections = self.client.list_collections()
            
            stats = {
                "total_collections": len(collections),
                "collections": {}
            }
            
            for collection in collections:
                try:
                    count = collection.count()
                    stats["collections"][collection.name] = {
                        "vector_count": count,
                        "metadata": collection.metadata
                    }
                except Exception as e:
                    logger.warning(f"Could not get stats for collection {collection.name}: {e}")
                    stats["collections"][collection.name] = {"error": str(e)}
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            raise
    
    def delete_collection(self, collection_name: str = None) -> None:
        """
        Delete a collection.
        
        Args:
            collection_name: Name of collection to delete (None for main collection)
        """
        try:
            target_collection = collection_name or self.collection_name
            self.client.delete_collection(name=target_collection)
            logger.info(f"Deleted collection: {target_collection}")
        except Exception as e:
            logger.error(f"Error deleting collection: {e}")
            raise


def main():
    """Test the ChromaDB vector store."""
    print("\n" + "="*60)
    print("CHROMADB VECTOR STORE TEST")
    print("="*60 + "\n")
    
    try:
        # Initialize vector store
        vector_store = ChromaVectorStore(
            collection_name="financial-concepts-test",
            dimension=3072,
            distance_metric="cosine"
        )
        
        # Get stats
        stats = vector_store.get_collection_stats()
        
        print("📊 Collection Statistics:")
        print(f"  Total collections: {stats['total_collections']}")
        
        for name, info in stats['collections'].items():
            if 'vector_count' in info:
                print(f"  - {name}: {info['vector_count']:,} vectors")
            else:
                print(f"  - {name}: {info.get('error', 'Unknown error')}")
        
        print("\n✅ ChromaDB vector store test complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nMake sure you have:")
        print("1. ChromaDB installed: pip install chromadb")
        print("2. Sufficient disk space for persistence")


if __name__ == "__main__":
    main()
