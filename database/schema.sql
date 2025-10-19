-- Financial RAG Engine Database Schema

CREATE TABLE IF NOT EXISTS concept_notes (
    concept_id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL UNIQUE,
    definition TEXT,
    formula TEXT,
    example TEXT,
    use_cases JSONB,
    references JSONB,
    source VARCHAR(50) DEFAULT 'PDF',  -- 'PDF' or 'Wikipedia'
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_title ON concept_notes(title);
CREATE INDEX idx_source ON concept_notes(source);
CREATE INDEX idx_created_at ON concept_notes(created_at);

-- Update timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_concept_notes_updated_at 
    BEFORE UPDATE ON concept_notes 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Sample concepts list
COMMENT ON TABLE concept_notes IS 'Stores generated financial concept notes with structured format';

