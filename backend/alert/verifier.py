"""
SlopeSense — Agentic LLM Verifier

Agent 2 (Auditor): Reviews the mathematical FPI model's (Agent 1) proposed alerts 
to suppress false positives by analyzing contextual telemetry.
"""

import json
import logging
import os
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

class LLMVerifier:
    """
    Acts as an independent auditor to review proposed alerts.
    """

    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        self._setup_client()

    def _setup_client(self):
        if self.api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-1.5-pro')
                self.has_llm = True
            except ImportError:
                logger.warning("google-generativeai not installed. Using dummy verifier.")
                self.has_llm = False
        else:
            logger.info("No GEMINI_API_KEY provided. Using dummy verifier.")
            self.has_llm = False

    async def verify(self, block_data: Dict) -> Tuple[bool, str]:
        """
        Verify if the proposed alert is valid based on telemetry context.
        Returns:
            (is_approved: bool, reason: str)
        """
        fpi = block_data.get('fpi_score', 0)
        rainfall = block_data.get('rainfall_3d_mm', 0)
        soil = block_data.get('soil_moisture_percentile', 0)
        tier = block_data.get('tier', 'UNKNOWN')

        if not self.has_llm:
            # Fallback heuristic if no LLM is available
            # Suppress high alerts if there's very little rain and low soil moisture
            if fpi > 0.65 and rainfall < 50 and soil < 60:
                return False, "Suppressed by heuristic: High FPI but insufficient rainfall and soil moisture."
            return True, "Approved by heuristic (No LLM available)."

        prompt = f"""
        You are an expert geotechnical auditor verifying a landslide alert system.
        The mathematical model has proposed an alert with the following telemetry:
        
        - Tier: {tier}
        - FPI Score: {fpi*100:.1f}%
        - 3-day Rainfall: {rainfall} mm
        - Soil Moisture Percentile: {soil}th percentile
        
        Rule: A landslide alert generally requires high rainfall (e.g., > 100mm) OR high soil moisture saturation (> 80th percentile).
        If the FPI is high but BOTH rainfall and soil moisture are low, it might be a false positive caused by static geological factors.
        
        Analyze this data and determine if the alert should be approved or suppressed.
        Return ONLY valid JSON in this exact format:
        {{"approved": true/false, "reason": "brief explanation"}}
        """

        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:-3]
            elif text.startswith("```"):
                text = text[3:-3]
                
            data = json.loads(text)
            return data.get("approved", True), data.get("reason", "LLM review complete.")
        except Exception as e:
            logger.error(f"LLM Verification failed: {e}")
            return True, f"Verification failed, defaulting to approve: {str(e)}"
