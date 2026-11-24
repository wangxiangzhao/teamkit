from pathlib import Path
import pytest
from teamkit.metrics import roas_csv


def test_long_mature_cohort_does_not_use_d45_as_d30(tmp_path):
    f=tmp_path/'cohorts.csv'
    f.write_text(
        'cohort,spend,revenue,days_observed,currency\n'
        'A,100,120,30,USD\n'
        'B,200,400,45,USD\n'
    )
    result=roas_csv(f,window=30)
    assert result['complete_cohorts']==1
    assert result['aggregate_roas']=='1.200000'
    assert result['cohorts'][1]['excluded_reason']=='revenue_not_at_requested_window'


def test_explicit_d30_revenue_for_old_cohort_is_eligible(tmp_path):
    f=tmp_path/'cohorts.csv'
    f.write_text(
        'cohort,spend,revenue,days_observed,currency,revenue_as_of_day\n'
        'A,100,120,45,USD,30\n'
    )
    result=roas_csv(f,window=30)
    assert result['complete_cohorts']==1
    assert result['aggregate_roas']=='1.200000'


def test_reject_nan_and_untrusted_as_of(tmp_path):
    f=tmp_path/'cohorts.csv'
    f.write_text('cohort,spend,revenue,days_observed,currency\nA,NaN,30,30,USD\n')
    with pytest.raises(ValueError):
        roas_csv(f)
    f.write_text('cohort,spend,revenue,days_observed,currency,revenue_as_of_day\nA,10,30,30,USD,40\n')
    with pytest.raises(ValueError):
        roas_csv(f)


def test_profit_and_revenue_per_user_use_eligible_cohort_totals(tmp_path):
    path = tmp_path / "cohorts.csv"
    path.write_text(
        "cohort,spend,revenue,days_observed,currency,other_costs,acquired_users\n"
        "A,100,120,30,USD,10,10\n"
        "B,200,190,30,USD,20,30\n"
        "C,800,900,45,USD,,\n"
    )
    result = roas_csv(path)
    assert result["aggregate_profit"] == "-20"
    assert result["aggregate_revenue_per_acquired_user"] == "7.750000"
    assert result["cohorts"][0]["d_window_profit"] == "10"
    assert result["cohorts"][2]["d_window_profit"] is None


def test_profit_and_revenue_per_user_do_not_impute_missing_inputs(tmp_path):
    path = tmp_path / "cohorts.csv"
    path.write_text(
        "cohort,spend,revenue,days_observed,currency,other_costs,acquired_users\n"
        "A,100,120,30,USD,0,10\n"
        "B,50,60,30,USD,,\n"
    )
    result = roas_csv(path)
    assert result["aggregate_roas"] == "1.200000"
    assert result["aggregate_profit"] is None
    assert result["aggregate_revenue_per_acquired_user"] is None
