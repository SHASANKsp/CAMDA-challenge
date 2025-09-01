import streamlit as st
import os
from langchain_ollama import OllamaLLM
import database
import processor
from typing import Dict, Any

# Page configuration
st.set_page_config(
    page_title="Medical Complications Assistant",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Available LLM models
AVAILABLE_MODELS = {
    "llama3.1:latest": "Meta Llama 3.1 (Latest)",
    "deepseek-r1:8b": "DeepSeek R1 (8B)",
    "phi3:latest": "Microsoft Phi-3 (Latest)"
}

# Initialize session state
if 'processor' not in st.session_state:
    st.session_state.processor = None
if 'graph' not in st.session_state:
    st.session_state.graph = None
if 'llm' not in st.session_state:
    st.session_state.llm = None
if 'selected_model' not in st.session_state:
    st.session_state.selected_model = "llama3.1:latest"

# Initialize connections
def initialize_connections(model_name: str):
    """Initialize database and LLM connections with selected model"""
    try:
        if st.session_state.graph is None:
            st.session_state.graph = database.initialize_neo4j_connection()
        
        # Only reinitialize LLM if model changed or not initialized
        if (st.session_state.llm is None or 
            st.session_state.selected_model != model_name):
            
            OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            st.session_state.llm = OllamaLLM(
                base_url=OLLAMA_BASE_URL, 
                model=model_name
            )
            st.session_state.selected_model = model_name
            st.toast(f"Switched to {AVAILABLE_MODELS[model_name]} model", icon="🤖")
        
        if st.session_state.processor is None:
            st.session_state.processor = processor.MedicalQueryProcessor(
                st.session_state.graph, st.session_state.llm
            )
            
        return True
    except Exception as e:
        st.error(f"Failed to initialize connections: {e}")
        return False

# UI Components
def render_sidebar():
    """Render the sidebar with information, model selection, and examples"""
    with st.sidebar:
        st.title("Medical Complications Assistant")
        
        # Model selection
        st.subheader("AI Model Selection")
        selected_model = st.selectbox(
            "Choose LLM Model:",
            options=list(AVAILABLE_MODELS.keys()),
            format_func=lambda x: AVAILABLE_MODELS[x],
            index=list(AVAILABLE_MODELS.keys()).index(st.session_state.selected_model)
        )
        
        # Update model if changed
        if selected_model != st.session_state.selected_model:
            initialize_connections(selected_model)
        
        st.markdown(f"**Current Model:** {AVAILABLE_MODELS[st.session_state.selected_model]}")
        
        st.markdown("""
        **How to use:**
        1. Select your preferred AI model
        2. Enter your query in natural language
        3. The system will analyze your query
        4. View potential complications and timelines
        
        **Example queries:**
        - "I have Diabetes. What complications might I develop in 2 years?"
        - "Diagnosed with Hypertension. What are the long-term risks?"
        - "I'm suffering from Obesity. What health issues might occur in 5 years?"
        """)
        
        st.divider()
        st.markdown("### Database Information")
        if st.session_state.graph:
            try:
                node_count = st.session_state.graph.query("MATCH (n) RETURN count(n) as count")[0]['count']
                rel_count = st.session_state.graph.query("MATCH ()-[r]->() RETURN count(r) as count")[0]['count']
                st.write(f"Nodes: {node_count}, Relationships: {rel_count}")
            except:
                st.write("Database stats unavailable")

def render_main_content():
    """Render the main content area"""
    st.title("Medical Complications Query Assistant")
    
    # Display current model info
    st.info(f"**Current AI Model:** {AVAILABLE_MODELS[st.session_state.selected_model]}")
    
    # Query input
    query = st.text_area(
        "Enter your medical query:",
        placeholder="e.g., I have Diabetes. What complications might I develop in 2 years?",
        height=100,
        key="query_input"
    )
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        analyze_btn = st.button("Analyze Query", type="primary", use_container_width=True)
    
    with col2:
        if st.button("Clear Input", use_container_width=True):
            st.session_state.query_input = ""
            st.rerun()
    
    if analyze_btn:
        if not query:
            st.warning("Please enter a query to analyze.")
            return
            
        if not initialize_connections(st.session_state.selected_model):
            st.error("Failed to initialize system connections. Please check your setup.")
            return
            
        with st.spinner(f"Analyzing with {AVAILABLE_MODELS[st.session_state.selected_model]}..."):
            result = st.session_state.processor.process_query(query)
            
        if not result["success"]:
            st.error(result["error"])
            return
            
        # Display results
        st.success("Analysis complete!")
        
        # Results summary
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Query Analysis")
            st.info(f"**Diagnosis:** {result['diagnosis']}")
            if result['timeframe']:
                st.info(f"**Timeframe:** {result['timeframe']} years")
            else:
                st.info("**Timeframe:** Not specified")
                
        with col2:
            st.subheader("Complications Found")
            st.info(f"**Number of complications:** {len(result['complications'])}")
            st.info(f"**AI Model Used:** {AVAILABLE_MODELS[st.session_state.selected_model]}")
        
        # Display complications in an expandable section
        with st.expander("View Detailed Complications Data", expanded=False):
            for i, comp in enumerate(result['complications']):
                with st.container():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**{i+1}. {comp['complication_name']}**")
                    with col2:
                        st.markdown(f"*{comp['frequency']} cases*")
                    
                    # Only show Average Onset rounded to 3 decimal places
                    st.metric("Average Onset", f"{comp['avg_years']} years")
                    
                    st.divider()
        
        # Display the generated response
        st.subheader("Medical Assessment")
        st.markdown("---")
        
        # Use a clean card-style container for the response
        st.markdown(
            f'<div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 4px solid #4CAF50; margin: 10px 0;">'
            f'<div style="color: #333333;">{result["response"]}</div>'
            f'</div>', 
            unsafe_allow_html=True
        )
        
        # Add a disclaimer
        st.markdown("---")
        st.warning("""
        **Disclaimer:** This information is based on general medical data and should not be 
        considered as personal medical advice. Always consult with a healthcare professional 
        for diagnosis and treatment recommendations.
        """)

# Main app
def main():
    # Initialize with default model if not already initialized
    if st.session_state.llm is None:
        initialize_connections(st.session_state.selected_model)
    
    render_sidebar()
    render_main_content()

if __name__ == "__main__":
    main()