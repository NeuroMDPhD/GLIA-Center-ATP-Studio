import numpy as np
import pytest
from atp_studio.metrics import quantify

def vox(start,end,y=2,x=3): return np.array([[i,y,x] for i in range(start,end+1)])

def test_triangular_event_physical_units():
    t=np.arange(21)*.5;y=np.maximum(0,1-np.abs(t-5)/2)
    m=quantify(y,vox(6,14),t,(21,8,8),2,3,(0,20),drug_s=2)
    assert m['peak_dff']==1 and m['area_um2']==6
    assert m['fwhm_s']==pytest.approx(2)
    assert m['auc_signed_dff_s']==pytest.approx(2)
    assert m['rise_10_90_s']==pytest.approx(1.6)
    assert m['fall_90_10_s']==pytest.approx(1.6)
    assert m['onset_from_drug_s']==1

def test_censored_crossing_is_not_fabricated():
    t=np.arange(20);y=np.linspace(.7,1,20)
    m=quantify(y,vox(0,19,y=0),t,(20,8,8),1,1,(0,19))
    assert m['fwhm_s'] is None and m['decay_tau_s'] is None
    assert m['starts_at_recording_start'] and m['ends_at_recording_end'] and m['touches_analysis_edge']

def test_known_exponential_decay():
    t=np.arange(100)*.25;y=np.where(t<3,t/3,np.exp(-(t-3)/2))
    m=quantify(y,vox(1,80),t,(100,8,8),1,1,(0,99))
    assert m['decay_tau_s']==pytest.approx(2,rel=.02)
    assert m['decay_fit_r2']>.999

def test_invalid_coordinates_fail():
    with pytest.raises(ValueError):quantify(np.zeros(10),vox(0,10),np.arange(10),(10,4,4),1,1)

def test_nonfinite_trace_does_not_generate_valid_metrics():
    y=np.zeros(20);y[8]=np.nan
    m=quantify(y,vox(5,10),np.arange(20),(20,8,8),1,1,(0,19))
    assert m['peak_dff'] is None and 'nonfinite_trace' in m['qc_flags']
