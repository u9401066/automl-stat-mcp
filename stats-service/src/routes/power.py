"""
Stats Service - Power Analysis Routes

Routes for sample size and power calculations:
- T-test power analysis
- Proportion test power analysis
- ANOVA power analysis
- Chi-square power analysis
- Survival analysis power
"""
from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional, List

router = APIRouter(prefix="/power", tags=["Power Analysis"])


# =============================================================================
# Request/Response Models
# =============================================================================

class TTestPowerRequest(BaseModel):
    """Request for t-test power analysis"""
    effect_size: Optional[float] = Field(None, description="Cohen's d effect size")
    mean1: Optional[float] = Field(None, description="Mean of group 1 (alternative to effect_size)")
    mean2: Optional[float] = Field(None, description="Mean of group 2")
    std: Optional[float] = Field(None, description="Common standard deviation")
    alpha: float = Field(default=0.05, description="Significance level")
    power: Optional[float] = Field(default=0.8, description="Desired power (for sample size calc)")
    n: Optional[int] = Field(None, description="Sample size per group (for power calc)")
    ratio: float = Field(default=1.0, description="n2/n1 ratio")
    alternative: str = Field(default="two-sided", description="Alternative: two-sided, larger, smaller")


class ProportionPowerRequest(BaseModel):
    """Request for proportion test power analysis"""
    p1: float = Field(..., description="Proportion in group 1")
    p2: float = Field(..., description="Proportion in group 2")
    alpha: float = Field(default=0.05, description="Significance level")
    power: Optional[float] = Field(default=0.8, description="Desired power")
    n: Optional[int] = Field(None, description="Sample size per group")
    ratio: float = Field(default=1.0, description="n2/n1 ratio")
    alternative: str = Field(default="two-sided", description="Alternative hypothesis")


class ANOVAPowerRequest(BaseModel):
    """Request for ANOVA power analysis"""
    effect_size: Optional[float] = Field(None, description="Cohen's f effect size")
    means: Optional[List[float]] = Field(None, description="Group means (alternative to effect_size)")
    std: Optional[float] = Field(None, description="Common standard deviation")
    k: int = Field(..., description="Number of groups")
    alpha: float = Field(default=0.05, description="Significance level")
    power: Optional[float] = Field(default=0.8, description="Desired power")
    n: Optional[int] = Field(None, description="Sample size per group")


class ChiSquarePowerRequest(BaseModel):
    """Request for chi-square power analysis"""
    effect_size: Optional[float] = Field(None, description="Cohen's w effect size")
    contingency_table: Optional[List[List[float]]] = Field(None, description="Expected proportions (alternative)")
    df: Optional[int] = Field(None, description="Degrees of freedom")
    alpha: float = Field(default=0.05, description="Significance level")
    power: Optional[float] = Field(default=0.8, description="Desired power")
    n: Optional[int] = Field(None, description="Total sample size")


class SurvivalPowerRequest(BaseModel):
    """Request for survival analysis power"""
    hazard_ratio: float = Field(..., description="Expected hazard ratio")
    p1: float = Field(..., description="Event probability in control group")
    alpha: float = Field(default=0.05, description="Significance level")
    power: Optional[float] = Field(default=0.8, description="Desired power")
    n_events: Optional[int] = Field(None, description="Number of events (for power calc)")
    ratio: float = Field(default=1.0, description="n2/n1 ratio")
    dropout_rate: float = Field(default=0.0, description="Expected dropout rate")
    accrual_time: Optional[float] = Field(None, description="Accrual period")
    followup_time: Optional[float] = Field(None, description="Follow-up period")


class PowerResponse(BaseModel):
    """Response for power analysis"""
    calculation_type: str = Field(..., description="sample_size or power")
    result: float = Field(..., description="Calculated sample size or power")
    parameters: dict = Field(..., description="Input parameters used")
    interpretation: str = Field(..., description="Plain language interpretation")
    assumptions: List[str] = Field(..., description="Key assumptions")


