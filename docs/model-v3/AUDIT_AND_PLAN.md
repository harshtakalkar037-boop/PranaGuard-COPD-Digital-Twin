# Second48h improvement attempt: audit and fixed plan

The repeated user request authorizes a new study after the disclosed v2 failure. Work uses a separate copy of the delivered v2 ZIP, not either original repository. Prior models, labels, outcomes, records and failed-study evidence stay unchanged.

Read-only audit found a tiny v2 calibration/threshold cohort, selection uncertainty from very few positive patients, no credible held-out improvement, and a2GB sandbox limit. The new design increases independent patients rather than making synthetic labels easier or repeatedly changing audit seeds.

Before code/data/fits: record separate development/selection/calibration/threshold seeds, bounded candidate list, causal longer-history features, final audit seed, gates and uncertainty. Process patients in chunks and keep data work under cache. Then fit/select/calibrate/cutoff, freeze, and run the single fresh audit. Only integrate if all gates pass; otherwise keep the old model. Add version-aware APIs/UI, real tests/reproduction/build/clean-install/archive checks, and deliver the latest ZIP with honest limitations.

Protocol.json is authoritative. This remains synthetic-generator generalization, not clinical or external validation. Prior unsuccessful attempts are not removed.
