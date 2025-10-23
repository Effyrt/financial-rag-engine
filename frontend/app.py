"""
Streamlit Frontend for Financial RAG Engine.

Provides user interface for:
- Querying financial concepts
- Viewing concept notes
- Browsing cached concepts
"""

import streamlit as st
import requests
import os
from typing import Optional, Dict, Any
import json

# Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8080")

# Page config
st.set_page_config(
    page_title="Financial RAG Engine",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .concept-card {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .formula-box {
        background-color: #ffffff;
        padding: 1rem;
        border-left: 4px solid #1f77b4;
        font-family: 'Courier New', monospace;
        margin: 1rem 0;
    }
    .metadata-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        margin: 0.25rem;
        background-color: #e1e4e8;
        border-radius: 1rem;
        font-size: 0.875rem;
    }
</style>
""", unsafe_allow_html=True)


def query_concept(concept: str, top_k: int = 5, force_regenerate: bool = False) -> Optional[Dict[str, Any]]:
    """Query the backend API for a concept."""
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/v1/query",
            json={
                "concept": concept,
                "top_k": top_k,
                "force_regenerate": force_regenerate
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error querying backend: {e}")
        return None


def list_concepts(limit: int = 50) -> Optional[list]:
    """List all cached concepts."""
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/v1/concepts",
            params={"limit": limit},
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error listing concepts: {e}")
        return None


def get_stats() -> Optional[Dict[str, Any]]:
    """Get system statistics."""
    try:
        response = requests.get(f"{BACKEND_URL}/api/v1/stats", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return None


def display_concept_note(result: Dict[str, Any]):
    """Display a concept note in a formatted card."""
    concept = result["concept"]
    source = result["source"]
    retrieval_time = result["retrieval_time_ms"]
    
    # Header with badges
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.markdown(f"### 📚 {concept['title']}")
    with col2:
        if source == "cache":
            st.markdown("🔖 **Cached**")
        elif source == "rag":
            st.markdown("🤖 **Generated**")
        else:
            st.markdown("📖 **Wikipedia**")
    with col3:
        st.markdown(f"⏱️ {retrieval_time:.0f}ms")
    
    st.markdown("---")
    
    # Definition
    st.markdown("#### 📖 Definition")
    st.markdown(f"<div class='concept-card'>{concept['definition']}</div>", unsafe_allow_html=True)
    
    # Formula (if exists)
    if concept.get("formula"):
        st.markdown("#### 🔢 Formula")
        st.markdown(f"<div class='formula-box'>{concept['formula']}</div>", unsafe_allow_html=True)
        # Try to render LaTeX
        try:
            st.latex(concept['formula'])
        except:
            pass
    
    # Example (if exists)
    if concept.get("example"):
        st.markdown("#### 💡 Example")
        st.info(concept['example'])
    
    # Use Cases
    if concept.get("use_cases") and len(concept['use_cases']) > 0:
        st.markdown("#### 🎯 Use Cases")
        for use_case in concept['use_cases']:
            st.markdown(f"- {use_case}")
    
    # References
    if concept.get("references") and len(concept['references']) > 0:
        st.markdown("#### 📚 References")
        for ref in concept['references']:
            st.markdown(f"- {ref}")
    
    # Metadata
    if concept.get("metadata"):
        with st.expander("🔍 Metadata"):
            st.json(concept['metadata'])


def main():
    """Main application."""
    
    # Header
    st.markdown("<h1 class='main-header'>📚 Financial RAG Engine</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #666;'>Intelligent Financial Concept Retrieval</p>", unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown("### ⚙️ Settings")
        
        # Backend status
        st.markdown("#### 🔌 Backend Status")
        try:
            health = requests.get(f"{BACKEND_URL}/health", timeout=5).json()
            st.success("✅ Connected")
            
            # Show stats
            stats = get_stats()
            if stats and "pinecone" in stats:
                st.metric("Total Vectors", stats["pinecone"]["total_vectors"])
                st.metric("Namespaces", len(stats["pinecone"]["namespaces"]))
        except:
            st.error("❌ Backend Offline")
        
        st.markdown("---")
        
        # Query settings
        st.markdown("#### 🎛️ Query Settings")
        top_k = st.slider("Top K Results", 1, 20, 5)
        force_regenerate = st.checkbox("Force Regenerate", value=False)
        
        st.markdown("---")
        
        # Browse concepts
        st.markdown("#### 📑 Browse Concepts")
        if st.button("Load Cached Concepts"):
            st.session_state["show_browse"] = True
    
    # Main content
    tab1, tab2 = st.tabs(["🔍 Search", "📑 Browse"])
    
    with tab1:
        # Search interface
        st.markdown("### 🔍 Search for a Financial Concept")
        
        col1, col2 = st.columns([4, 1])
        with col1:
            concept_query = st.text_input(
                "Enter a financial concept",
                placeholder="e.g., Black-Scholes Model, Monte Carlo Simulation, Value at Risk...",
                label_visibility="collapsed"
            )
        with col2:
            search_button = st.button("🔍 Search", use_container_width=True)
        
        # Example queries
        st.markdown("**💡 Try these:**")
        examples = ["Black-Scholes Model", "Monte Carlo Simulation", "Value at Risk", "Option Pricing"]
        cols = st.columns(len(examples))
        for i, example in enumerate(examples):
            if cols[i].button(example, key=f"example_{i}"):
                concept_query = example
                search_button = True
        
        # Process search
        if search_button and concept_query:
            with st.spinner(f"🔍 Searching for '{concept_query}'..."):
                result = query_concept(concept_query, top_k=top_k, force_regenerate=force_regenerate)
                
                if result:
                    st.success("✅ Concept found!")
                    display_concept_note(result)
                    
                    # Add to history
                    if "history" not in st.session_state:
                        st.session_state["history"] = []
                    st.session_state["history"].insert(0, concept_query)
                    st.session_state["history"] = st.session_state["history"][:10]  # Keep last 10
        
        # Search history
        if "history" in st.session_state and len(st.session_state["history"]) > 0:
            st.markdown("---")
            st.markdown("### 📜 Recent Searches")
            for i, query in enumerate(st.session_state["history"][:5]):
                if st.button(f"🔄 {query}", key=f"history_{i}"):
                    result = query_concept(query, top_k=top_k)
                    if result:
                        display_concept_note(result)
    
    with tab2:
        # Browse cached concepts
        st.markdown("### 📑 Cached Concepts")
        
        if st.button("🔄 Refresh List"):
            st.session_state["cached_concepts"] = None
        
        if "cached_concepts" not in st.session_state:
            with st.spinner("Loading concepts..."):
                st.session_state["cached_concepts"] = list_concepts(limit=100)
        
        concepts = st.session_state.get("cached_concepts", [])
        
        if concepts:
            st.info(f"📊 {len(concepts)} concepts in cache")
            
            # Display as cards
            for concept in concepts:
                with st.expander(f"📚 {concept['title']}"):
                    st.markdown(f"**Definition:** {concept['definition']}")
                    if concept.get("formula"):
                        st.markdown(f"**Formula:** `{concept['formula']}`")
                    if concept.get("use_cases"):
                        st.markdown(f"**Use Cases:** {', '.join(concept['use_cases'][:3])}")
                    st.markdown(f"**Source:** {concept['source']}")
        else:
            st.info("No cached concepts yet. Search for concepts to populate the cache!")


if __name__ == "__main__":
    main()