class EffectSizeRequest(BaseModel):
    """Request for effect size calculation"""
    test_type: str = Field(..., description="ttest, proportion, anova, chi-square")
    # For t-test
    mean1: Optional[float] = Field(None, description="Mean of group 1")
    mean2: Optional[float] = Field(None, description="Mean of group 2")
    std: Optional[float] = Field(None, description="Pooled standard deviation")
    # For proportion
    p1: Optional[float] = Field(None, description="Proportion 1")
    p2: Optional[float] = Field(None, description="Proportion 2")
    # For ANOVA
    means: Optional[List[float]] = Field(None, description="Group means")
    # For chi-square
    contingency_table: Optional[List[List[float]]] = Field(None, description="Observed frequencies")


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/ttest", response_model=PowerResponse)
async def calculate_ttest_power(request: TTestPowerRequest):
    """
    📊 Calculate sample size or power for independent t-test.
    
    Provide either:
    - effect_size (Cohen's d): For direct calculation
    - mean1, mean2, std: Effect size calculated as (mean1-mean2)/std
    
    If n is provided: Calculates power
    If power is provided: Calculates required sample size
    
    Effect size interpretation (Cohen's d):
    - 0.2: Small effect
    - 0.5: Medium effect
    - 0.8: Large effect
    """
    from statsmodels.stats.power import TTestIndPower
    
    analysis = TTestIndPower()
    
    # Calculate effect size if means provided
    effect_size = request.effect_size
    if effect_size is None and all([request.mean1, request.mean2, request.std]):
        effect_size = abs(request.mean1 - request.mean2) / request.std
    
    if effect_size is None:
        return PowerResponse(
            calculation_type="error",
            result=0,
            parameters=request.model_dump(),
            interpretation="Please provide either effect_size or (mean1, mean2, std)",
            assumptions=[],
        )
    
    # Determine calculation type
    if request.n is not None:
        # Calculate power
        calc_type = "power"
        result = analysis.solve_power(
            effect_size=effect_size,
            nobs1=request.n,
            alpha=request.alpha,
            ratio=request.ratio,
            alternative=request.alternative,
        )
    else:
        # Calculate sample size
        calc_type = "sample_size"
        result = analysis.solve_power(
            effect_size=effect_size,
            power=request.power,
            alpha=request.alpha,
            ratio=request.ratio,
            alternative=request.alternative,
        )
    
    return PowerResponse(
        calculation_type=calc_type,
        result=result,
        parameters={
            "effect_size": effect_size,
            "alpha": request.alpha,
            "power": request.power,
            "n": request.n,
            "ratio": request.ratio,
            "alternative": request.alternative,
        },
        interpretation=f"With effect size d={effect_size:.2f} and α={request.alpha}, "
                       f"you need approximately {int(result)} subjects per group for {request.power*100:.0f}% power."
                       if calc_type == "sample_size" else
                       f"With n={request.n} per group and effect size d={effect_size:.2f}, "
                       f"you have {result*100:.1f}% power to detect a significant difference.",
        assumptions=[
            "Independent samples",
            "Normally distributed outcomes",
            "Equal variances (use Welch's t-test if violated)",
        ],
    )


@router.post("/proportion", response_model=PowerResponse)
async def calculate_proportion_power(request: ProportionPowerRequest):
    """
    📊 Calculate sample size or power for two-proportion test.
    
    Args:
        p1: Expected proportion in group 1 (control)
        p2: Expected proportion in group 2 (treatment)
        alpha: Significance level
        power: Desired power (if calculating sample size)
        n: Sample size per group (if calculating power)
    
    Effect size (Cohen's h) interpretation:
    - 0.2: Small effect
    - 0.5: Medium effect
    - 0.8: Large effect
    """
    import math
    from statsmodels.stats.power import NormalIndPower
    
    analysis = NormalIndPower()
    
    # Calculate Cohen's h
    h = 2 * (math.asin(math.sqrt(request.p1)) - math.asin(math.sqrt(request.p2)))
    effect_size = abs(h)
    
    # Calculate
    if request.n is not None:
        calc_type = "power"
        result = analysis.solve_power(
            effect_size=effect_size,
            nobs1=request.n,
            alpha=request.alpha,
            ratio=request.ratio,
            alternative=request.alternative,
        )
    else:
        calc_type = "sample_size"
        result = analysis.solve_power(
            effect_size=effect_size,
            power=request.power,
            alpha=request.alpha,
            ratio=request.ratio,
            alternative=request.alternative,
        )
    
    return PowerResponse(
        calculation_type=calc_type,
        result=result,
        parameters={
            "p1": request.p1,
            "p2": request.p2,
            "effect_size_h": effect_size,
            "alpha": request.alpha,
            "power": request.power,
            "n": request.n,
        },
        interpretation=f"To detect a difference from {request.p1*100:.1f}% to {request.p2*100:.1f}% "
                       f"(absolute diff: {abs(request.p1-request.p2)*100:.1f}%), "
                       f"you need {int(result)} subjects per group."
                       if calc_type == "sample_size" else
                       f"With n={request.n}, power to detect difference is {result*100:.1f}%.",
        assumptions=[
            "Independent samples",
            "Large sample approximation (np > 5)",
            "Simple random sampling",
        ],
    )


