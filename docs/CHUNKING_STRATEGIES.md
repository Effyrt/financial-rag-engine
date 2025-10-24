# Chunking Strategies - Comprehensive Guide

## Overview

This document explains the **5 chunking strategies** implemented using LangChain, their use cases, trade-offs, and evaluation metrics.

---

## 🎯 Strategy 1: Recursive Character Text Splitter

### Description
The baseline strategy that splits text recursively using a hierarchy of separators.

### Configuration
```python
chunk_size=1000
chunk_overlap=100
separators=["\n\n", "\n", ". ", ", ", " ", ""]
```

### How It Works
1. Try to split on paragraph breaks (`\n\n`)
2. If chunks too large, split on line breaks (`\n`)
3. If still too large, split on sentences (`. `)
4. Continue down the hierarchy until chunk size is met

### Pros
✅ **Fast**: Simple algorithm, minimal overhead  
✅ **Respects natural boundaries**: Tries to keep paragraphs/sentences intact  
✅ **Predictable**: Consistent chunk sizes  
✅ **General purpose**: Works for most text types  

### Cons
❌ **No semantic awareness**: May split related concepts  
❌ **Ignores document structure**: Doesn't consider headings/sections  
❌ **Code-blind**: Treats code like regular text  

### Best For
- General text documents
- When speed is important
- Baseline for comparison

### Example Output
```json
{
  "chunk_id": "doc_0_a1b2c3d4",
  "text": "Financial derivatives are contracts...",
  "char_count": 987,
  "word_count": 156,
  "strategy": "Recursive-1000-100"
}
```

### Variants Tested
1. **Recursive-500-50**: Smaller chunks, more precise retrieval
2. **Recursive-1000-100**: Balanced (default)
3. **Recursive-1500-200**: Larger chunks, more context

---

## 🧠 Strategy 2: Semantic Chunking

### Description
Splits text based on semantic boundaries (paragraphs, topics) rather than just character count.

### Configuration
```python
chunk_size=1200
chunk_overlap=150
semantic_block_detection=True
```

### How It Works
1. Identify semantic blocks (paragraphs, topic shifts)
2. Keep related content together
3. Only split blocks if they exceed chunk size
4. Use larger overlap to maintain context

### Pros
✅ **Meaning-preserving**: Keeps related concepts together  
✅ **Better retrieval**: Chunks are semantically coherent  
✅ **Context-aware**: Understands topic boundaries  

### Cons
❌ **Variable sizes**: Chunks may vary significantly  
❌ **Slower**: More processing required  
❌ **Requires clear structure**: Works best with well-written text  

### Best For
- Documents with clear paragraph structure
- When retrieval quality > chunk uniformity
- Academic papers, articles

### Example Output
```json
{
  "chunk_id": "doc_0_e5f6g7h8",
  "text": "The Black-Scholes model...",
  "char_count": 1156,
  "semantic_block": true,
  "strategy": "Semantic-1200-150"
}
```

---

## 📚 Strategy 3: Heading-Aware Splitting

### Description
Preserves document hierarchy by splitting on section headings while maintaining context.

### Configuration
```python
chunk_size=1000
chunk_overlap=100
heading_detection=True
```

### How It Works
1. Detect headings (Markdown `#`, numbered `1.`, underlined)
2. Split document into sections
3. Include heading in first chunk of each section
4. Maintain section context in metadata

### Pros
✅ **Structure preservation**: Maintains document hierarchy  
✅ **Context retention**: Each chunk knows its section  
✅ **Better citations**: Can reference specific sections  
✅ **Navigation**: Easier to locate information  

### Cons
❌ **Requires structured docs**: Needs clear headings  
❌ **Variable chunk sizes**: Sections may be very different sizes  
❌ **Heading detection**: May miss non-standard heading formats  

### Best For
- Technical documentation
- Structured reports
- Textbooks, manuals
- Financial Toolbox documentation

