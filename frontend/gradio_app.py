"""
Gradio Frontend for Financial RAG Engine
Chat interface with file upload and RAG capabilities
"""

import gradio as gr
import requests
import json
import os
from typing import List, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FinancialRAGInterface:
    """Gradio interface for Financial RAG Engine"""
    
    def __init__(self):
        self.backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        
    def upload_pdf(self, file) -> str:
        """Handle PDF upload and trigger pipeline"""
        if file is None:
            return "❌ Please upload a PDF file"
        
        try:
            # Upload file to backend
            with open(file.name, 'rb') as f:
                files = {'file': f}
                response = requests.post(f"{self.backend_url}/upload", files=files)
            
            if response.status_code == 200:
                return "✅ PDF uploaded successfully! Pipeline started."
            else:
                return f"❌ Upload failed: {response.text}"
                
        except Exception as e:
            logger.error(f"Upload error: {e}")
            return f"❌ Upload error: {str(e)}"
    
    def query_rag(self, question: str, history: List[Tuple[str, str]]) -> Tuple[str, List[Tuple[str, str]]]:
        """Handle RAG queries"""
        if not question.strip():
            return "", history
        
        try:
            # Send query to backend
            response = requests.post(
                f"{self.backend_url}/query",
                json={"question": question}
            )
            
            if response.status_code == 200:
                result = response.json()
                answer = result.get("answer", "No answer found")
                sources = result.get("sources", [])
                
                # Format response with sources
                formatted_answer = f"{answer}\n\n**Sources:**\n"
                for i, source in enumerate(sources[:3], 1):
                    formatted_answer += f"{i}. {source}\n"
                
                # Update history
                history.append((question, formatted_answer))
                return "", history
            else:
                error_msg = f"❌ Query failed: {response.text}"
                history.append((question, error_msg))
                return "", history
                
        except Exception as e:
            logger.error(f"Query error: {e}")
            error_msg = f"❌ Query error: {str(e)}"
            history.append((question, error_msg))
            return "", history
    
    def get_pipeline_status(self) -> str:
        """Get pipeline status"""
        try:
            response = requests.get(f"{self.backend_url}/status")
            if response.status_code == 200:
                status = response.json()
                return f"**Pipeline Status:** {status.get('status', 'Unknown')}\n**Progress:** {status.get('progress', '0%')}"
            else:
                return "❌ Status check failed"
        except Exception as e:
            return f"❌ Status error: {str(e)}"

# Create interface
rag_interface = FinancialRAGInterface()

# Gradio interface
with gr.Blocks(title="Financial RAG Engine", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🏦 Financial RAG Engine")
    gr.Markdown("Upload financial documents and ask questions about them!")
    
    with gr.Tab("📄 Upload & Process"):
        with gr.Row():
            with gr.Column():
                pdf_upload = gr.File(
                    label="Upload Financial PDF",
                    file_types=[".pdf"],
                    file_count="single"
                )
                upload_btn = gr.Button("Upload & Start Pipeline", variant="primary")
                upload_status = gr.Textbox(label="Upload Status", interactive=False)
            
            with gr.Column():
                status_btn = gr.Button("Check Pipeline Status")
                pipeline_status = gr.Textbox(label="Pipeline Status", interactive=False)
    
    with gr.Tab("💬 Chat with Documents"):
        chatbot = gr.Chatbot(
            label="Financial RAG Chat",
            height=400,
            show_label=True
        )
        
        with gr.Row():
            msg = gr.Textbox(
                label="Ask a question about your financial documents",
                placeholder="What is the company's revenue?",
                lines=2
            )
            send_btn = gr.Button("Send", variant="primary")
    
    with gr.Tab("📊 Analytics"):
        gr.Markdown("### Pipeline Analytics")
        analytics = gr.Textbox(
            label="Processing Statistics",
            value="No data available yet",
            interactive=False,
            lines=10
        )
    
    # Event handlers
    upload_btn.click(
        fn=rag_interface.upload_pdf,
        inputs=[pdf_upload],
        outputs=[upload_status]
    )
    
    status_btn.click(
        fn=rag_interface.get_pipeline_status,
        outputs=[pipeline_status]
    )
    
    send_btn.click(
        fn=rag_interface.query_rag,
        inputs=[msg, chatbot],
        outputs=[msg, chatbot]
    )
    
    msg.submit(
        fn=rag_interface.query_rag,
        inputs=[msg, chatbot],
        outputs=[msg, chatbot]
    )

# Launch the interface
if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=True
    )