@router.post("/anova", response_model=PowerResponse)
async def calculate_anova_power(request: ANOVAPowerRequest):
    """
    📊 Calculate sample size or power for one-way ANOVA.
    
    Effect size (Cohen's f) interpretation:
    - 0.10: Small effect
    - 0.25: Medium effect
    - 0.40: Large effect
    
    Cohen's f = sqrt(η²/(1-η²)) where η² is eta-squared
    """
    from statsmodels.stats.power import FTestAnovaPower
    import numpy as np
    
    analysis = FTestAnovaPower()
    
    # Calculate effect size if means provided
    effect_size = request.effect_size
    if effect_size is None and request.means and request.std:
        means = np.array(request.means)
        between_var = np.var(means, ddof=0)
        effect_size = np.sqrt(between_var) / request.std
    
    if effect_size is None:
        effect_size = 0.25  # Default to medium effect
    
    # Calculate
    if request.n is not None:
        calc_type = "power"
        result = analysis.solve_power(
            effect_size=effect_size,
            nobs=request.n,
            alpha=request.alpha,
            k_groups=request.k,
        )
    else:
        calc_type = "sample_size"
        result = analysis.solve_power(
            effect_size=effect_size,
            power=request.power,
            alpha=request.alpha,
            k_groups=request.k,
        )
    
    return PowerResponse(
        calculation_type=calc_type,
        result=result,
        parameters={
            "effect_size_f": effect_size,
            "k": request.k,
            "alpha": request.alpha,
            "power": request.power,
            "n": request.n,
        },
        interpretation=f"For {request.k}-group ANOVA with f={effect_size:.2f}, "
                       f"you need {int(result)} subjects per group."
                       if calc_type == "sample_size" else
                       f"Power is {result*100:.1f}%.",
        assumptions=[
            "Independent observations",
            "Normally distributed residuals",
            "Homogeneity of variances",
        ],
    )


@router.post("/chi-square", response_model=PowerResponse)
async def calculate_chisquare_power(request: ChiSquarePowerRequest):
    """
    📊 Calculate sample size or power for chi-square test.
    
    Effect size (Cohen's w) interpretation:
    - 0.10: Small effect
    - 0.30: Medium effect
    - 0.50: Large effect
    """
    from statsmodels.stats.power import GofChisquarePower
    
    analysis = GofChisquarePower()
    effect_size = request.effect_size or 0.3  # Default medium effect
    
    # Calculate df
    df = request.df
    if df is None:
        df = 1  # Default
    
    # Calculate
    if request.n is not None:
        calc_type = "power"
        result = analysis.solve_power(
            effect_size=effect_size,
            nobs=request.n,
            alpha=request.alpha,
            n_bins=df + 1,  # n_bins = df + 1
        )
    else:
        calc_type = "sample_size"
        result = analysis.solve_power(
            effect_size=effect_size,
            power=request.power,
            alpha=request.alpha,
            n_bins=df + 1,
        )
    
    return PowerResponse(
        calculation_type=calc_type,
        result=result,
        parameters={
            "effect_size_w": effect_size,
            "df": request.df,
            "alpha": request.alpha,
            "power": request.power,
            "n": request.n,
        },
        interpretation=f"For chi-square test with w={effect_size:.2f} and df={request.df}, "
                       f"total N={int(result)} needed."
                       if calc_type == "sample_size" else
                       f"Power is {result*100:.1f}%.",
        assumptions=[
            "Expected cell counts ≥ 5",
            "Independent observations",
            "Mutually exclusive categories",
        ],
    )