### Example Output
```json
{
  "chunk_id": "doc_0_i9j0k1l2",
  "text": "## Option Pricing\n\nThe Black-Scholes model...",
  "section_heading": "Option Pricing",
  "heading_level": 2,
  "is_first_in_section": true,
  "strategy": "HeadingAware-1000-100"
}
```

---

## 💻 Strategy 4: Code-Aware Splitting

### Description
Specialized strategy that handles code blocks differently from regular text.

### Configuration
```python
chunk_size=1000
chunk_overlap=100
code_detection=True
language_detection=True
```

### How It Works
1. Detect code blocks (markdown ` ```lang ` syntax)
2. Use language-specific splitter for code
3. Use regular splitter for text
4. Preserve code block integrity

### Pros
✅ **Code preservation**: Keeps functions/classes intact  
✅ **Syntax-aware**: Respects language structure  
✅ **Language detection**: Identifies programming language  
✅ **Mixed content**: Handles text + code documents  

### Cons
❌ **Code-specific**: Only useful for code-heavy docs  
❌ **Pattern dependency**: Relies on markdown code blocks  
❌ **Complexity**: More processing overhead  

### Best For
- Programming tutorials
- API documentation
- Jupyter notebooks
- Financial Toolbox (has MATLAB code)

### Example Output
```json
{
  "chunk_id": "doc_0_m3n4o5p6",
  "text": "def black_scholes(S, K, T, r, sigma):\n    ...",
  "content_type": "code",
  "language": "python",
  "strategy": "CodeAware-1000-100"
}
```

---

## 🔥 Strategy 5: Hybrid Strategy (RECOMMENDED)

### Description
Combines the best aspects of all strategies for maximum flexibility and quality.

### Configuration
```python
chunk_size=1000
chunk_overlap=100
heading_aware=True
code_aware=True
semantic_aware=True
```

### How It Works
1. **First**: Split by headings (structure preservation)
2. **Then**: Detect code blocks in each section
3. **For code**: Use code-aware splitting
4. **For text**: Use semantic splitting
5. **Finally**: Apply size constraints with overlap

### Pros
✅ **Best of all worlds**: Combines all strategy benefits  
✅ **Flexible**: Adapts to content type  
✅ **High quality**: Best retrieval performance  
✅ **Context-rich**: Maintains structure, semantics, and code integrity  

### Cons
❌ **Most complex**: More processing steps  
❌ **Slower**: Takes longest to process  
❌ **Overkill**: May be unnecessary for simple documents  

### Best For
- **Financial Toolbox** (our use case!)
- Complex documents with mixed content
- When quality > speed
- Production systems

### Example Output
```json
{
  "chunk_id": "doc_0_q7r8s9t0",
  "text": "## Option Pricing\n\nThe Black-Scholes model...",
  "section_heading": "Option Pricing",
  "heading_level": 2,
  "content_type": "text",
  "strategy": "Hybrid-1000-100"
}
```

---

## 📊 Evaluation Metrics

### 1. Chunk Size Distribution
Measures how chunks are distributed across size ranges:
- **Very Small** (<500 chars): May lack context
- **Small** (500-800 chars): Good for precise retrieval
- **Optimal** (800-1200 chars): Best balance
- **Large** (1200-1500 chars): Good for context
- **Very Large** (>1500 chars): May be too broad

### 2. Optimal Percentage
Percentage of chunks in the "optimal" range (800-1200 chars).  
**Higher is better**.

### 3. Size Variance
Measures consistency of chunk sizes.  
**Lower is better** for predictable behavior.

### 4. Retrieval Quality (Theoretical)
Based on:
- Semantic coherence
- Context preservation
- Structure awareness
- Code integrity

---

## 🎯 Recommendations by Use Case

### Financial Toolbox (Our Project)
**Recommended**: `hybrid_1000_100`

**Why?**
- Has structured sections (headings)
- Contains MATLAB code snippets
- Needs semantic coherence for concepts
- Requires accurate citations

**Metrics** (Expected):
- Optimal percentage: 75-85%
- Avg chunk size: 950-1050 chars
- Low variance: <50,000

---

### General Technical Documentation
**Recommended**: `heading_aware_1000_100`

**Why?**
- Clear section structure
- Needs context from headings
- Less code than Financial Toolbox

---

### Code-Heavy Tutorials
**Recommended**: `code_aware_1000_100`

**Why?**
- Preserves code block integrity
- Language-specific splitting
- Maintains function/class boundaries

---

### Academic Papers
**Recommended**: `semantic_1200_150`

**Why?**
- Semantic coherence critical
- Larger chunks for context
- More overlap for continuity

---

## 🧪 Running the Evaluation

### Test All Strategies
```bash
cd /Users/HemanthRayudu/Profession/Assignments/DAMG/financial-rag-engine
source venv/bin/activate

python pipeline/evaluate_chunking.py \
  --parsed-file data/processed/parsed_10p.json \
  --output-dir data/processed/chunking_evaluation
```

### List Available Strategies
```bash
python pipeline/evaluate_chunking.py --list-strategies
```

### Output
The evaluation produces:
1. **Chunks for each strategy**: `chunks_{strategy_name}.json`
2. **Evaluation report**: `evaluation_report.json`
3. **Console comparison**: Side-by-side metrics
4. **Recommendations**: Best strategy for your data

---

## 📈 Example Evaluation Results

```
📊 STRATEGY COMPARISON

Strategy                       Chunks     Avg Size     Optimal %    Variance    
--------------------------------------------------------------------------------
recursive_1000_100             45         987          68.9         12,345      
recursive_1500_200             32         1,456        56.3         28,901      
recursive_500_50               78         512          34.6         5,678       
semantic_1200_150              38         1,123        78.9         15,234      
heading_aware_1000_100         42         1,034        72.4         11,890      
code_aware_1000_100            47         965          71.3         13,456      
hybrid_1000_100                44         1,012        81.8         9,876       

================================================================================
🏆 RECOMMENDED STRATEGY: hybrid_1000_100
   Highest optimal chunk percentage: 81.8%
================================================================================
```

---

## 🔧 Customizing Strategies

### Create Custom Configuration
```python
from pipeline.chunker_strategies import ChunkingConfig, HybridStrategy

custom_config = ChunkingConfig(
    name="Custom-2000-300",
    chunk_size=2000,
    chunk_overlap=300,
    description="Extra large chunks for maximum context"
)

strategy = HybridStrategy(custom_config)
chunks = strategy.chunk(text, metadata)
```

### Adjust Parameters
- **Increase chunk_size**: More context, fewer chunks
- **Increase chunk_overlap**: Better continuity, more redundancy
- **Decrease chunk_size**: More precise retrieval, more chunks
- **Decrease chunk_overlap**: Less redundancy, faster processing

---

## 🎓 Key Takeaways

1. **No one-size-fits-all**: Different documents need different strategies
2. **Hybrid is best for mixed content**: Our Financial Toolbox needs it
3. **Evaluate on your data**: Run the evaluation script
4. **Balance size and overlap**: 1000/100 is a good starting point
5. **Consider your use case**: Retrieval precision vs. context
6. **Monitor metrics**: Optimal percentage and variance are key

---

## 📚 References

- [LangChain Text Splitters](https://python.langchain.com/docs/modules/data_connection/document_transformers/)
- [Chunking Strategies for RAG](https://www.pinecone.io/learn/chunking-strategies/)
- [Recursive Character Text Splitter](https://python.langchain.com/docs/modules/data_connection/document_transformers/recursive_text_splitter)

---

## ✅ Next Steps

1. ✅ Run evaluation on 10-page sample
2. ✅ Review metrics and recommendations
3. ✅ Select best strategy (likely `hybrid_1000_100`)
4. ✅ Integrate into main pipeline
5. ✅ Test with full document
6. ✅ Monitor retrieval quality in production

