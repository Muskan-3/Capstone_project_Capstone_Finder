export type TechComfort = "exploring" | "moderate" | "high";

export interface StudentProfile {
  id?: number;
  name: string;
  skills: string[];
  interests: string[];
  tech_comfort: TechComfort | string;
  prior_projects: string;
  preferred_outcome: string;
}

export interface TermDriver {
  term: string;
  contribution: number;
  share: number;
}

export interface RecExplanation {
  cosine_similarity: number;
  feasibility: number;
  feasibility_basis: string;
  composite_score: number;
  weights: Record<string, number>;
  top_term_drivers: TermDriver[];
  routing: {
    mode: string;
    routed_clusters: number[];
    cluster_confidence: number;
    threshold: number;
  };
}

export interface Recommendation {
  rank: number;
  project_id: string;
  title: string;
  statement: string;
  adapted_text: string;
  cluster_id: number;
  cluster_label: string;
  similarity: number;
  composite_score: number;
  feasibility: number;
  confidence_band: "strong" | "moderate" | "weak";
  diversity_note: string;
  explanation: RecExplanation;
  recommendation_id?: number;
}

export interface ClusterDist {
  cluster_id: number;
  label: string;
  similarity: number;
  share: number;
  size: number;
}

export interface RecommendationResponse {
  student_id: number;
  model_version: number | null;
  mode: "routed" | "low_confidence" | "no_signal";
  message: string;
  routed_cluster: number | null;
  routed_clusters: number[];
  cluster_confidence: number;
  cluster_distribution: ClusterDist[];
  scoring_formula: string;
  weights: Record<string, number>;
  faculty_matching_active: boolean;
  faculty_matching_note: string;
  recommendations: Recommendation[];
  refinement?: { negative: string[]; positive: string[] } | null;
}

export interface ProblemStatement {
  id: number;
  project_id: string;
  title: string | null;
  statement: string | null;
  cluster_id: number | null;
  cluster_label: string | null;
  is_flagged: boolean;
  flag_reason: string | null;
  source_batch: string;
  original_project_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface CorpusPage {
  items: ProblemStatement[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ModelVersion {
  version: number;
  corpus_size: number;
  cluster_count: number;
  silhouette: number;
  trained_at: string;
  is_active: boolean;
  notes: string;
  params: Record<string, unknown>;
}

export interface ModelStatus {
  active_version: number | null;
  corpus_size: number;
  active_corpus_size: number;
  flagged_count: number;
  cluster_count: number | null;
  last_trained_at: string | null;
  silhouette: number | null;
  silhouette_by_k: Record<string, number>;
  clusters: { cluster_id: number; label: string; terms: string[]; size: number }[];
  faculty_matching_active: boolean;
  faculty_matching_note: string;
  versions: ModelVersion[];
}

export interface FacultyPreference {
  id: number;
  faculty_name: string;
  domain: string;
  notes: string;
  created_at: string;
}

export interface FacultyPreferenceList {
  items: FacultyPreference[];
  active_in_scoring: boolean;
  note: string;
}
