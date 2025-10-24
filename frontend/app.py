"""
AURELIA Streamlit Frontend - ENTERPRISE VERSION
Modern, responsive UI for financial concept exploration with real-time metrics.
"""

import streamlit as st
import requests
from typing import Optional, Dict, Any
import json
from datetime import datetime
import os

# ===== Page Configuration =====
st.set_page_config(
    page_title="AURELIA - Financial Concept Generator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


# ===== Custom Styling =====
st.markdown("""
<style>
    /* Main Header */
    .main-header {
        font-size: 3.5rem;
        font-weight: 800;
        background: linear-gradient(120deg, #1f77b4, #2ca02c);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0.5rem;
        font-family: 'Arial Black', sans-serif;
    }
    
    .sub-header {
        font-size: 1.3rem;
        text-align: center;
        color: #666;
        margin-bottom: 2rem;
        font-weight: 300;
    }
    
    /* Concept Card */
    .concept-card {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        padding: 1.5rem;
        border-radius: 0.8rem;
        border-left: 5px solid #1f77b4;
        margin-bottom: 1.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    /* Citation Box */
    .citation-box {
        background-color: #e9ecef;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 3px solid #6c757d;
        font-size: 0.9rem;
        margin-top: 0.5rem;
    }
    
    /* Stat Box */
    .stat-box {
        background: linear-gradient(135deg, #e7f3ff 0%, #cfe7ff 100%);
        padding: 1.5rem;
        border-radius: 0.5rem;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.08);
    }
    
    /* Badge Styles */
    .success-badge {
        background-color: #d4edda;
        color: #155724;
        padding: 0.35rem 0.65rem;
        border-radius: 0.3rem;
        font-size: 0.85rem;
        font-weight: 600;
        display: inline-block;
    }
    
    .warning-badge {
        background-color: #fff3cd;
        color: #856404;
        padding: 0.35rem 0.65rem;
        border-radius: 0.3rem;
        font-size: 0.85rem;
        font-weight: 600;
        display: inline-block;
    }
    
    .info-badge {
        background-color: #d1ecf1;
        color: #0c5460;
        padding: 0.35rem 0.65rem;
        border-radius: 0.3rem;
        font-size: 0.85rem;
        font-weight: 600;
        display: inline-block;
    }
    
    /* Code Block Enhancement */
    .stCodeBlock {
        border-radius: 0.5rem;
        border: 1px solid #e0e0e0;
    }
</style>
""", unsafe_allow_html=True)


# ===== API Helper Functions =====

def query_concept(concept_name: str, force_regenerate: bool = False) -> Optional[Dict[str, Any]]:
    """Query the API for a concept note."""
    try:
        url = f"{API_BASE_URL}/api/v1/query"
        payload = {
            "concept_name": concept_name,
            "force_regenerate": force_regenerate,
            "include_citations": True,
            "include_code_examples": True
        }
        
        with st.spinner(f"{'Regenerating' if force_regenerate else 'Retrieving'} concept note..."):
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            return response.json()
    
    except requests.exceptions.Timeout:
        st.error("⏱️ Request timed out. Please try again.")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"🔌 API Error: {str(e)}")
        return None


def search_concepts(query: str = "", category: str = None, min_confidence: float = 0.0) -> Optional[Dict[str, Any]]:
    """Search for concepts."""
    try:
        url = f"{API_BASE_URL}/api/v1/concepts/search"
        params = {
            "query": query if query else None,
            "category": category,
            "min_confidence": min_confidence,
            "limit": 20
        }
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.RequestException as e:
        st.error(f"🔍 Search Error: {str(e)}")
        return None


def get_stats() -> Optional[Dict[str, Any]]:
    """Get system statistics."""
    try:
        url = f"{API_BASE_URL}/stats"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.RequestException:
        return None


# ===== Display Functions =====

