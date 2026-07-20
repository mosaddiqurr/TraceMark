export type JobState = "queued" | "running" | "completed" | "failed" | "cancelled";
export type WatermarkType = "visible" | "lsb" | "robust" | "combined";
export type EvidenceClassification =
  | "exact_registered_hash"
  | "valid_distribution_watermark"
  | "valid_ownership_watermark"
  | "invalid_authenticated_payload"
  | "calibrated_visual_derivative"
  | "possible_visual_match"
  | "no_evidence"
  | "inconclusive";

export interface User { id: string; email: string; display_name: string; role: "user" | "admin" }
export interface SessionResponse { user: User; csrf_token: string }
export interface Page<T> { items: T[]; total?: number; next_cursor?: string | null }
export interface Job {
  id: string;
  state: JobState;
  stage: string;
  progress: number;
  cancellable: boolean;
  created_at: string;
  updated_at: string;
  result_url?: string | null;
  error?: { code: string; message: string } | null;
}
export interface Asset {
  id: string;
  name: string;
  media_type: string;
  width: number;
  height: number;
  size_bytes: number;
  created_at: string;
  thumbnail_url?: string;
}
export interface Distribution {
  id: string;
  asset_id: string;
  recipient_label: string;
  reference?: string;
  created_at: string;
  download_url?: string;
}
export interface Collection { id: string; name: string; item_count: number; updated_at: string; state?: JobState }
export interface Report { id: string; kind: "verification" | "benchmark"; title: string; created_at: string; formats: string[] }
export interface Scan { id: string; url: string; state: JobState; candidate_count: number; match_count: number; created_at: string }
export interface BenchmarkResult { transformation: string; parameter: string; robust_detected: boolean; lsb_detected: boolean; ssim?: number; psnr?: number }
export interface BenchmarkRun { id: string; name: string; profile: string; state: JobState; created_at: string; results?: BenchmarkResult[] }
export interface DashboardSummary {
  asset_count: number;
  protected_count: number;
  collection_count: number;
  active_job_count: number;
  recent_jobs: Job[];
}
export interface Evidence {
  id: string;
  classification: EvidenceClassification;
  created_at: string;
  exact_hash_match: boolean;
  watermark?: { valid: boolean; type?: WatermarkType; repetitions_found?: number; corrected_symbols?: number };
  visual?: { phash_distance?: number; orb_matches?: number; ransac_inliers?: number; homography_valid?: boolean };
  provenance?: { state: string; detail?: string };
}
