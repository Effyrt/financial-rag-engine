-- AURELIA Database Initialization Script - ENTERPRISE VERSION
-- PostgreSQL 15+ with complete schema, indexes, and functions

-- Connect to database
\c aurelia;

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search
CREATE EXTENSION IF NOT EXISTS "btree_gin";  -- For advanced indexing

-- Create enum types
DO $$ BEGIN
    CREATE TYPE source_type AS ENUM ('pdf', 'wikipedia', 'hybrid');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE concept_status AS ENUM ('active', 'outdated', 'pending', 'error');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- ============================================================================
-- Main Concept Notes Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS concept_notes (
    id SERIAL PRIMARY KEY,
    concept_name VARCHAR(255) UNIQUE NOT NULL,
    category VARCHAR(100) NOT NULL,
    aliases JSONB DEFAULT '[]'::jsonb,
    definition TEXT NOT NULL,
    detailed_explanation TEXT NOT NULL,
    key_points JSONB NOT NULL,
    formulas JSONB DEFAULT '[]'::jsonb,
    use_cases JSONB NOT NULL,
    code_examples JSONB DEFAULT '[]'::jsonb,
    prerequisites JSONB DEFAULT '[]'::jsonb,
    related_concepts JSONB DEFAULT '[]'::jsonb,
    primary_source source_type NOT NULL,
    citations JSONB NOT NULL,
    confidence_score FLOAT NOT NULL CHECK (confidence_score >= 0 AND confidence_score <= 1),
    status concept_status DEFAULT 'active',
    model_used VARCHAR(100) NOT NULL,
    version VARCHAR(20) DEFAULT '1.0',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_accessed TIMESTAMP,
    access_count INTEGER DEFAULT 0
);

-- Indexes for concept_notes
CREATE INDEX IF NOT EXISTS idx_concept_name ON concept_notes(concept_name);
CREATE INDEX IF NOT EXISTS idx_concept_category_status ON concept_notes(category, status);
CREATE INDEX IF NOT EXISTS idx_concept_source_status ON concept_notes(primary_source, status);
CREATE INDEX IF NOT EXISTS idx_concept_confidence_status ON concept_notes(confidence_score DESC, status);
CREATE INDEX IF NOT EXISTS idx_concept_updated_status ON concept_notes(updated_at DESC, status);
CREATE INDEX IF NOT EXISTS idx_concept_name_trgm ON concept_notes USING gin(concept_name gin_trgm_ops);

-- ============================================================================
-- Query Tracking Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS concept_queries (
    id SERIAL PRIMARY KEY,
    query_text TEXT NOT NULL,
    concept_name_resolved VARCHAR(255),
    source_used source_type NOT NULL,
    confidence_score FLOAT,
    contexts_count INTEGER,
    retrieval_time_ms INTEGER,
    generation_time_ms INTEGER,
    total_time_ms INTEGER,
    was_cached BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    user_agent VARCHAR(255),
    session_id VARCHAR(100)
);

