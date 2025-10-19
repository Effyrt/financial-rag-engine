# Raw Data Directory

This directory contains raw input files for the Financial RAG Engine.

## Required Files

### fintbx.pdf
**Financial Toolbox User's Guide**

- **Source:** MATLAB Financial Toolbox documentation
- **Purpose:** Primary knowledge source for RAG system
- **Size:** ~50 MB
- **Status:** Not included in Git (too large)

**How to obtain:**
1. Download from MATLAB documentation site
2. Or request from course instructor
3. Place in this directory: `data/raw/fintbx.pdf`

**Verification:**
```bash
# Check if file exists
ls -lh data/raw/fintbx.pdf

# Should show approximately 50 MB file size
```

## Note

PDF files are excluded from Git via `.gitignore` to keep the repository size manageable.
Each team member should obtain `fintbx.pdf` separately and place it in this directory.

