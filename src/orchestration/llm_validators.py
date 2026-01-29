"""
LLM Output Validators for FinagentiX

This module implements validation and guardrails for LLM-generated content,
ensuring outputs are:
1. Structurally valid (schema validation)
2. Grounded in source data (no hallucinated numbers)
3. Logically consistent (recommendation matches reasoning)

Approaches implemented:
- Pydantic Schema Validation
- Data Grounding Verification
- Recommendation Consistency Checks
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field, field_validator, model_validator


class Recommendation(str, Enum):
    """Valid investment recommendations"""
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"


class Confidence(str, Enum):
    """Valid confidence levels"""
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"


class InvestmentAnalysisSchema(BaseModel):
    """
    Pydantic schema for validating LLM investment analysis output.
    
    This ensures the LLM returns properly structured data with all required fields.
    """
    analysis: str = Field(
        ..., 
        min_length=20, 
        max_length=1000,
        description="Executive summary of the investment case"
    )
    recommendation: str = Field(
        ..., 
        description="BUY, HOLD, or SELL recommendation"
    )
    confidence: str = Field(
        ..., 
        description="Confidence level: high, moderate, or low"
    )
    reasoning: str = Field(
        ..., 
        min_length=50,
        description="Detailed explanation of the recommendation"
    )
    key_insights: List[str] = Field(
        default_factory=list,
        min_length=0,
        max_length=10,
        description="List of key insights"
    )
    risk_considerations: List[str] = Field(
        default_factory=list,
        min_length=0,
        max_length=10,
        description="List of risk factors"
    )
    price_context: str = Field(
        default="",
        description="Context on current price"
    )
    
    @field_validator('recommendation')
    @classmethod
    def validate_recommendation(cls, v: str) -> str:
        """Normalize and validate recommendation"""
        v_upper = v.upper().strip()
        if v_upper not in ["BUY", "HOLD", "SELL"]:
            # Try to extract from common variations
            if "buy" in v.lower():
                return "BUY"
            elif "sell" in v.lower():
                return "SELL"
            else:
                return "HOLD"
        return v_upper
    
    @field_validator('confidence')
    @classmethod
    def validate_confidence(cls, v: str) -> str:
        """Normalize and validate confidence"""
        v_lower = v.lower().strip()
        if v_lower not in ["high", "moderate", "low"]:
            # Default to moderate if unclear
            return "moderate"
        return v_lower
    
    @field_validator('key_insights', 'risk_considerations')
    @classmethod
    def validate_list_items(cls, v: List[str]) -> List[str]:
        """Ensure list items are non-empty strings"""
        return [item.strip() for item in v if item and isinstance(item, str) and item.strip()]


@dataclass
class ValidationResult:
    """Result of LLM output validation"""
    is_valid: bool
    validated_output: Optional[Dict[str, Any]] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    grounding_issues: List[str] = field(default_factory=list)
    consistency_issues: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "grounding_issues": self.grounding_issues,
            "consistency_issues": self.consistency_issues,
        }


class LLMOutputValidator:
    """
    Validates LLM outputs for investment analysis.
    
    Implements three levels of validation:
    1. Schema Validation - Ensures JSON structure matches expected format
    2. Data Grounding - Verifies LLM claims match source data
    3. Consistency Checks - Ensures recommendation aligns with reasoning
    """
    
    # Tolerance for numerical grounding checks (10% difference allowed)
    NUMERIC_TOLERANCE = 0.10
    
    def __init__(self):
        self.validation_count = 0
        self.failure_count = 0
    
    def validate(
        self,
        llm_output: Dict[str, Any],
        source_data: Dict[str, Any],
        rule_based_recommendation: Optional[Dict[str, Any]] = None,
    ) -> ValidationResult:
        """
        Perform full validation of LLM output.
        
        Args:
            llm_output: The raw LLM output dictionary
            source_data: Original data used to generate the analysis
            rule_based_recommendation: Optional rule-based rec for consistency check
            
        Returns:
            ValidationResult with validated output or errors
        """
        self.validation_count += 1
        result = ValidationResult(is_valid=True)
        
        # Step 1: Schema Validation
        schema_result = self._validate_schema(llm_output)
        if not schema_result[0]:
            result.is_valid = False
            result.errors.extend(schema_result[1])
            self.failure_count += 1
            return result
        
        validated_output = schema_result[1]
        
        # Step 2: Data Grounding Checks
        grounding_issues = self._check_data_grounding(validated_output, source_data)
        result.grounding_issues = grounding_issues
        if grounding_issues:
            result.warnings.extend([f"Grounding: {issue}" for issue in grounding_issues])
        
        # Step 3: Consistency Checks
        consistency_issues = self._check_consistency(
            validated_output, 
            source_data, 
            rule_based_recommendation
        )
        result.consistency_issues = consistency_issues
        if consistency_issues:
            result.warnings.extend([f"Consistency: {issue}" for issue in consistency_issues])
        
        # If there are major grounding issues, mark as invalid
        if len(grounding_issues) > 2:
            result.is_valid = False
            result.errors.append("Too many grounding issues - LLM may be hallucinating")
            self.failure_count += 1
        
        result.validated_output = validated_output
        return result
    
    def _validate_schema(
        self, 
        llm_output: Dict[str, Any]
    ) -> Tuple[bool, Any]:
        """
        Validate LLM output against Pydantic schema.
        
        Returns:
            Tuple of (success, validated_dict or error_list)
        """
        try:
            validated = InvestmentAnalysisSchema(**llm_output)
            return (True, validated.model_dump())
        except Exception as e:
            errors = []
            if hasattr(e, 'errors'):
                for error in e.errors():
                    field_name = '.'.join(str(loc) for loc in error.get('loc', ['unknown']))
                    msg = error.get('msg', 'validation error')
                    errors.append(f"Field '{field_name}': {msg}")
            else:
                errors.append(str(e))
            return (False, errors)
    
    def _check_data_grounding(
        self,
        validated_output: Dict[str, Any],
        source_data: Dict[str, Any],
    ) -> List[str]:
        """
        Verify that LLM claims are grounded in source data.
        
        Checks:
        - Price mentions match actual price data
        - Technical indicators mentioned match source
        - Risk metrics mentioned match source
        """
        issues = []
        
        reasoning = validated_output.get("reasoning", "").lower()
        analysis = validated_output.get("analysis", "").lower()
        combined_text = f"{reasoning} {analysis}"
        
        # Extract source values for comparison
        market_data = source_data.get("market_data", {})
        technical = source_data.get("technical", {})
        risk = source_data.get("risk", {})
        
        # Check price grounding
        current_price = market_data.get("current_price", {}).get("value")
        if current_price and isinstance(current_price, (int, float)):
            # Look for price mentions in text
            issues.extend(
                self._check_number_grounding(
                    combined_text, 
                    current_price, 
                    "price",
                    tolerance=self.NUMERIC_TOLERANCE
                )
            )
        
        # Check SMA grounding
        sma_50 = technical.get("sma_50", {}).get("sma")
        if sma_50 and isinstance(sma_50, (int, float)):
            if "sma" in combined_text or "moving average" in combined_text:
                issues.extend(
                    self._check_number_grounding(
                        combined_text,
                        sma_50,
                        "SMA 50",
                        tolerance=self.NUMERIC_TOLERANCE
                    )
                )
        
        # Check RSI grounding
        rsi = technical.get("rsi", {}).get("rsi")
        if rsi and isinstance(rsi, (int, float)):
            if "rsi" in combined_text:
                issues.extend(
                    self._check_number_grounding(
                        combined_text,
                        rsi,
                        "RSI",
                        tolerance=0.15  # Slightly higher tolerance for RSI
                    )
                )
        
        # Check for contradictory sentiment claims
        sentiment = source_data.get("sentiment", {}).get("sentiment", {})
        overall_sentiment = sentiment.get("overall_sentiment", "").lower()
        
        if overall_sentiment:
            if "positive" in overall_sentiment and "negative sentiment" in combined_text:
                issues.append("Claims negative sentiment but source shows positive")
            elif "negative" in overall_sentiment and "positive sentiment" in combined_text:
                issues.append("Claims positive sentiment but source shows negative")
        
        return issues
    
    def _check_number_grounding(
        self,
        text: str,
        expected_value: float,
        metric_name: str,
        tolerance: float = 0.10,
    ) -> List[str]:
        """
        Check if numbers mentioned in text match expected value within tolerance.
        
        This is a heuristic check - we look for numbers in the text that might
        be referring to the metric and verify they're close to the actual value.
        """
        issues = []
        import re
        
        # Find all numbers in text (including decimals)
        numbers = re.findall(r'\$?([\d,]+\.?\d*)', text)
        
        for num_str in numbers:
            try:
                num = float(num_str.replace(',', ''))
                # Check if this number is in the same magnitude as expected
                if expected_value > 0:
                    ratio = num / expected_value
                    # If the number is close to expected (within 50% of range)
                    # but not within tolerance, flag it
                    if 0.5 < ratio < 2.0:  # Same order of magnitude
                        if abs(ratio - 1.0) > tolerance:
                            issues.append(
                                f"{metric_name} mentioned as ~{num:.2f} but actual is {expected_value:.2f}"
                            )
            except (ValueError, ZeroDivisionError):
                continue
        
        return issues
    
    def _check_consistency(
        self,
        validated_output: Dict[str, Any],
        source_data: Dict[str, Any],
        rule_based_recommendation: Optional[Dict[str, Any]],
    ) -> List[str]:
        """
        Check logical consistency of the analysis.
        
        Verifies:
        - Recommendation aligns with reasoning tone
        - Key insights support the recommendation
        - Risk considerations match risk metrics
        """
        issues = []
        
        recommendation = validated_output.get("recommendation", "HOLD")
        reasoning = validated_output.get("reasoning", "").lower()
        key_insights = validated_output.get("key_insights", [])
        risk_considerations = validated_output.get("risk_considerations", [])
        
        # Check recommendation vs reasoning tone
        bullish_words = ["bullish", "upward", "growth", "strong", "positive", "opportunity", "undervalued"]
        bearish_words = ["bearish", "downward", "decline", "weak", "negative", "risk", "overvalued", "concern"]
        
        bullish_count = sum(1 for word in bullish_words if word in reasoning)
        bearish_count = sum(1 for word in bearish_words if word in reasoning)
        
        if recommendation == "BUY" and bearish_count > bullish_count + 2:
            issues.append("BUY recommendation but reasoning contains more bearish than bullish language")
        elif recommendation == "SELL" and bullish_count > bearish_count + 2:
            issues.append("SELL recommendation but reasoning contains more bullish than bearish language")
        
        # Check if rule-based and LLM recommendations align
        if rule_based_recommendation:
            rule_action = rule_based_recommendation.get("action", "HOLD")
            if rule_action != recommendation:
                # This is a warning, not necessarily wrong
                issues.append(
                    f"LLM recommends {recommendation} but rule-based system suggests {rule_action}"
                )
        
        # Check risk metrics vs risk considerations
        risk = source_data.get("risk", {})
        max_drawdown = risk.get("drawdown", {}).get("max_drawdown_pct", 0)
        beta = risk.get("beta", {}).get("beta", 1.0)
        
        if max_drawdown and isinstance(max_drawdown, (int, float)):
            if max_drawdown > 20 and recommendation == "BUY":
                has_risk_mention = any("drawdown" in r.lower() or "volatil" in r.lower() 
                                       for r in risk_considerations)
                if not has_risk_mention:
                    issues.append("High drawdown risk not mentioned in risk considerations for BUY")
        
        if beta and isinstance(beta, (int, float)):
            if beta > 1.5 and recommendation == "BUY":
                has_beta_mention = any("beta" in r.lower() or "volatil" in r.lower() 
                                       for r in risk_considerations)
                if not has_beta_mention:
                    issues.append("High beta not mentioned in risk considerations for BUY")
        
        return issues
    
    def get_stats(self) -> Dict[str, Any]:
        """Get validation statistics"""
        return {
            "total_validations": self.validation_count,
            "failures": self.failure_count,
            "success_rate": (
                (self.validation_count - self.failure_count) / self.validation_count * 100
                if self.validation_count > 0 else 0
            ),
        }


def validate_llm_investment_analysis(
    llm_output: Dict[str, Any],
    market_data: Dict[str, Any],
    technical: Dict[str, Any],
    risk: Dict[str, Any],
    sentiment: Dict[str, Any],
    rule_based_recommendation: Optional[Dict[str, Any]] = None,
) -> ValidationResult:
    """
    Convenience function to validate LLM investment analysis output.
    
    Args:
        llm_output: Raw output from LLM
        market_data: Market data used in analysis
        technical: Technical indicators used
        risk: Risk metrics used
        sentiment: Sentiment data used
        rule_based_recommendation: Optional rule-based recommendation
        
    Returns:
        ValidationResult with validation status and any issues found
    """
    validator = LLMOutputValidator()
    
    source_data = {
        "market_data": market_data,
        "technical": technical,
        "risk": risk,
        "sentiment": sentiment,
    }
    
    return validator.validate(
        llm_output=llm_output,
        source_data=source_data,
        rule_based_recommendation=rule_based_recommendation,
    )
