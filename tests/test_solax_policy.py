"""Tests for the Solax start/stop policy (no Home Assistant needed)."""
import importlib.util
import sys
from pathlib import Path

_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components/solar_ev_charger/charger/solax_policy.py"
)
_spec = importlib.util.spec_from_file_location("solax_policy", _PATH)
solax_policy = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = solax_policy
_spec.loader.exec_module(solax_policy)

SolaxStartStopPolicy = solax_policy.SolaxStartStopPolicy

MIN_SOC = 90


def decide(policy, now, active, target, soc=95.0, battery=0.0):
    return policy.decide(now, active, target, soc, battery, MIN_SOC)


def test_start_waits_for_smoothing_period():
    policy = SolaxStartStopPolicy(smoothing_period=30)
    assert decide(policy, 0, False, 8) is False
    assert decide(policy, 29, False, 8) is False
    assert decide(policy, 30, False, 8) is True


def test_short_surplus_does_not_start():
    policy = SolaxStartStopPolicy(smoothing_period=30)
    assert decide(policy, 0, False, 8) is False
    assert decide(policy, 10, False, 0) is False
    assert decide(policy, 20, False, 8) is False
    assert decide(policy, 45, False, 8) is False
    assert decide(policy, 50, False, 8) is True


def test_stop_waits_for_smoothing_period():
    policy = SolaxStartStopPolicy(smoothing_period=30)
    assert decide(policy, 0, True, 0) is True
    assert decide(policy, 29, True, 0) is True
    assert decide(policy, 30, True, 0) is False


def test_zero_smoothing_is_immediate():
    policy = SolaxStartStopPolicy(smoothing_period=0)
    assert decide(policy, 0, False, 8) is True
    assert decide(policy, 1, True, 0) is False


def test_below_min_soc_starts_only_while_battery_charges():
    policy = SolaxStartStopPolicy(smoothing_period=0)
    assert decide(policy, 0, False, 8, soc=80, battery=-50) is False
    assert decide(policy, 1, False, 8, soc=80, battery=None) is False
    assert decide(policy, 2, False, 8, soc=80, battery=2000) is True


def test_discharge_below_min_soc_latches_until_soc_recovers():
    policy = SolaxStartStopPolicy(smoothing_period=30)
    assert decide(policy, 0, True, 6, soc=85, battery=-500) is True
    assert decide(policy, 29, True, 6, soc=85, battery=-500) is True
    assert decide(policy, 30, True, 6, soc=85, battery=-500) is False
    assert policy.latched

    # Boiler switches off: surplus and battery charging come back, still latched.
    assert decide(policy, 100, False, 10, soc=86, battery=1500) is False
    assert decide(policy, 500, False, 10, soc=89, battery=1500) is False

    # SOC reaches the minimum: latch clears, normal debounced start.
    assert decide(policy, 600, False, 10, soc=90, battery=1500) is False
    assert not policy.latched
    assert decide(policy, 630, False, 10, soc=90, battery=1500) is True


def test_discharge_blip_does_not_latch():
    policy = SolaxStartStopPolicy(smoothing_period=30)
    assert decide(policy, 0, True, 6, soc=85, battery=-500) is True
    assert decide(policy, 20, True, 6, soc=85, battery=300) is True
    assert decide(policy, 40, True, 6, soc=85, battery=-500) is True
    assert decide(policy, 60, True, 6, soc=85, battery=-500) is True
    assert not policy.latched


def test_discharge_above_min_soc_does_not_latch():
    policy = SolaxStartStopPolicy(smoothing_period=30)
    assert decide(policy, 0, True, 6, soc=95, battery=-800) is True
    assert decide(policy, 60, True, 6, soc=95, battery=-800) is True
    assert not policy.latched
