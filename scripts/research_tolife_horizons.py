#!/usr/bin/env python3
"""Corrected TOLIFE 24/48/72h probes from v1 processed data -> platform research artifacts."""
import os, sys, json
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import GroupKFold
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss, log_loss

ROOT = Path(os.environ.get('RESEARCH_ROOT', 'external-research/pranaguard-unified-copd-dataset'))
SCRIPT_DIR = Path(__file__).resolve().parent
OUT = Path(os.environ.get('RESEARCH_OUT', SCRIPT_DIR.parent/'backend'/'app'/'research'/'artifacts')); OUT.mkdir(parents=True, exist_ok=True)
SEED = 20261108
CHANNELS = ['bri_night_mean','hr_sleep_mean','ppg_hr_mean','ppg_stdrr_ms','ppg_rmssd_ms',
            'fev1_session_L','pef_session_Lmin','spo2_daily','hr_session','sleep_hours',
            'sleep_efficiency','waso_hours','gait_speed','walked_time_min','walked_dist_m',
            'env_aqi_mean','env_temp_mean','env_humidity_mean']

def main():
    day = pd.read_parquet(ROOT/'data/processed/physiological_timeseries/tolife_patient_day.parquet')
    day['day'] = pd.to_datetime(day['day'])
    day = day.sort_values(['participant_id','day']).reset_index(drop=True)
    ex = pd.read_csv(ROOT/'data/processed/clinical_events/tolife_exacerbations.csv')
    kits = pd.read_csv(ROOT/'data/processed/patient_profiles/tolife_patients.csv')
    day_w = day.groupby('participant_id').agg(first=('day','min'), last=('day','max'))
    days_by_pid = day.assign(d=day['day'].dt.strftime('%Y-%m-%d')).groupby('participant_id')['d'].apply(set).to_dict()  # string day keys for the validity audit
    kits_w = kits.set_index('participant_id')[['first_day','last_day']].dropna(how='any')
    ev_rows = []
    for _, r in ex.iterrows():
        p, ev = r['participant_id'], str(r['event_date'])
        kw = kits_w.loc[p] if p in kits_w.index else None
        in_device = kw is not None and kw['first_day'] <= ev <= kw['last_day']
        dw = day_w.loc[p] if p in day_w.index else None
        in_frame = dw is not None and str(dw['first'].date()) <= ev <= str(dw['last'].date())
        prior = sum(1 for dd in range(1,8) if (pd.Timestamp(ev)-pd.Timedelta(days=dd)).strftime('%Y-%m-%d') in days_by_pid.get(p,set()))
        ev_rows.append({'participant_id':p,'event_date':ev,'in_device_window':bool(in_device),
                        'in_observed_frame':bool(in_frame),'valid_days_in_prior_7d':int(prior)})
    audit = {'summary':{
        'total_entries':int(len(ex)),'unique_participants':int(ex.participant_id.nunique()),
        'missing_dates':int(ex.event_date.isna().sum()),
        },'events':ev_rows}
    ins_d=sum(e['in_device_window'] for e in ev_rows); ins_f=sum(e['in_observed_frame'] for e in ev_rows)
    audit['summary']['device_window']={'inside':int(ins_d),'outside':int(len(ex)-ins_d)}
    audit['summary']['observed_frame']={'inside':int(ins_f),'outside':int(len(ex)-ins_f)}
    audit['summary']['events_with_valid_measurements_in_prior_7d']=int(sum(e['valid_days_in_prior_7d']>0 for e in ev_rows))
    audit['summary']['in_frame_events_with_prior_7d_measurements']=int(sum(1 for e in ev_rows if e['in_observed_frame'] and e['valid_days_in_prior_7d']>0))
    audit['summary']['note']='Counts reconciled: prior-7d validity is computed against observed participant-days only; many register events fall outside any device/observed window.'
    (OUT/'event_register_audit.json').write_text(json.dumps(audit, indent=1))

    # corrected features (prior-day only; in-frame events only)
    ex_map = {}
    for e in ev_rows:
        if e['in_observed_frame']:
            ex_map.setdefault(e['participant_id'], []).append(pd.Timestamp(e['event_date']))
    parts = []
    for pid, g in day.groupby('participant_id'):
        g = g.sort_values('day').reset_index(drop=True)
        hist = g[CHANNELS].astype(float).shift(1)
        g['measured_channels_prev_day'] = hist.notna().sum(axis=1)
        for ch in CHANNELS:
            v = hist[ch]
            bl = v.rolling(7, min_periods=3).mean()
            g[f'{ch}_d_lag1_bl7'] = v - bl
            g[f'{ch}_miss7'] = 7 - v.notna().rolling(7, min_periods=1).sum()
        evs = ex_map.get(pid, [])
        for hname, hlen in (('24',1),('48',2),('72',3)):
            flag = np.zeros(len(g), dtype=int)
            for ev in evs:
                in_win = (g['day'] >= ev - pd.Timedelta(days=hlen-1)) & (g['day'] <= ev)
                flag = np.maximum(flag, in_win.astype(int))  # day d in [ev-h+1, ev] <=> event within [d, d+h-1]
            g[f'exac_next_{hname}h'] = flag
        parts.append(g)
    feats = pd.concat(parts, ignore_index=True)
    FEATS = [c for c in feats.columns if c.endswith('_d_lag1_bl7')] + \
            [c for c in feats.columns if c.endswith('_miss7')] + ['measured_channels_prev_day']

    def probe(horizon):
        y = feats[f'exac_next_{horizon}h'].values
        X = feats[FEATS].astype(float).replace([np.inf,-np.inf], np.nan)
        mask = X['measured_channels_prev_day'] >= 1
        Xs = feats[mask][FEATS].astype(float).replace([np.inf,-np.inf], np.nan)
        Xv = np.nan_to_num(feats[mask][FEATS].astype(float).replace([np.inf,-np.inf], np.nan).values, nan=0.0)
        yv = y[mask.values]; gv = feats[mask]['participant_id'].values
        probs = np.full(len(yv), np.nan)
        for pid in np.unique(gv):
            te = gv == pid; tr = ~te
            if yv[tr].sum() == 0 or yv[tr].sum() == tr.sum(): continue
            clf = make_pipeline(StandardScaler(), LogisticRegression(max_iter=800, C=0.5, class_weight='balanced'))
            clf.fit(Xv[tr], yv[tr])
            probs[te] = clf.predict_proba(Xv[te])[:,1]
        valid = ~np.isnan(probs)
        y2, p2, g2 = yv[valid], probs[valid], gv[valid]
        rng = np.random.default_rng(SEED)
        uniq = np.unique(g2); idx = {u: np.where(g2==u)[0] for u in uniq}
        def ci(fn):
            s=[]
            for _ in range(300):
                sel = np.concatenate([idx[u] for u in rng.choice(uniq, len(uniq), replace=True)])
                if y2[sel].std()==0: continue
                s.append(fn(y2[sel], p2[sel]))
            return [round(float(np.percentile(s,2.5)),4), round(float(np.percentile(s,97.5)),4)]
        res = {
          'horizon_hours': int(horizon),
          'definition': f'day d positive iff register event begins in [today d, d+{horizon//24-1}] using only days <= d-1 features',
          'prediction_cutoff': 'after previous-day measurements (strictly prior-day features)',
          'n_eval_days': int(len(y2)), 'n_positive_days': int(y2.sum()),
          'prevalence': float(y2.mean()),
          'n_participants': int(len(uniq)),
          'n_participants_with_positive': int((feats[mask].groupby('participant_id')[f'exac_next_{horizon}h'].sum()>0).sum()),
          'n_independent_register_events_in_frame': int(sum(feats[mask].groupby('participant_id')[f'exac_next_{horizon}h'].max()>0)),
          'auroc': float(roc_auc_score(y2, p2)), 'auroc_ci': ci(roc_auc_score),
          'auprc': float(average_precision_score(y2, p2)), 'auprc_ci': ci(average_precision_score),
          'brier': float(brier_score_loss(y2, p2)),
          'log_loss': float(log_loss(y2, np.clip(p2,1e-7,1-1e-7))),
        }
        return res

    results = {str(h): probe(h) for h in (24, 48, 72)}
    (OUT/'tolife_horizon_results.json').write_text(json.dumps({
        'experiment': 'tolife_exacerbation_horizons_v2', 'protocol': 'LOGO patient-level; prior-day-only features; in-frame events only; model-estimate symptom classes excluded; seed 20261108',
        'results': results}, indent=1))
    print(json.dumps(results, indent=1))

if __name__ == '__main__':
    main()
