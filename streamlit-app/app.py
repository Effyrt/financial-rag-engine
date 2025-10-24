import streamlit as st
from api_client import MockAPIClient
import time

# Page configuration
st.set_page_config(
    page_title="Financial Concepts RAG System",
    page_icon="📊",
    layout="wide"
)

# Initialize session state
if 'search_history' not in st.session_state:
    st.session_state.search_history = []

# Initialize API Client (use mock during development)
@st.cache_resource
def get_api_client():
    # Switch use_real_api=True to use real API
    return MockAPIClient(use_real_api=False)

client = get_api_client()

# ===== Title and Description =====
st.title("📊 Financial Concepts RAG System")
st.markdown("""
This is a RAG (Retrieval-Augmented Generation) based financial concept query system.
- ✅ Retrieves relevant content from textbook (fintbx.pdf)
- 🔄 Automatically generates structured notes
- 💾 Intelligent caching for faster queries
- 📚 Wikipedia as fallback data source
""")

st.divider()

# ===== Main Query Interface =====
col1, col2 = st.columns([3, 1])

with col1:
    concept_input = st.text_input(
        "🔍 Enter Financial Concept",
        placeholder="e.g., Credit Default Swap, Black-Scholes Model...",
        help="Enter the name of the financial concept you want to query"
    )

with col2:
    st.write("")  # Spacing alignment
    st.write("")
    search_button = st.button("🚀 Search", type="primary", use_container_width=True)

# ===== Execute Query =====
if search_button and concept_input:
    
    with st.spinner("🔄 Querying concept note..."):
        try:
            # Record start time
            start_time = time.time()
            
            # Call API
            result = client.query_concept(concept_input)
            
            # Calculate total time
            total_time = time.time() - start_time
            
            # Add to search history
            st.session_state.search_history.insert(0, {
                'concept': concept_input,
                'timestamp': result['timestamp'],
                'source': result['source'],
                'cached': result['cached']
            })
            
            # ===== Display Results =====
            st.success(f"✅ Query completed! Time elapsed: {total_time:.2f}s")
            
            # Status indicators
            col_status1, col_status2, col_status3 = st.columns(3)
            
            with col_status1:
                if result['cached']:
                    st.info("💾 **Cache Hit**", icon="✅")
                else:
                    st.warning("🔄 **Newly Generated**", icon="🆕")
            
            with col_status2:
                if result['source'] == 'fintbx.pdf':
                    st.success("📖 **Source: Textbook**", icon="📚")
                else:
                    st.error("🌐 **Source: Wikipedia**", icon="⚠️")
            
            with col_status3:
                gen_time = result.get('generation_time', 0)
                st.metric("Generation Time", f"{gen_time:.2f}s")
            
            # Wikipedia warning
            if result['source'] == 'wikipedia':
                st.warning("""
                ⚠️ **Notice**: This content is from Wikipedia, not from the textbook.
                Relevant information was not found in the textbook, so Wikipedia was automatically used as a fallback source.
                """, icon="🌐")
            
            st.divider()
            
            # ===== Concept Note Content =====
            st.header(f"📝 {result['concept']}")
            
            # Definition
            st.subheader("📖 Definition")
            st.write(result['definition'])
            
            # Key Points
            st.subheader("🎯 Key Points")
            for i, point in enumerate(result['key_points'], 1):
                st.markdown(f"{i}. {point}")
            
            # Examples
            st.subheader("💡 Examples")
            for i, example in enumerate(result['examples'], 1):
                with st.expander(f"Example {i}"):
                    st.write(example)
            
            # References
            st.subheader("📚 References")
            if result['source'] == 'fintbx.pdf':
                st.markdown("**Textbook Chapter Citations:**")
                for ref in result['references']:
                    st.markdown(f"- {ref}")
            else:
                st.markdown("**Wikipedia Links:**")
                for ref in result['references']:
                    st.markdown(f"- {ref}")
            
        except Exception as e:
            st.error(f"❌ Query failed: {str(e)}")

elif search_button and not concept_input:
    st.warning("⚠️ Please enter a concept to query")

# ===== Sidebar: Search History =====
with st.sidebar:
    st.header("📜 Search History")
    
    if st.session_state.search_history:
        for i, item in enumerate(st.session_state.search_history[:10]):
            with st.expander(f"{item['concept']}", expanded=(i==0)):
                st.write(f"**Source**: {item['source']}")
                st.write(f"**Cached**: {'Yes' if item['cached'] else 'No'}")
                st.caption(f"Query Time: {item['timestamp']}")
        
        if st.button("🗑️ Clear History"):
            st.session_state.search_history = []
            st.rerun()
    else:
        st.info("No search records yet")
    
    st.divider()
    
    # System Information
    st.subheader("⚙️ System Info")
    st.caption("API Mode: Mock (Development)")
    st.caption("Vector DB: Pending Connection")
    st.caption("Cache DB: Pending Connection")

# ===== Footer =====
st.divider()
st.caption("Financial Concepts RAG System | Lab 4 Implementation")