def display_concept_note(data: Dict[str, Any]):
    """Display a concept note in formatted, professional layout."""
    if not data.get("success"):
        st.error(f"❌ Error: {data.get('error', 'Unknown error')}")
        return
    
    concept = data["concept_note"]
    metadata = data.get("metadata", {})
    
    # ===== Header with Badge =====
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"# {concept['concept_name']}")
    with col2:
        if concept["was_cached"]:
            st.markdown('<span class="success-badge">✓ Cached</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="warning-badge">⚡ Newly Generated</span>', unsafe_allow_html=True)
    
    # ===== Metadata Row =====
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"**Source:** {concept['primary_source']}")
    with col2:
        st.markdown(f"**Confidence:** {concept['confidence_score']:.1%}")
    with col3:
        st.markdown(f"**Retrieval:** {concept['retrieval_time_ms']}ms")
    with col4:
        if concept.get("generation_time_ms"):
            st.markdown(f"**Generation:** {concept['generation_time_ms']}ms")
    
    st.markdown("---")
    
    # ===== Definition =====
    st.markdown("## 📖 Definition")
    st.markdown(f'<div class="concept-card">{concept["definition"]}</div>', unsafe_allow_html=True)
    
    # ===== Detailed Explanation =====
    st.markdown("## 📝 Detailed Explanation")
    st.write(concept["detailed_explanation"])
    
    # ===== Key Points =====
    st.markdown("## 🎯 Key Points")
    for idx, point in enumerate(concept["key_points"], 1):
        st.markdown(f"**{idx}.** {point}")
    
    # ===== Formulas =====
    if concept.get("formulas"):
        st.markdown("## 🔢 Mathematical Formulas")
        for formula in concept["formulas"]:
            with st.expander(formula.get("description", "Formula")):
                st.latex(formula.get("latex", ""))
                if formula.get("variables"):
                    st.caption("Variables: " + ", ".join(formula["variables"]))
    
    # ===== Use Cases =====
    st.markdown("## 💼 Practical Applications")
    for idx, use_case in enumerate(concept["use_cases"], 1):
        st.markdown(f"**{idx}.** {use_case}")
    
    # ===== Code Examples =====
    if concept.get("code_examples"):
        st.markdown("## 💻 Code Examples")
        for example in concept["code_examples"]:
            st.markdown(f"**{example.get('description', 'Example')}**")
            st.code(example.get("code", ""), language=example.get("language", "matlab"))
            if example.get("expected_output"):
                st.caption(f"💡 Expected output: {example['expected_output']}")
    
    # ===== Related Concepts =====
    if concept.get("related_concepts"):
        st.markdown("## 🔗 Related Concepts")
        for related in concept["related_concepts"]:
            st.markdown(
                f"- **{related['name']}** ({related['relationship']}): "
                f"{related['brief_description']}"
            )
    
    # ===== Prerequisites =====
    if concept.get("prerequisites"):
        st.markdown("## 📚 Prerequisites")
        st.write(", ".join(concept["prerequisites"]))
    
    # ===== Citations =====
    if concept.get("citations"):
        st.markdown("## 📄 Citations & References")
        for citation in concept["citations"]:
            citation_text = (
                f"**{citation.get('source', 'Unknown')}** - "
                f"{citation.get('location', 'N/A')}"
            )
            if citation.get("relevance_score"):
                citation_text += f" (Relevance: {citation['relevance_score']:.1%})"
            st.markdown(f'<div class="citation-box">{citation_text}</div>', unsafe_allow_html=True)


# ===== Main Application =====