-- Indexes for concept_queries
CREATE INDEX IF NOT EXISTS idx_query_created ON concept_queries(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_query_cached ON concept_queries(was_cached);
CREATE INDEX IF NOT EXISTS idx_query_session ON concept_queries(session_id);
CREATE INDEX IF NOT EXISTS idx_query_concept ON concept_queries(concept_name_resolved);

-- ============================================================================
-- Vector Index Metadata Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS vector_index_metadata (
    id SERIAL PRIMARY KEY,
    index_name VARCHAR(100) NOT NULL,
    namespace VARCHAR(100),
    vector_db_type VARCHAR(50) NOT NULL,
    total_vectors INTEGER,
    dimension INTEGER,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    update_source VARCHAR(100),
    chunks_added INTEGER DEFAULT 0,
    chunks_updated INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE
);

-- Indexes for vector_index_metadata
CREATE INDEX IF NOT EXISTS idx_vector_index_name ON vector_index_metadata(index_name);
CREATE INDEX IF NOT EXISTS idx_vector_namespace ON vector_index_metadata(namespace);
CREATE INDEX IF NOT EXISTS idx_vector_updated ON vector_index_metadata(last_updated DESC);

-- ============================================================================
-- Concept Seed Jobs Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS concept_seed_jobs (
    id SERIAL PRIMARY KEY,
    dag_run_id VARCHAR(255) NOT NULL,
    execution_date TIMESTAMP NOT NULL,
    concepts_list JSONB NOT NULL,
    total_concepts INTEGER NOT NULL,
    processed_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    skipped_count INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'running',
    error_message TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    duration_seconds INTEGER
);

-- Indexes for concept_seed_jobs
CREATE INDEX IF NOT EXISTS idx_seed_dag_run ON concept_seed_jobs(dag_run_id);
CREATE INDEX IF NOT EXISTS idx_seed_execution ON concept_seed_jobs(execution_date DESC);
CREATE INDEX IF NOT EXISTS idx_seed_status ON concept_seed_jobs(status);

-- ============================================================================
-- System Health Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS system_health (
    id SERIAL PRIMARY KEY,
    vector_db_status VARCHAR(20) DEFAULT 'unknown',
    database_status VARCHAR(20) DEFAULT 'unknown',
    api_status VARCHAR(20) DEFAULT 'unknown',
    embedding_service_status VARCHAR(20) DEFAULT 'unknown',
    avg_query_time_ms FLOAT,
    cache_hit_rate FLOAT,
    total_concepts_cached INTEGER,
    disk_usage_percent FLOAT,
    memory_usage_percent FLOAT,
    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Index for system_health
CREATE INDEX IF NOT EXISTS idx_health_checked ON system_health(checked_at DESC);

-- ============================================================================
-- Functions and Triggers
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for concept_notes
DROP TRIGGER IF EXISTS update_concept_notes_updated_at ON concept_notes;
CREATE TRIGGER update_concept_notes_updated_at
    BEFORE UPDATE ON concept_notes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function to calculate cache hit rate
CREATE OR REPLACE FUNCTION get_cache_hit_rate(hours INTEGER DEFAULT 24)
RETURNS FLOAT AS $$
DECLARE
    hit_rate FLOAT;
BEGIN
    SELECT 
        CASE 
            WHEN COUNT(*) = 0 THEN 0
            ELSE (COUNT(*) FILTER (WHERE was_cached = TRUE)::FLOAT / COUNT(*)::FLOAT) * 100
        END INTO hit_rate
    FROM concept_queries
    WHERE created_at > CURRENT_TIMESTAMP - (hours || ' hours')::INTERVAL;
    
    RETURN hit_rate;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Views for Analytics
-- ============================================================================

-- Concept statistics view
CREATE OR REPLACE VIEW concept_statistics AS
SELECT 
    category,
    primary_source,
    status,
    COUNT(*) as concept_count,
    AVG(confidence_score) as avg_confidence,
    MAX(updated_at) as last_updated,
    SUM(access_count) as total_accesses,
    AVG(access_count) as avg_accesses
FROM concept_notes
GROUP BY category, primary_source, status;

-- Query performance view
CREATE OR REPLACE VIEW query_performance AS
SELECT 
    DATE_TRUNC('hour', created_at) as hour,
    COUNT(*) as total_queries,
    COUNT(*) FILTER (WHERE was_cached = TRUE) as cached_queries,
    AVG(total_time_ms) as avg_total_time,
    AVG(retrieval_time_ms) as avg_retrieval_time,
    AVG(generation_time_ms) FILTER (WHERE generation_time_ms IS NOT NULL) as avg_generation_time,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY total_time_ms) as median_total_time,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY total_time_ms) as p95_total_time
FROM concept_queries
WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '7 days'
GROUP BY DATE_TRUNC('hour', created_at)
ORDER BY hour DESC;

-- ============================================================================
-- Initial Data
-- ============================================================================

-- Insert initial system health record
INSERT INTO system_health (
    vector_db_status,
    database_status,
    api_status,
    embedding_service_status,
    checked_at
) VALUES (
    'initializing',
    'healthy',
    'initializing',
    'initializing',
    CURRENT_TIMESTAMP
) ON CONFLICT DO NOTHING;

-- ============================================================================
-- Completion Message
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE '============================================================';
    RAISE NOTICE 'AURELIA DATABASE INITIALIZATION COMPLETE';
    RAISE NOTICE '============================================================';
    RAISE NOTICE 'Tables created:';
    RAISE NOTICE '  ✓ concept_notes (main concept cache)';
    RAISE NOTICE '  ✓ concept_queries (query tracking)';
    RAISE NOTICE '  ✓ vector_index_metadata (vector DB tracking)';
    RAISE NOTICE '  ✓ concept_seed_jobs (Airflow job tracking)';
    RAISE NOTICE '  ✓ system_health (health monitoring)';
    RAISE NOTICE '';
    RAISE NOTICE 'Views created:';
    RAISE NOTICE '  ✓ concept_statistics';
    RAISE NOTICE '  ✓ query_performance';
    RAISE NOTICE '';
    RAISE NOTICE 'Functions created:';
    RAISE NOTICE '  ✓ update_updated_at_column()';
    RAISE NOTICE '  ✓ get_cache_hit_rate(hours)';
    RAISE NOTICE '';
    RAISE NOTICE 'Database is ready for use!';
    RAISE NOTICE '============================================================';
END $$;