@router.post("/survival", response_model=PowerResponse)
async def calculate_survival_power(request: SurvivalPowerRequest):
    """
    📊 Calculate sample size or power for log-rank test.
    
    Based on Schoenfeld (1983) formula:
    Events needed = 4(Z_α/2 + Z_β)² / (log(HR))²
    
    Args:
        hazard_ratio: Expected HR (treatment vs control)
        p1: Event probability in control group
        alpha: Significance level
        power: Desired power (if calculating sample size)
        n_events: Number of events (if calculating power)
        ratio: Allocation ratio (n_treatment / n_control)
    """
    import math
    from scipy import stats
    
    log_hr = math.log(request.hazard_ratio)
    r = request.ratio
    
    # Get z_alpha
    z_alpha = stats.norm.ppf(1 - request.alpha / 2)
    
    if request.n_events is not None:
        # Calculate power given number of events
        calc_type = "power"
        # Solve for z_beta from: events = (z_alpha + z_beta)^2 * (1+r)^2 / (r * log_hr^2)
        # z_beta = sqrt(events * r * log_hr^2 / (1+r)^2) - z_alpha
        z_beta = math.sqrt(request.n_events * r * log_hr**2 / (1 + r)**2) - z_alpha
        result = stats.norm.cdf(z_beta)  # Convert z to power
        result = max(0, min(1, result))  # Clamp to [0, 1]
        
        interpretation = (
            f"With {request.n_events} events and HR={request.hazard_ratio:.2f}, "
            f"you have {result*100:.1f}% power to detect a significant difference."
        )
    else:
        # Calculate sample size given power
        calc_type = "sample_size"
        power = request.power if request.power is not None else 0.8
        z_beta = stats.norm.ppf(power)
        
        # Schoenfeld formula for events
        events_needed = (z_alpha + z_beta)**2 * (1 + r)**2 / (r * log_hr**2)
        
        # Convert to sample size
        sample_size = events_needed / request.p1
        result = sample_size
        
        interpretation = (
            f"To detect HR={request.hazard_ratio:.2f} with {power*100:.0f}% power, "
            f"you need {int(events_needed)} events "
            f"({int(sample_size)} total subjects assuming {request.p1*100:.0f}% event rate)."
        )
    
    return PowerResponse(
        calculation_type=calc_type,
        result=result,
        parameters={
            "hazard_ratio": request.hazard_ratio,
            "p1": request.p1,
            "alpha": request.alpha,
            "power": request.power,
            "n_events": request.n_events,
        },
        interpretation=interpretation,
        assumptions=[
            "Proportional hazards",
            "Non-informative censoring",
            "Exponential survival times",
        ],
    )


@router.post("/effect-size")
async def calculate_effect_size(request: EffectSizeRequest):
    """
    🔢 Calculate effect size from raw data.
    
    Converts means/proportions to standardized effect sizes.
    """
    import math
    
    result = {}
    
    if request.test_type == "ttest":
        if all([request.mean1, request.mean2, request.std]):
            d = (request.mean1 - request.mean2) / request.std
            result = {
                "cohens_d": abs(d),
                "interpretation": "small" if abs(d) < 0.5 else "medium" if abs(d) < 0.8 else "large",
            }
    
    elif request.test_type == "proportion":
        if request.p1 is not None and request.p2 is not None:
            h = 2 * (math.asin(math.sqrt(request.p1)) - math.asin(math.sqrt(request.p2)))
            result = {
                "cohens_h": abs(h),
                "absolute_difference": abs(request.p1 - request.p2),
                "relative_risk": request.p2 / request.p1 if request.p1 > 0 else None,
                "interpretation": "small" if abs(h) < 0.5 else "medium" if abs(h) < 0.8 else "large",
            }
    
    return {
        "test_type": request.test_type,
        "effect_size": result,
    }


@router.get("/guidelines")
async def get_power_guidelines():
    """
    📋 Get power analysis guidelines and effect size conventions.
    """
    return {
        "general_guidelines": {
            "recommended_power": "0.80 (80%) is standard, 0.90 for confirmatory studies",
            "alpha": "0.05 for most studies, 0.01 for multiple comparisons",
            "effect_size": "Use pilot data or literature; avoid 'medium' without justification",
        },
        "effect_size_conventions": {
            "cohens_d": {
                "test": "Independent t-test",
                "small": 0.2,
                "medium": 0.5,
                "large": 0.8,
                "formula": "d = (M1 - M2) / SD_pooled",
            },
            "cohens_h": {
                "test": "Two proportions",
                "small": 0.2,
                "medium": 0.5,
                "large": 0.8,
                "formula": "h = 2*arcsin(√p1) - 2*arcsin(√p2)",
            },
            "cohens_f": {
                "test": "ANOVA",
                "small": 0.10,
                "medium": 0.25,
                "large": 0.40,
                "formula": "f = σ_between / σ_within",
            },
            "cohens_w": {
                "test": "Chi-square",
                "small": 0.10,
                "medium": 0.30,
                "large": 0.50,
                "formula": "w = √(Σ(O-E)²/E / N)",
            },
        },
        "survival_guidelines": {
            "hazard_ratio": {
                "clinically_meaningful": "Usually HR ≤ 0.75 or HR ≥ 1.33",
                "small": "HR = 0.90 or 1.11",
                "medium": "HR = 0.75 or 1.33",
                "large": "HR = 0.50 or 2.00",
            },
            "median_survival_ratio": "Alternative: ratio of median survival times",
        },
        "common_mistakes": [
            "Using 'medium' effect size without clinical justification",
            "Ignoring dropout/attrition in sample size",
            "Not accounting for multiple comparisons",
            "Confusing total N with per-group N",
        ],
    }
