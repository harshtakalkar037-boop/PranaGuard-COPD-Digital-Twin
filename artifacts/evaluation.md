# Executed model evaluation

ALL patient data and outcomes are synthetic. Row-wise metrics use correlated hourly windows. No clinical validation; generator learnability is not clinical performance.

| Model / ablation | Horizon | AUROC | AUPRC | Brier | Positive hours / test hours |
|---|---:|---:|---:|---:|---:|
| LogisticRegression / personalized | 24h | 0.6619 | 0.1993 | 0.0260 | 136 / 4699 |
| LogisticRegression / personalized | 48h | 0.6285 | 0.1841 | 0.0537 | 260 / 4699 |
| LogisticRegression / personalized | 72h | 0.6253 | 0.2281 | 0.0800 | 363 / 4699 |
| LightGBM / static_only | 24h | 0.2688 | 0.0214 | 0.0292 | 136 / 4699 |
| LightGBM / static_only | 48h | 0.2246 | 0.0390 | 0.0565 | 260 / 4699 |
| LightGBM / static_only | 72h | 0.2197 | 0.0550 | 0.0816 | 363 / 4699 |
| LightGBM / body_stream | 24h | 0.6242 | 0.0408 | 0.0294 | 136 / 4699 |
| LightGBM / body_stream | 48h | 0.6160 | 0.0688 | 0.0561 | 260 / 4699 |
| LightGBM / body_stream | 72h | 0.6358 | 0.1086 | 0.0815 | 363 / 4699 |
| LightGBM / full_environment | 24h | 0.6991 | 0.0676 | 0.0282 | 136 / 4699 |
| LightGBM / full_environment | 48h | 0.6613 | 0.0939 | 0.0558 | 260 / 4699 |
| LightGBM / full_environment | 72h | 0.3119 | 0.0514 | 0.0816 | 363 / 4699 |
| LightGBM / personalized | 24h | 0.6916 | 0.0882 | 0.0279 | 136 / 4699 |
| LightGBM / personalized | 48h | 0.6144 | 0.0968 | 0.0557 | 260 / 4699 |
| LightGBM / personalized | 72h | 0.3951 | 0.0593 | 0.0853 | 363 / 4699 |

Lead-time audit: `{"test_onsets": 5, "detected_onsets": 0, "median_hours_detected": null, "rule": "Earliest 72h risk >=0.35 in the prior72h among eligible TEST rows only. Undetected events excluded from median; boundary-truncated windows possible. Descriptive synthetic result."}`

Protocol: `{"patient_ids": {"train": ["PG-0001", "PG-0002", "PG-0003", "PG-0004", "PG-0005", "PG-0006", "PG-0007", "PG-0008", "PG-0009", "PG-0010", "PG-0011", "PG-0012", "PG-0013", "PG-0014", "PG-0015", "PG-0016", "PG-0017", "PG-0018", "PG-0019", "PG-0020", "PG-0021", "PG-0022", "PG-0023", "PG-0024", "PG-0025", "PG-0026", "PG-0027", "PG-0028", "PG-0029", "PG-0030", "PG-0031", "PG-0032", "PG-0033", "PG-0034", "PG-0035", "PG-0036", "PG-0037", "PG-0038", "PG-0039", "PG-0040", "PG-0041", "PG-0042", "PG-0043", "PG-0044", "PG-0045", "PG-0046", "PG-0047", "PG-0048", "PG-0049", "PG-0050", "PG-0051", "PG-0052", "PG-0053", "PG-0054", "PG-0055", "PG-0056", "PG-0057", "PG-0058", "PG-0059", "PG-0060", "PG-0061", "PG-0062", "PG-0063", "PG-0064", "PG-0065", "PG-0066", "PG-0067", "PG-0068", "PG-0069", "PG-0070", "PG-0071", "PG-0072"], "calibration": ["PG-0073", "PG-0074", "PG-0075", "PG-0076", "PG-0077", "PG-0078", "PG-0079", "PG-0080", "PG-0081", "PG-0082", "PG-0083", "PG-0084", "PG-0085", "PG-0086", "PG-0087", "PG-0088", "PG-0089", "PG-0090", "PG-0091", "PG-0092", "PG-0093", "PG-0094", "PG-0095", "PG-0096"], "test": ["PG-0097", "PG-0098", "PG-0099", "PG-0100", "PG-0101", "PG-0102", "PG-0103", "PG-0104", "PG-0105", "PG-0106", "PG-0107", "PG-0108", "PG-0109", "PG-0110", "PG-0111", "PG-0112", "PG-0113", "PG-0114", "PG-0115", "PG-0116", "PG-0117", "PG-0118", "PG-0119", "PG-0120"]}, "hour_bounds": {"train_end_exclusive": 748, "cal_start": 849, "cal_end_exclusive": 1051, "test_start": 1152, "test_end_exclusive": 1368}, "protocol": "Patient-disjoint and calendar-time disjoint; >=72h purge between partitions; first72h baseline only.", "fit_stride": 3, "threshold": 0.35, "feature_names": ["age", "fev1_pct", "prior_exacerbations", "smoking_pack_years", "bmi", "spo2", "heart_rate", "resp_rate", "symptom_score", "adherence", "steps", "sleep_hours", "spo2_mean6", "hr_mean6", "rr_mean6", "symptom_mean6", "spo2_change6", "hr_change6", "adherence_mean24", "pm25", "pm10", "no2", "ozone", "temperature", "humidity", "pm25_mean24", "pm25_change6", "spo2_delta", "hr_delta", "rr_delta", "symptom_delta", "steps_ratio", "spo2_baseline", "hr_baseline", "rr_baseline"], "labels": "New synthetic onset in (t,t+h]; active episodes excluded; full 72h follow-up required.", "rows": {"train_sampled": 14605, "calibration_sampled": 1377, "test_hourly": 4699}, "timestamps": {"train": {"min": "2026-08-04 00:00:00+00:00", "max": "2026-09-01 03:00:00+00:00"}, "calibration": {"min": "2026-09-05 09:00:00+00:00", "max": "2026-09-13 18:00:00+00:00"}, "test": {"min": "2026-09-18 00:00:00+00:00", "max": "2026-09-26 23:00:00+00:00"}}}`