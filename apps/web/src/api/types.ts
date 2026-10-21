export interface Workspace {
  csrf_token: string;
  expires_at: string;
  limits: {
    max_upload_bytes: number;
    max_image_pixels: number;
    max_image_dimension: number;
    output_ttl_seconds: number;
    retention_seconds: number;
  };
}
export interface ImageDetails {
  filename: string;
  width: number;
  height: number;
  size_bytes: number;
  media_type: string;
  sha256: string;
}
export interface Protection {
  identifier: string;
  reference_label: string | null;
  status: "protected";
  file: ImageDetails;
  profile: string;
  quality: Record<string, number | null>;
  created_at: string;
  download_url: string;
  download_expires_at: string;
  trace_expires_at: string;
}
export interface Evidence {
  id: string;
  verified: boolean;
  classification: string;
  created_at: string;
  identifier: string | null;
  reference_label: string | null;
  source_filename: string | null;
  protected_at: string | null;
  file: ImageDetails;
  watermark: {
    authentic: boolean;
    integrity_state: string;
    type: string | null;
    algorithm: string;
    algorithm_version: number | null;
    key_version: number | null;
    repetitions_found: number;
    corrected_symbols: number | null;
    integrity_error: string | null;
  };
  exact_hash: { matched: boolean; kind: "protected_copy" | "source" | null };
  visual: {
    phash_distance: number;
    dhash_distance: number;
    whash_distance: number;
    orb_available: boolean;
    orb_match_count: number | null;
    ransac_inliers: number | null;
    inlier_ratio: number | null;
    homography_valid: boolean | null;
    failure_reason: string | null;
    similar: boolean;
    note: string;
  } | null;
  provenance: { state: string; detail?: string };
  limitations: string[];
  report: { download_url: string; expires_at: string };
  source_url?: string;
}
export interface LinkCheckImage {
  url: string;
  status: "verified" | "checked" | "error";
  classification?: string;
  reference_label?: string | null;
  identifier?: string | null;
  message?: string;
}
export interface LinkCheck {
  source_url: string;
  kind: "image" | "page";
  images: LinkCheckImage[];
  truncated: boolean;
  evidence: Evidence | null;
}
export interface TraceImport {
  imported: number;
  skipped: number;
}
