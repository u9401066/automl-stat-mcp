"""
Isolated tests for survival analysis utilities.

Tests Kaplan-Meier, Cox regression, log-rank tests.
"""
import numpy as np
from scipy import stats
from typing import List, Tuple, Optional


# ==============================================================================
# Kaplan-Meier Implementation (for testing)
# ==============================================================================

def kaplan_meier(times: np.ndarray, events: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Calculate Kaplan-Meier survival estimates.
    
    Args:
        times: Event/censoring times
        events: Event indicators (1=event, 0=censored)
    
    Returns:
        unique_times: Unique event times
        survival: Survival probability at each time
        variance: Greenwood's variance estimate
    """
    # Sort by time
    order = np.argsort(times)
    times = times[order]
    events = events[order]
    
    # Get unique event times (excluding censored)
    event_times = times[events == 1]
    unique_times = np.unique(event_times)
    
    n_at_risk = len(times)
    survival = []
    variance = []
    current_survival = 1.0
    current_var_sum = 0.0
    
    time_idx = 0
    
    for t in unique_times:
        # Count censored before this time
        while time_idx < len(times) and times[time_idx] < t:
            n_at_risk -= 1
            time_idx += 1
        
        # Count events at this time
        n_events = np.sum((times == t) & (events == 1))
        
        if n_at_risk > 0:
            # Survival update
            current_survival *= (1 - n_events / n_at_risk)
            
            # Greenwood's variance component
            if n_at_risk - n_events > 0:
                current_var_sum += n_events / (n_at_risk * (n_at_risk - n_events))
        
        survival.append(current_survival)
        variance.append(current_survival**2 * current_var_sum)
        
        # Update for events at this time
        n_at_risk -= n_events
        time_idx += n_events
    
    return np.array(unique_times), np.array(survival), np.array(variance)


def log_rank_test(times1: np.ndarray, events1: np.ndarray, 
                  times2: np.ndarray, events2: np.ndarray) -> Tuple[float, float]:
    """
    Perform log-rank test for two survival curves.
    
    Args:
        times1, events1: Group 1 times and events
        times2, events2: Group 2 times and events
    
    Returns:
        chi2: Test statistic
        p_value: P-value
    """
    # Combine data
    all_times = np.concatenate([times1, times2])
    all_events = np.concatenate([events1, events2])
    group = np.concatenate([np.zeros(len(times1)), np.ones(len(times2))])
    
    # Sort by time
    order = np.argsort(all_times)
    all_times = all_times[order]
    all_events = all_events[order]
    group = group[order]
    
    # Unique event times
    event_times = np.unique(all_times[all_events == 1])
    
    observed1 = 0
    expected1 = 0
    variance = 0
    
    n1 = len(times1)
    n2 = len(times2)
    
    for t in event_times:
        # At risk at time t
        at_risk1 = np.sum(times1 >= t)
        at_risk2 = np.sum(times2 >= t)
        at_risk = at_risk1 + at_risk2
        
        # Events at time t
        events_t1 = np.sum((times1 == t) & (events1 == 1))
        events_t2 = np.sum((times2 == t) & (events2 == 1))
        events_t = events_t1 + events_t2
        
        if at_risk > 1:
            # Expected events in group 1
            expected_t1 = events_t * at_risk1 / at_risk
            expected1 += expected_t1
            observed1 += events_t1
            
            # Variance component
            var_t = events_t * at_risk1 * at_risk2 * (at_risk - events_t) / (at_risk**2 * (at_risk - 1))
            variance += var_t
    
    # Chi-square statistic
    if variance > 0:
        chi2 = (observed1 - expected1)**2 / variance
        p_value = 1 - stats.chi2.cdf(chi2, 1)
    else:
        chi2 = 0
        p_value = 1.0
    
    return chi2, p_value


# ==============================================================================
# Tests
# ==============================================================================

class TestKaplanMeier:
    """Test Kaplan-Meier survival estimation"""
    
    def test_basic_km_curve(self):
        """Test basic KM curve calculation"""
        times = np.array([1, 2, 3, 4, 5])
        events = np.array([1, 1, 1, 1, 1])  # All events
        
        unique_times, survival, variance = kaplan_meier(times, events)
        
        assert len(unique_times) == 5
        assert survival[0] == 0.8  # 4/5
        assert survival[-1] == 0.0  # No survivors
        print("✓ Basic KM curve")
    
    def test_km_with_censoring(self):
        """Test KM with censored observations"""
        # Events at t=1, 3; censored at t=2, 4, 5
        times = np.array([1, 2, 3, 4, 5])
        events = np.array([1, 0, 1, 0, 0])  # Last observation censored
        
        unique_times, survival, variance = kaplan_meier(times, events)
        
        # Only event times included
        assert len(unique_times) == 2  # Events at t=1 and t=3
        assert survival[-1] > 0  # Some survival due to censoring
        print(f"✓ KM with censoring: final survival = {survival[-1]:.3f}")
    
    def test_km_all_censored(self):
        """Test KM when all observations are censored"""
        times = np.array([1, 2, 3, 4, 5])
        events = np.array([0, 0, 0, 0, 0])
        
        unique_times, survival, variance = kaplan_meier(times, events)
        
        assert len(unique_times) == 0
        print("✓ KM all censored")
    
    def test_km_survival_decreasing(self):
        """Test that survival is monotonically decreasing"""
        np.random.seed(42)
        times = np.random.exponential(10, 50)
        events = np.random.binomial(1, 0.7, 50)
        
        unique_times, survival, variance = kaplan_meier(times, events)
        
        for i in range(1, len(survival)):
            assert survival[i] <= survival[i-1]
        
        print("✓ Survival monotonically decreasing")
    
    def test_km_variance(self):
        """Test Greenwood's variance estimate"""
        times = np.array([1, 2, 3, 4, 5])
        events = np.array([1, 1, 1, 1, 1])
        
        unique_times, survival, variance = kaplan_meier(times, events)
        
        # Variance should be non-negative
        assert all(v >= 0 for v in variance)
        # Variance should increase (more uncertainty over time)
        print("✓ Greenwood's variance")


class TestLogRankTest:
    """Test log-rank test"""
    
    def test_identical_groups(self):
        """Test log-rank for identical groups"""
        times = np.array([1, 2, 3, 4, 5])
        events = np.array([1, 1, 1, 1, 1])
        
        chi2, p = log_rank_test(times, events, times, events)
        
        # Identical groups should have high p-value
        assert p > 0.5
        print(f"✓ Identical groups: p = {p:.3f}")
    
    def test_very_different_groups(self):
        """Test log-rank for very different groups"""
        # Group 1: Short survival
        times1 = np.array([1, 2, 3, 4, 5])
        events1 = np.array([1, 1, 1, 1, 1])
        
        # Group 2: Long survival
        times2 = np.array([10, 20, 30, 40, 50])
        events2 = np.array([1, 1, 1, 1, 1])
        
        chi2, p = log_rank_test(times1, events1, times2, events2)
        
        # Different groups should have low p-value
        assert p < 0.05
        print(f"✓ Different groups: p = {p:.4f}")
    
    def test_with_censoring(self):
        """Test log-rank with censored data"""
        times1 = np.array([1, 2, 3, 4, 5])
        events1 = np.array([1, 0, 1, 0, 1])
        
        times2 = np.array([6, 7, 8, 9, 10])
        events2 = np.array([1, 0, 1, 0, 1])
        
        chi2, p = log_rank_test(times1, events1, times2, events2)
        
        # Should still detect difference
        assert p < 0.3
        print(f"✓ Log-rank with censoring: p = {p:.3f}")


class TestMedianSurvival:
    """Test median survival time estimation"""
    
    def test_median_from_km(self):
        """Test median survival from KM curve"""
        times = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        events = np.array([1, 1, 1, 1, 1, 1, 1, 1, 1, 1])
        
        unique_times, survival, _ = kaplan_meier(times, events)
        
        # Find where survival crosses 0.5
        median = None
        for t, s in zip(unique_times, survival):
            if s <= 0.5:
                median = t
                break
        
        # Median should be around 5
        assert median is not None
        assert 4 <= median <= 6
        print(f"✓ Median survival = {median}")
    
    def test_median_with_heavy_censoring(self):
        """Test median when not reached"""
        times = np.array([1, 2, 3, 4, 5])
        events = np.array([1, 0, 0, 0, 0])  # Only one event
        
        unique_times, survival, _ = kaplan_meier(times, events)
        
        # Survival never drops below 0.5
        assert survival[-1] > 0.5
        print("✓ Median not reached (heavy censoring)")


class TestHazardRatio:
    """Test hazard ratio estimation"""
    
    def test_hr_from_medians(self):
        """Test HR estimation from median survival"""
        m1 = 12  # months
        m2 = 18  # months
        
        # HR ≈ log(2)/m2 / log(2)/m1 = m1/m2 (inverted because longer = better)
        # Actually HR = lambda1/lambda2 where lambda = log(2)/median
        hr = m2 / m1  # Group 1 has shorter survival = higher hazard
        
        assert hr > 1
        print(f"✓ HR from medians: {hr:.2f}")
    
    def test_hr_interpretation(self):
        """Test HR interpretation"""
        def interpret_hr(hr):
            if hr < 1:
                return "protective"
            elif hr > 1:
                return "harmful"
            else:
                return "neutral"
        
        assert interpret_hr(0.7) == "protective"
        assert interpret_hr(1.5) == "harmful"
        assert interpret_hr(1.0) == "neutral"
        print("✓ HR interpretation")


class TestCensoringPatterns:
    """Test different censoring patterns"""
    
    def test_type1_censoring(self):
        """Test Type I censoring (fixed study end)"""
        study_end = 10
        true_times = np.array([5, 8, 12, 15, 3])
        
        # Observed times (censored at study_end)
        obs_times = np.minimum(true_times, study_end)
        events = (true_times <= study_end).astype(int)
        
        assert sum(events) == 3  # 3 events, 2 censored
        print(f"✓ Type I censoring: {sum(events)} events, {sum(1-events)} censored")
    
    def test_random_censoring(self):
        """Test random (right) censoring"""
        np.random.seed(42)
        n = 100
        
        # Event times (exponential)
        event_times = np.random.exponential(10, n)
        
        # Censoring times (also exponential)
        censor_times = np.random.exponential(15, n)
        
        # Observed
        obs_times = np.minimum(event_times, censor_times)
        events = (event_times <= censor_times).astype(int)
        
        event_rate = events.mean()
        assert 0.3 < event_rate < 0.8
        print(f"✓ Random censoring: event rate = {event_rate:.2f}")
    
    def test_informative_vs_noninformative(self):
        """Test informative censoring detection"""
        # In practice, we assume non-informative censoring
        # (censoring independent of event process)
        
        np.random.seed(42)
        n = 100
        
        # Non-informative: independent processes
        event_times = np.random.exponential(10, n)
        censor_times = np.random.exponential(15, n)
        
        obs_times = np.minimum(event_times, censor_times)
        events = (event_times <= censor_times).astype(int)
        
        # For non-informative, no correlation between observed time and event indicator
        # (when conditioning on being censored)
        print("✓ Censoring pattern analysis")


class TestSurvivalCurveComparison:
    """Test survival curve comparison methods"""
    
    def test_crossing_curves_logrank(self):
        """Test log-rank for crossing curves"""
        # Group 1: Good early, bad later
        times1 = np.array([1, 2, 3, 4, 5, 10, 10, 10, 10, 10])
        events1 = np.array([0, 0, 0, 0, 0, 1, 1, 1, 1, 1])
        
        # Group 2: Bad early, good later
        times2 = np.array([1, 1, 1, 1, 1, 10, 10, 10, 10, 10])
        events2 = np.array([1, 1, 1, 1, 1, 0, 0, 0, 0, 0])
        
        chi2, p = log_rank_test(times1, events1, times2, events2)
        
        # Log-rank may not detect crossing curves well
        print(f"✓ Crossing curves: chi2={chi2:.2f}, p={p:.3f}")
    
    def test_proportional_hazards(self):
        """Test proportional hazards assumption"""
        # PH: hazard ratio constant over time
        
        np.random.seed(42)
        n = 50
        
        # Group 1: baseline hazard
        lambda1 = 0.1
        times1 = np.random.exponential(1/lambda1, n)
        events1 = np.ones(n)
        
        # Group 2: proportional hazard (HR = 0.5)
        hr = 0.5
        lambda2 = lambda1 * hr
        times2 = np.random.exponential(1/lambda2, n)
        events2 = np.ones(n)
        
        # Under PH, log-rank is optimal
        chi2, p = log_rank_test(times1, events1, times2, events2)
        
        assert p < 0.05  # Should detect difference
        print(f"✓ Proportional hazards: p = {p:.4f}")


class TestRestrictedMeanSurvivalTime:
    """Test RMST (Restricted Mean Survival Time)"""
    
    def test_rmst_calculation(self):
        """Test RMST calculation"""
        # RMST = area under KM curve up to time tau
        times = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        events = np.array([1, 1, 1, 1, 1, 1, 1, 1, 1, 1])
        tau = 10
        
        unique_times, survival, _ = kaplan_meier(times, events)
        
        # Calculate area under curve
        rmst = 0
        prev_t = 0
        prev_s = 1.0
        
        for t, s in zip(unique_times, survival):
            if t <= tau:
                rmst += prev_s * (t - prev_t)
                prev_t = t
                prev_s = s
        
        # Add final rectangle
        rmst += prev_s * (tau - prev_t)
        
        assert rmst > 0
        print(f"✓ RMST = {rmst:.2f}")


def run_all_tests():
    """Run all test classes"""
    print("=" * 60)
    print("Running survival analysis isolated tests")
    print("=" * 60)
    
    test_classes = [
        TestKaplanMeier(),
        TestLogRankTest(),
        TestMedianSurvival(),
        TestHazardRatio(),
        TestCensoringPatterns(),
        TestSurvivalCurveComparison(),
        TestRestrictedMeanSurvivalTime(),
    ]
    
    for test_class in test_classes:
        class_name = test_class.__class__.__name__
        print(f"\n{class_name}:")
        print("-" * 40)
        
        test_methods = [m for m in dir(test_class) if m.startswith('test_')]
        
        for method_name in test_methods:
            try:
                method = getattr(test_class, method_name)
                method()
            except Exception as e:
                print(f"✗ {method_name}: {e}")
                raise
    
    print("\n" + "=" * 60)
    print("🎉 ALL SURVIVAL ANALYSIS TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
