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
