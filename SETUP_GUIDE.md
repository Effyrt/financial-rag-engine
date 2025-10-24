# 🚀 Financial RAG Engine - Setup Guide

## Quick Start (5 minutes)

### 1. **Configure Environment**
```bash
# Edit the .env file with your actual API keys
nano .env

# Required: Update these values
OPENAI_API_KEY=sk-your-actual-openai-key-here
DATABASE_URL=sqlite:///./data/financial_rag.db
CHROMA_DB_PATH=./data/chroma_db
```

### 2. **Install Dependencies**
```bash
# Install Python packages
pip install -r requirements.txt

# For development
pip install -r requirements.txt
```

### 3. **Test the Setup**
```bash
# Test everything is working
python start_pipeline.py

# Test with small batch
python test_pipeline.py
```

### 4. **Run the Pipeline**
```bash
# Test with first 5 pages
python run_pipeline.py --pages 5

# Test with first 20 pages  
python run_pipeline.py --pages 20

# Full pipeline (3,462 pages)
python run_pipeline.py --pages all
```

### 5. **Start the API**
```bash
# Start FastAPI backend
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080

# In another terminal, start Streamlit frontend
cd frontend
streamlit run app.py
```

## 🔧 Troubleshooting

### **Common Issues:**

#### **1. "OpenAI API key not found"**
```bash
# Solution: Update .env file
echo "OPENAI_API_KEY=sk-your-actual-key-here" >> .env
```

#### **2. "ChromaDB initialization failed"**
```bash
# Solution: Create directory and check permissions
mkdir -p data/chroma_db
chmod 755 data/chroma_db
```

#### **3. "PDF file not found"**
```bash
# Solution: Ensure fintbx.pdf is in project root
ls -la fintbx.pdf
# If missing, download or copy your PDF file
```

#### **4. "Database connection failed"**
```bash
# Solution: Check database URL in .env
# For SQLite (default):
DATABASE_URL=sqlite:///./data/financial_rag.db

# For PostgreSQL:
DATABASE_URL=postgresql://user:password@localhost:5432/financial_rag
```

### **Performance Issues:**

#### **Slow Processing**
- Reduce batch size: `--pages 10` instead of `--pages 50`
- Check available memory and CPU
- Use cloud processing for large batches

#### **Memory Issues**
- Process smaller page ranges
- Increase system memory
- Use cloud processing

## 📊 Expected Performance

| **Pages** | **Time** | **Memory** | **Cost** |
|-----------|----------|------------|----------|
| 5 pages | 1-2 minutes | 2GB | ~$0.01 |
| 20 pages | 5-10 minutes | 4GB | ~$0.05 |
| 100 pages | 30-60 minutes | 8GB | ~$0.25 |
| 3,462 pages | 2-4 hours | 16GB | ~$8.00 |

## 🎯 Next Steps

1. **Test with small batches first** (5-20 pages)
2. **Verify API keys are working**
3. **Check all components initialize properly**
4. **Scale up gradually** (50 → 100 → 500 pages)
5. **Use cloud processing for full 3,462 pages**

## 🆘 Need Help?

- Check logs in `logs/` directory
- Run `python start_pipeline.py` for diagnostics
- Run `python test_pipeline.py` for component tests
- Check `.env` file configuration
- Verify all dependencies are installed

---

**Your pipeline is now ready to process financial documents and generate concept notes! 🎉**