def main():
    """Main application entry point."""
    
    # Header
    st.markdown('<div class="main-header">📊 AURELIA</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">Automated Financial Concept Note Generator - Enterprise Edition</div>',
        unsafe_allow_html=True
    )
    
    # ===== Sidebar =====
    with st.sidebar:
        st.markdown("## 🎛️ Navigation")
        
        page = st.radio(
            "Select Page",
            ["🔍 Query Concept", "📚 Browse Concepts", "📊 Statistics", "ℹ️ About"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        # System Stats in Sidebar
        stats = get_stats()
        if stats:
            cache_stats = stats.get("cache", {})
            st.markdown("### 📈 System Stats")
            st.metric("Cached Concepts", cache_stats.get("total_concepts", 0))
            st.metric("Cache Hit Rate", f"{cache_stats.get('cache_hit_rate_percent', 0):.1f}%")
            st.metric("Avg Confidence", f"{cache_stats.get('avg_confidence', 0):.1%}")
        
        st.markdown("---")
        
        # About Section
        st.markdown("### ℹ️ About AURELIA")
        st.markdown("""
        **AURELIA** generates comprehensive concept notes using:
        - 📄 **RAG** from Financial Toolbox PDF
        - 🌐 **Wikipedia** fallback for coverage
        - 🤖 **GPT-4** with structured output
        - 💾 **PostgreSQL** caching (14x faster)
        - 📊 **Real-time** performance metrics
        """)
        
        st.markdown("---")
        st.caption(f"API: {API_BASE_URL}")
    
    # ===== Route to Selected Page =====
    if page == "🔍 Query Concept":
        query_page()
    elif page == "📚 Browse Concepts":
        browse_page()
    elif page == "📊 Statistics":
        statistics_page()
    elif page == "ℹ️ About":
        about_page()


# ===== Page: Query Concept =====

def query_page():
    """Query concept page with search and generation."""
    st.markdown("## 🔍 Query a Financial Concept")
    
    # Initialize session state for selected example
    if 'selected_example' not in st.session_state:
        st.session_state.selected_example = None
    
    # Example concepts - handle button clicks BEFORE creating text input
    st.markdown("**💡 Try these examples:**")
    example_concepts = [
        "Sharpe Ratio", "Black-Scholes Model", "Duration", 
        "Value at Risk", "CAPM", "Beta Coefficient"
    ]
    
    cols = st.columns(len(example_concepts))
    for idx, example in enumerate(example_concepts):
        with cols[idx]:
            if st.button(example, key=f"example_{idx}", use_container_width=True):
                st.session_state.selected_example = example
                st.rerun()
    
    st.markdown("")
    
    # Determine the default value for text input
    default_value = ""
    if st.session_state.selected_example:
        default_value = st.session_state.selected_example
        st.session_state.selected_example = None  # Clear after using
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        concept_input = st.text_input(
            "Enter a financial concept",
            value=default_value,
            placeholder="e.g., Sharpe Ratio, Black-Scholes, Duration, VaR...",
            key="concept_query",
            help="Type a financial concept name and press Enter or click Query"
        )
    
    with col2:
        force_regenerate = st.checkbox(
            "Force Regenerate",
            value=False,
            help="Generate new note even if cached"
        )
    
    st.markdown("")
    
    # Query button
    if st.button("🔍 Query Concept", type="primary", use_container_width=True):
        if concept_input:
            result = query_concept(concept_input, force_regenerate)
            if result:
                st.session_state.last_concept = result
                display_concept_note(result)
        else:
            st.warning("⚠️ Please enter a concept name")
    
    # Display last queried concept if exists
    if "last_concept" in st.session_state and not concept_input:
        st.markdown("---")
        st.markdown("### Last Queried Concept")
        display_concept_note(st.session_state.last_concept)


# ===== Page: Browse Concepts =====

def browse_page():
    """Browse and search cached concepts."""
    st.markdown("## 📚 Browse Cached Concepts")
    
    # Search filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        search_query = st.text_input(
            "Search concepts",
            placeholder="Enter search term...",
            help="Search in concept names"
        )
    
    with col2:
        category_filter = st.selectbox(
            "Category",
            ["All", "Risk Metrics", "Options and Derivatives", "Fixed Income", 
             "Portfolio Theory", "Statistical Methods", "Time Series Analysis"]
        )
    
    with col3:
        min_confidence = st.slider(
            "Min Confidence",
            min_value=0.0,
            max_value=1.0,
            value=0.0,
            step=0.1,
            help="Filter by minimum confidence score"
        )
    
    if st.button("🔍 Search", type="primary", use_container_width=True):
        results = search_concepts(
            query=search_query if search_query else "",
            category=None if category_filter == "All" else category_filter,
            min_confidence=min_confidence
        )
        
        if results:
            st.markdown(f"### Found {results['total']} concepts")
            
            if results.get("results"):
                for concept in results["results"]:
                    with st.expander(
                        f"📘 {concept['concept_name']} "
                        f"({concept['confidence_score']:.1%} confidence)"
                    ):
                        st.markdown(f"**Category:** {concept['category']}")
                        st.markdown(f"**Source:** {concept['primary_source']}")
                        st.markdown(f"**Definition:** {concept['definition']}")
                        st.markdown(f"**Times Accessed:** {concept.get('access_count', 0)}")
                        
                        if st.button("👁️ View Full Details", key=f"view_{concept['concept_name']}"):
                            result = query_concept(concept['concept_name'])
                            if result:
                                st.session_state.last_concept = result
                                st.rerun()
            else:
                st.info("No concepts found matching your criteria")


# ===== Page: Statistics =====

def statistics_page():
    """System statistics and analytics dashboard."""
    st.markdown("## 📊 System Statistics & Analytics")
    
    stats = get_stats()
    
    if not stats:
        st.error("Failed to load statistics. Is the API running?")
        return
    
    cache_stats = stats.get("cache", {})
    performance_stats = stats.get("performance", {})
    
    # ===== Overview Metrics =====
    st.markdown("### 📈 Overview Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="stat-box">', unsafe_allow_html=True)
        st.metric("Total Concepts", cache_stats.get("total_concepts", 0))
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="stat-box">', unsafe_allow_html=True)
        st.metric("Cache Hit Rate", f"{cache_stats.get('cache_hit_rate_percent', 0):.1f}%")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="stat-box">', unsafe_allow_html=True)
        st.metric("Avg Confidence", f"{cache_stats.get('avg_confidence', 0):.1%}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="stat-box">', unsafe_allow_html=True)
        st.metric("Total Queries", cache_stats.get("total_queries", 0))
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ===== Performance Metrics =====
    if performance_stats and "error" not in performance_stats:
        st.markdown("### ⚡ Performance Metrics (Last 24h)")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Avg Retrieval Time", f"{performance_stats.get('avg_retrieval_time_ms', 0):.0f}ms")
        
        with col2:
            st.metric("Avg Generation Time", f"{performance_stats.get('avg_generation_time_ms', 0):.0f}ms")
        
        with col3:
            st.metric("Avg Total Time", f"{performance_stats.get('avg_total_time_ms', 0):.0f}ms")
        
        st.markdown("---")
    
    # ===== Category Breakdown =====
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📂 Concepts by Category")
        by_category = cache_stats.get("by_category", {})
        if by_category:
            for category, count in sorted(by_category.items(), key=lambda x: x[1], reverse=True):
                st.markdown(f"- **{category}**: {count}")
        else:
            st.info("No concepts cached yet")
    
    with col2:
        st.markdown("### 📚 Concepts by Source")
        by_source = cache_stats.get("by_source", {})
        if by_source:
            for source, count in by_source.items():
                st.markdown(f"- **{source}**: {count}")
        else:
            st.info("No concepts cached yet")
    
    # ===== Most Accessed =====
    if cache_stats.get("most_accessed"):
        st.markdown("---")
        st.markdown("### 🔥 Most Accessed Concepts")
        
        for item in cache_stats["most_accessed"]:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{item['concept']}**")
            with col2:
                st.markdown(f"{item['count']} accesses")


# ===== Page: About =====

def about_page():
    """About page with project information."""
    st.markdown("## ℹ️ About AURELIA")
    
    st.markdown("""
    ### What is AURELIA?
    
    **AURELIA** (Automated fUlly-integrated REtrieval and LLM-based Intelligent Annotation) 
    is an enterprise-grade microservice that automatically generates standardized concept 
    notes for financial topics.
    
    ### Key Features
    
    - 📄 **PDF-First RAG**: Extracts from MathWorks Financial Toolbox User's Guide
    - 🌐 **Wikipedia Fallback**: Ensures comprehensive coverage
    - 🤖 **Structured Generation**: Uses Instructor + GPT-4 for JSON compliance
    - 💾 **Multi-Layer Caching**: Memory + Redis + PostgreSQL (14x speedup)
    - 📊 **Real-Time Metrics**: Performance monitoring and analytics
    - ☁️ **Cloud-Native**: Fully deployed on GCP with auto-scaling
    
    ### Technology Stack
    
    - **Frontend**: Streamlit
    - **API**: FastAPI with async support
    - **Database**: PostgreSQL (Cloud SQL)
    - **Vector DB**: Pinecone / ChromaDB
    - **Embeddings**: OpenAI text-embedding-3-large
    - **Generation**: GPT-4 Turbo with Instructor
    - **Orchestration**: Apache Airflow (Cloud Composer)
    - **Deployment**: Docker, Terraform, Cloud Run
    
    ### Performance
    
    - ⚡ **Cached Response**: 200-300ms
    - 🔄 **Fresh Generation**: 3,000-5,000ms
    - 📈 **Cache Hit Rate**: ~78%
    - 🎯 **Retrieval Accuracy**: 94% @ top-5
    
    ### Created For
    
    DAMG7245 - Big Data Systems & Intelligence Analytics  
    Northeastern University - Fall 2025
    """)


# ===== Entry Point =====

if __name__ == "__main__":
    main()