/** Types for the external Research Models module (v7). These models are never merged with the production Digital Twin. */

export interface RegistryModel{
  model_id:string;model_display_name:string;model_kind:string;version:string;
  dataset_source:string;task_type:string;
  feature_schema:Record<string,unknown>;preprocessing:Record<string,unknown>;
  artifact_path:string|null;inference_method:string;
  supported_outputs:string[];evaluation:Record<string,unknown>;limitations:string[];
  provenance_evidence_class:string;registered_at:string;updated_at:string;
}
export interface RegistryResponse{models:RegistryModel[];count:number;}

export interface CoughTestMetrics{
  auroc:number;auprc:number;prevalence_copd:number;accuracy:number;f1_copd:number;
  sensitivity_copd:number;specificity:number;precision_copd:number;brier:number;log_loss:number;
  confusion:{tn:number;fp:number;fn:number;tp:number}|number[][];
}
export interface CoughInfo{
  model_id:string;version:string;features:string[];feature_version:string;
  dataset:string;protocol:string;
  train:{n:number;COPD:number;Healthy:number};test:{n:number;COPD:number;Healthy:number};
  test_metrics:CoughTestMetrics;limitations:string[];
  global_feature_importance:{feature:string;importance:number}[];
  global_feature_importance_note:string;runtime_environment:string;
  inference_available:boolean;inference_note?:string;
}
export interface CoughPrediction{
  model_id:string;model_version:string;class_label:string;p_copd:number;p_healthy:number;
  threshold:number;audio:{duration_s:number;samplerate_hz:number};input_hash:string;
  evidence:string;disclaimer:string;
}
export interface CoughHistory{
  predictions:{id:number;model_id:string;version:string;input_hash:string;
    input_summary:{audio:{duration_s:number;samplerate_hz:number};filename:string};
    output:{class_label:string;p_copd:number};evidence_class:string;created_at:string}[];
  count:number;
}

export interface HorizonResult{
  horizon_hours:number;definition:string;prediction_cutoff:string;n_eval_days:number;
  n_positive_days:number;prevalence:number;n_participants:number;
  n_participants_with_positive:number;n_independent_register_events_in_frame:number;
  auroc:number|null;auroc_ci:[number,number]|null;auprc:number|null;
  auprc_ci:[number,number]|null;brier:number|null;log_loss:number|null;
}
export interface TolifeOverview{
  model_id:string;dataset:string;
  event_audit:{
    total_entries:number;unique_participants:number;missing_dates:number;
    device_window:{inside:number;outside:number};
    observed_frame:{inside:number;outside:number};
    events_with_valid_measurements_in_prior_7d:number;
    in_frame_events_with_prior_7d_measurements:number;note:string;
  };
  horizons:Record<string,HorizonResult>;
  corrected_experiment_note:string;framing:string;
}
export interface SeriesPoint{rel_day:number;median:number|null;q1:number|null;q3:number|null;n:number;}
export interface TolifeSeries{
  series:Record<string,SeriesPoint[]>;
  n_in_frame_events:number;rel_day_definition:string;channels_note:string;
  severity_of_in_frame_events:string[];
}
export interface TolifeParticipant{
  participant_id:string;country:string;monitoring_days:number;first_day:string;last_day:string;
  n_register_exacerbations:number;coverage_days:number;n_fev1:number;n_hr:number;n_sleep:number;n_env:number;
}
export interface TolifeParticipants{participants:TolifeParticipant[];count:number;identity_note:string;}
