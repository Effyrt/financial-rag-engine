#!/usr/bin/env python3
"""
Financial RAG Engine - Concept Seeding DAG
Cloud Run Job for seeding vector store with financial concepts and updating embeddings
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from google.cloud import storage
from google.cloud import secretmanager
import subprocess
import tempfile
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConceptSeedDAG:
    """
    DAG for seeding vector store with financial concepts and updating embeddings
    """
    
    def __init__(self, 
                 project_id: str,
                 region: str = "us-central1",
                 bucket_name: str = "financial-rag-artifacts",
                 secret_name: str = "financial-rag-secrets"):
        self.project_id = project_id
        self.region = region
        self.bucket_name = bucket_name
        self.secret_name = secret_name
        
        # Initialize GCP clients
        self.storage_client = storage.Client(project=project_id)
        self.secret_client = secretmanager.SecretManagerServiceClient()
        
        # Ensure bucket exists
        self._ensure_bucket_exists()
        
    def _ensure_bucket_exists(self):
        """Create GCS bucket if it doesn't exist"""
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            if not bucket.exists():
                bucket = self.storage_client.create_bucket(
                    self.bucket_name, 
                    location=self.region
                )
                logger.info(f"Created bucket: {self.bucket_name}")
            else:
                logger.info(f"Bucket exists: {self.bucket_name}")
        except Exception as e:
            logger.error(f"Error creating bucket: {e}")
            raise
    
    def _get_secret(self, secret_key: str) -> str:
        """Retrieve secret from Secret Manager"""
        try:
            secret_path = f"projects/{self.project_id}/secrets/{self.secret_name}/versions/latest"
            response = self.secret_client.access_secret_version(request={"name": secret_path})
            secrets = json.loads(response.payload.data.decode("UTF-8"))
            return secrets[secret_key]
        except Exception as e:
            logger.error(f"Error retrieving secret {secret_key}: {e}")
            raise
    
    def _download_concept_data(self, concept_file_path: str) -> str:
        """Download concept data from GCS"""
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(concept_file_path)
            
            # Create temp file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
            blob.download_to_filename(temp_file.name)
            
            logger.info(f"Downloaded concept data: {concept_file_path} -> {temp_file.name}")
            return temp_file.name
        except Exception as e:
            logger.error(f"Error downloading concept data: {e}")
            raise
    
    def _upload_artifacts_to_gcs(self, local_dir: str, gcs_prefix: str):
        """Upload processing artifacts to GCS"""
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            
            for root, dirs, files in os.walk(local_dir):
                for file in files:
                    local_path = os.path.join(root, file)
                    relative_path = os.path.relpath(local_path, local_dir)
                    gcs_path = f"{gcs_prefix}/{relative_path}"
                    
                    blob = bucket.blob(gcs_path)
                    blob.upload_from_filename(local_path)
                    logger.info(f"Uploaded: {relative_path} -> {gcs_path}")
                    
        except Exception as e:
            logger.error(f"Error uploading artifacts: {e}")
            raise
    
    def _generate_financial_concepts(self) -> List[Dict[str, Any]]:
        """Generate financial concepts for seeding"""
        concepts = [
            {
                "concept_id": "market_efficiency",
                "name": "Market Efficiency",
                "description": "The degree to which market prices reflect all available information",
                "category": "market_theory",
                "keywords": ["efficient market hypothesis", "EMH", "price discovery", "information"],
                "formulas": ["E[R] = Rf + β(Rm - Rf)"],
                "related_concepts": ["arbitrage", "anomalies", "behavioral finance"]
            },
            {
                "concept_id": "portfolio_optimization",
                "name": "Portfolio Optimization",
                "description": "The process of selecting the best portfolio from available assets",
                "category": "portfolio_management",
                "keywords": ["Markowitz", "efficient frontier", "risk-return", "diversification"],
                "formulas": ["σp² = Σwi²σi² + ΣΣwiwjσij"],
                "related_concepts": ["CAPM", "Sharpe ratio", "correlation"]
            },
            {
                "concept_id": "black_scholes",
                "name": "Black-Scholes Model",
                "description": "Mathematical model for pricing European options",
                "category": "derivatives",
                "keywords": ["option pricing", "volatility", "time decay", "Greeks"],
                "formulas": ["C = S₀N(d₁) - Ke^(-rT)N(d₂)"],
                "related_concepts": ["binomial model", "Monte Carlo", "implied volatility"]
            },
            {
                "concept_id": "var_calculation",
                "name": "Value at Risk (VaR)",
                "description": "Statistical measure of potential loss in value of a portfolio",
                "category": "risk_management",
                "keywords": ["risk metric", "confidence level", "loss probability"],
                "formulas": ["VaR = μ - σ × Zα"],
                "related_concepts": ["CVaR", "stress testing", "backtesting"]
            },
            {
                "concept_id": "monte_carlo",
                "name": "Monte Carlo Simulation",
                "description": "Computational method using random sampling for numerical results",
                "category": "computational_finance",
                "keywords": ["simulation", "random sampling", "stochastic", "convergence"],
                "formulas": ["E[f(X)] ≈ (1/N)Σf(xi)"],
                "related_concepts": ["bootstrap", "quasi-Monte Carlo", "variance reduction"]
            }
        ]
        
        logger.info(f"Generated {len(concepts)} financial concepts")
        return concepts
    
    def _seed_vector_store(self, concepts: List[Dict[str, Any]], 
                          use_chromadb: bool = True) -> Dict[str, Any]:
        """Seed vector store with financial concepts"""
        try:
            # Set up environment
            os.environ["OPENAI_API_KEY"] = self._get_secret("OPENAI_API_KEY")
            if not use_chromadb:
                os.environ["PINECONE_API_KEY"] = self._get_secret("PINECONE_API_KEY")
            
            # Create concept chunks
            concept_chunks = []
            for concept in concepts:
                # Create comprehensive text for each concept
                concept_text = f"""
                Financial Concept: {concept['name']}
                
                Description: {concept['description']}
                
                Category: {concept['category']}
                
                Keywords: {', '.join(concept['keywords'])}
                
                Formulas: {', '.join(concept['formulas'])}
                
                Related Concepts: {', '.join(concept['related_concepts'])}
                """
                
                concept_chunks.append({
                    "chunk_id": f"concept_{concept['concept_id']}",
                    "chunk_text": concept_text.strip(),
                    "concept_id": concept['concept_id'],
                    "concept_name": concept['name'],
                    "category": concept['category'],
                    "chunk_type": "concept_seed",
                    "source": "generated_concepts"
                })
            
            # Save concept chunks to file
            concept_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
            json.dump(concept_chunks, concept_file, indent=2)
            concept_file.close()
            
            # Generate embeddings and upload to vector store
            if use_chromadb:
                # Use ChromaDB seeding script
                cmd = [
                    "python", "scripts/seed_chromadb_concepts.py",
                    "--concepts-file", concept_file.name,
                    "--collection-name", "financial-concepts"
                ]
            else:
                # Use Pinecone seeding script
                cmd = [
                    "python", "scripts/seed_pinecone_concepts.py",
                    "--concepts-file", concept_file.name,
                    "--index-name", "financial-concepts"
                ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd="/app"
            )
            
            if result.returncode != 0:
                logger.error(f"Seeding failed: {result.stderr}")
                raise RuntimeError(f"Seeding failed: {result.stderr}")
            
            logger.info("✅ Vector store seeded successfully")
            
            return {
                "concepts_seeded": len(concept_chunks),
                "vector_store": "chromadb" if use_chromadb else "pinecone",
                "status": "completed"
            }
            
        except Exception as e:
            logger.error(f"Error seeding vector store: {e}")
            raise
        finally:
            # Cleanup
            try:
                if 'concept_file' in locals():
                    os.unlink(concept_file.name)
            except:
                pass
    
    def _update_existing_embeddings(self, 
                                   concept_file_path: str,
                                   use_chromadb: bool = True) -> Dict[str, Any]:
        """Update existing embeddings with new concept data"""
        try:
            # Download existing concept data
            local_concept_file = self._download_concept_data(concept_file_path)
            
            with open(local_concept_file, 'r') as f:
                existing_concepts = json.load(f)
            
            logger.info(f"Loaded {len(existing_concepts)} existing concepts")
            
            # Update embeddings
            if use_chromadb:
                cmd = [
                    "python", "scripts/update_chromadb_embeddings.py",
                    "--concepts-file", local_concept_file,
                    "--collection-name", "financial-concepts"
                ]
            else:
                cmd = [
                    "python", "scripts/update_pinecone_embeddings.py",
                    "--concepts-file", local_concept_file,
                    "--index-name", "financial-concepts"
                ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd="/app"
            )
            
            if result.returncode != 0:
                logger.error(f"Update failed: {result.stderr}")
                raise RuntimeError(f"Update failed: {result.stderr}")
            
            logger.info("✅ Embeddings updated successfully")
            
            return {
                "concepts_updated": len(existing_concepts),
                "vector_store": "chromadb" if use_chromadb else "pinecone",
                "status": "completed"
            }
            
        except Exception as e:
            logger.error(f"Error updating embeddings: {e}")
            raise
        finally:
            # Cleanup
            try:
                if 'local_concept_file' in locals():
                    os.unlink(local_concept_file)
            except:
                pass
    
    def run_concept_seeding(self,
                           mode: str = "generate",  # "generate" or "update"
                           concept_file_path: Optional[str] = None,
                           use_chromadb: bool = True) -> Dict[str, Any]:
        """
        Run concept seeding workflow
        
        Args:
            mode: "generate" for new concepts, "update" for existing
            concept_file_path: Path to existing concept file (for update mode)
            use_chromadb: Use ChromaDB instead of Pinecone
        """
        logger.info("🌱 Starting Concept Seed DAG")
        logger.info(f"   Mode: {mode}")
        logger.info(f"   ChromaDB: {use_chromadb}")
        
        # Create timestamp for this run
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_id = f"concept_seed_{timestamp}"
        
        try:
            if mode == "generate":
                # Generate new concepts and seed
                logger.info("📝 Generating financial concepts")
                concepts = self._generate_financial_concepts()
                
                logger.info("🌱 Seeding vector store with new concepts")
                result = self._seed_vector_store(concepts, use_chromadb)
                
            elif mode == "update":
                if not concept_file_path:
                    raise ValueError("concept_file_path required for update mode")
                
                logger.info("🔄 Updating existing embeddings")
                result = self._update_existing_embeddings(concept_file_path, use_chromadb)
                
            else:
                raise ValueError(f"Invalid mode: {mode}")
            
            # Step 4: Upload artifacts to GCS
            logger.info("📤 Uploading artifacts to GCS")
            artifacts_prefix = f"concept_artifacts/{run_id}"
            self._upload_artifacts_to_gcs("data/processed", artifacts_prefix)
            
            # Step 5: Update metadata
            metadata = {
                "run_id": run_id,
                "timestamp": timestamp,
                "mode": mode,
                "use_chromadb": use_chromadb,
                "status": "completed",
                "artifacts_prefix": artifacts_prefix,
                **result
            }
            
            # Save metadata to GCS
            metadata_blob = self.storage_client.bucket(self.bucket_name).blob(
                f"{artifacts_prefix}/concept_seed_metadata.json"
            )
            metadata_blob.upload_from_string(json.dumps(metadata, indent=2))
            
            logger.info(f"✅ Concept Seed DAG completed successfully: {run_id}")
            return metadata
            
        except Exception as e:
            logger.error(f"❌ Concept Seed DAG failed: {e}")
            
            # Upload error logs
            error_metadata = {
                "run_id": run_id,
                "timestamp": timestamp,
                "mode": mode,
                "status": "failed",
                "error": str(e)
            }
            
            try:
                error_blob = self.storage_client.bucket(self.bucket_name).blob(
                    f"concept_artifacts/{run_id}/error_metadata.json"
                )
                error_blob.upload_from_string(json.dumps(error_metadata, indent=2))
            except:
                pass  # Don't fail on error logging
            
            raise

def main():
    """Main entry point for Cloud Run Job"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Concept Seed DAG")
    parser.add_argument("--project-id", required=True, help="GCP Project ID")
    parser.add_argument("--mode", choices=["generate", "update"], default="generate",
                       help="Mode: generate new concepts or update existing")
    parser.add_argument("--concept-file-path", help="Path to concept file (for update mode)")
    parser.add_argument("--use-chromadb", action="store_true", help="Use ChromaDB")
    parser.add_argument("--region", default="us-central1", help="GCP Region")
    parser.add_argument("--bucket", default="financial-rag-artifacts", help="GCS Bucket")
    
    args = parser.parse_args()
    
    # Create and run DAG
    dag = ConceptSeedDAG(
        project_id=args.project_id,
        region=args.region,
        bucket_name=args.bucket
    )
    
    result = dag.run_concept_seeding(
        mode=args.mode,
        concept_file_path=args.concept_file_path,
        use_chromadb=args.use_chromadb
    )
    
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
