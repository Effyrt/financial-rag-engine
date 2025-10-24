"""
Concept Note Generator using Instructor - ENTERPRISE VERSION
Structured output generation with GPT-4, validation, and quality control.
"""

from typing import List, Optional
import instructor
from openai import OpenAI
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
import os

from concept_generator.instructor_models import (
    ConceptNote, ConceptNoteRequest, Citation, CitationType
)


class ConceptNoteGenerator:
    """
    Production concept note generator with Instructor.
    
    Features:
    - Structured JSON output via Instructor
    - Automatic schema validation
    - Context-aware generation
    - Source-specific prompting (PDF vs Wikipedia)
    - Quality validation
    - Automatic retry on validation failures
    - Token usage tracking
    """
    
    def __init__(self,
                 model: str = "gpt-4-turbo-preview",
                 api_key: Optional[str] = None,
                 temperature: float = 0.3,
                 max_retries: int = 3):
        """Initialize concept note generator."""
        self.model = model
        self.temperature = temperature
        self.max_retries = max_retries
        
        # Initialize Instructor-patched OpenAI client
        client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.client = instructor.patch(client)
        
        logger.info(f"ConceptNoteGenerator initialized with {model}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True
    )
    def generate(self, request: ConceptNoteRequest) -> ConceptNote:
        """Generate structured concept note from request."""
        logger.info(f"Generating concept note for: {request.concept_name}")
        
        system_prompt = self._build_system_prompt(request)
        user_prompt = self._build_user_prompt(request)
        
        try:
            concept_note = self.client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                response_model=ConceptNote,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_retries=self.max_retries
            )
            
            logger.info(
                f"✓ Generated concept note for '{concept_note.concept_name}' "
                f"(confidence: {concept_note.confidence_score:.2f}, "
                f"key_points: {len(concept_note.key_points)}, "
                f"citations: {len(concept_note.citations)})"
            )
            
            return concept_note
            
        except Exception as e:
            logger.error(f"Concept generation failed: {e}")
            raise
    
    def _build_system_prompt(self, request: ConceptNoteRequest) -> str:
        """Build comprehensive system prompt."""
        
        base_prompt = """You are AURELIA, an expert financial concept note generator. Your role is to create comprehensive, accurate, and well-structured concept notes for financial topics.

Your notes should be:
1. **Accurate**: Based strictly on provided context
2. **Comprehensive**: Cover all important aspects
3. **Practical**: Include real-world applications and examples
4. **Technical**: Include formulas and code when relevant
5. **Well-cited**: Provide clear, specific citations to sources

Generate concept notes that would be valuable for:
- Financial professionals learning new concepts
- Students studying quantitative finance
- Developers implementing financial algorithms
- Risk managers and portfolio managers"""
        
        if request.source.lower() == "pdf" or "fintbx" in request.source.lower():
            base_prompt += """

The context is from the Financial Toolbox User's Guide (fintbx.pdf).
IMPORTANT INSTRUCTIONS:
- Include specific MATLAB code examples when available in context
- Reference exact sections and page numbers for citations
- Emphasize practical implementation details
- Include function signatures and parameter descriptions
- Use technical terminology from MathWorks documentation
- Provide code examples that can be directly used"""
        
        elif request.source.lower() == "wikipedia":
            base_prompt += """

The context is from Wikipedia.
IMPORTANT INSTRUCTIONS:
- Provide more foundational, educational explanation
- Include historical context when relevant
- Be clear that this is from Wikipedia (not the primary PDF source)
- Mark all citations as Wikipedia sources
- Confidence score should be lower (typically 0.5-0.7) as this is secondary source
- Focus on conceptual understanding over implementation"""
        
        return base_prompt
    
    def _build_user_prompt(self, request: ConceptNoteRequest) -> str:
        """Build detailed user prompt with context."""
        
        prompt_parts = [
            f"Generate a comprehensive concept note for: **{request.concept_name}**",
            "",
            "## Retrieved Context",
            ""
        ]
        
        if request.context:
            for idx, context in enumerate(request.context, 1):
                prompt_parts.append(f"### Context Passage {idx}")
                prompt_parts.append(context)
                prompt_parts.append("")
        else:
            prompt_parts.append("No specific context provided. Use your knowledge of this financial concept.")
            prompt_parts.append("")
        
        prompt_parts.extend([
            "## Generation Requirements",
            f"- Primary source: {request.source}",
            f"- Include code examples: {request.include_code_examples}",
            f"- Target length: {request.target_length}",
            "",
            "## Output Structure",
            "Generate a complete ConceptNote that includes:",
            "",
            "1. **Clear Definition** (50-500 characters)",
            "   - Concise, accurate definition",
            "   - Use standard financial terminology",
            "",
            "2. **Detailed Explanation** (200+ characters)",
            "   - Comprehensive explanation with context",
            "   - Include mathematical basis if applicable",
            "   - Explain practical significance",
            "",
            "3. **Key Points** (3-7 bullet points)",
            "   - Most important takeaways",
            "   - Practical considerations",
            "   - Common use cases",
            "",
            "4. **Formulas** (if applicable)",
            "   - LaTeX representation",
            "   - Variable definitions",
            "   - Explanation of each formula",
            "",
            "5. **Use Cases** (1-5 examples)",
            "   - Real-world applications",
            "   - Industry usage",
            "   - Practical scenarios",
            "",
            "6. **Code Examples** (if requested and context includes code)",
            "   - Complete, working examples",
            "   - Clear descriptions",
            "   - Expected outputs",
            "",
            "7. **Related Concepts**",
            "   - Prerequisites needed to understand",
            "   - Related concepts with relationships",
            "",
            "8. **Citations**",
            "   - Specific section and page references",
            "   - Relevance scores for each citation",
            "",
            "CRITICAL: Ensure all information is accurate and directly traceable to the provided context.",
            "Do not invent information not present in the context."
        ])
        
        return "\n".join(prompt_parts)
    
    def generate_from_contexts(self,
                              concept_name: str,
                              contexts: List[str],
                              source: str,
                              citations: Optional[List[dict]] = None) -> ConceptNote:
        """Convenience method to generate from contexts directly."""
        request = ConceptNoteRequest(
            concept_name=concept_name,
            context=contexts,
            source=source,
            include_code_examples=True,
            target_length="comprehensive"
        )
        
        concept_note = self.generate(request)
        
        # Enhance citations if provided
        if citations:
            concept_note.citations = self._merge_citations(
                concept_note.citations,
                citations
            )
        
        return concept_note
    
    def _merge_citations(self,
                        generated_citations: List[Citation],
                        provided_citations: List[dict]) -> List[Citation]:
        """Merge generated citations with provided citation metadata."""
        enhanced_citations = list(generated_citations)
        
        for prov_cit in provided_citations:
            if isinstance(prov_cit, dict):
                citation = Citation(
                    source=prov_cit.get('source', 'Unknown'),
                    citation_type=CitationType.PDF_SECTION,
                    location=f"Section {prov_cit.get('section', 'Unknown')}, "
                            f"Pages {prov_cit.get('pages', [])}",
                    relevance_score=prov_cit.get('score', 0.8),
                    excerpt=None
                )
                enhanced_citations.append(citation)
        
        return enhanced_citations
    
    def validate_concept_note(self, concept_note: ConceptNote) -> tuple[bool, List[str]]:
        """
        Validate quality of generated concept note.
        
        Returns:
            (is_valid, list_of_issues)
        """
        issues = []
        
        if len(concept_note.definition) < 50:
            issues.append("Definition too short (minimum 50 characters)")
        
        if len(concept_note.detailed_explanation) < 200:
            issues.append("Explanation too brief (minimum 200 characters)")
        
        if len(concept_note.key_points) < 3:
            issues.append("Too few key points (minimum 3)")
        
        if len(concept_note.use_cases) < 1:
            issues.append("No use cases provided")
        
        if len(concept_note.citations) < 1:
            issues.append("No citations provided")
        
        if concept_note.confidence_score < 0.5:
            issues.append(f"Low confidence score ({concept_note.confidence_score:.2f})")
        
        is_valid = len(issues) == 0
        
        if not is_valid:
            logger.warning(f"Concept note validation failed for '{concept_note.concept_name}': {issues}")
        else:
            logger.info(f"✓ Concept note validation passed for '{concept_note.concept_name}'")
        
        return is_valid, issues


if __name__ == "__main__":
    generator = ConceptNoteGenerator()
    
    # Test with sample
    request = ConceptNoteRequest(
        concept_name="Sharpe Ratio",
        context=[
            "The Sharpe ratio is a measure of risk-adjusted return. "
            "It is calculated as the excess return divided by the standard deviation. "
            "Formula: S = (Rp - Rf) / σp"
        ],
        source="Financial Toolbox User Guide",
        include_code_examples=True
    )
    
    try:
        note = generator.generate(request)
        is_valid, issues = generator.validate_concept_note(note)
        
        print(f"\nGenerated: {note.concept_name}")
        print(f"Category: {note.category}")
        print(f"Definition: {note.definition[:100]}...")
        print(f"Key Points: {len(note.key_points)}")
        print(f"Formulas: {len(note.formulas)}")
        print(f"Citations: {len(note.citations)}")
        print(f"Valid: {is_valid}")
        if issues:
            print(f"Issues: {issues}")
            
    except Exception as e:
        print(f"Generation failed: {e}")
        print("Make sure OPENAI_API_KEY is set in .env")
