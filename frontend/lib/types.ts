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
    domains: string[];
    source: "keyword" | "classifier" | "unrouted";
    keyword_hits: Record<string, string[]>;
    gate_score: number;
    gate_threshold: number;
    topic_concentration: number | null;
  };
}

export interface Recommendation {
  rank: number;
  project_id: string;
  title: string;
  statement: string;
  adapted_text: string;
  domain: string | null;
  /** internal ranking numbers - sent by the API, never displayed to students */
  similarity: number;
  composite_score: number;
  feasibility: number;
  diversity_note: string;
  explanation: RecExplanation;
  recommendation_id?: number;
  short_description?: string;
  /** where the statement came from (upload `source` column, else its batch) */
  source?: string | null;
  field?: string | null;
  difficulty?: string | null;
}

/** Generate mode: a new idea from the offline generator. Deliberately has no
 *  project_id - it is not a catalogue row. */
export interface GeneratedIdea {
  title: string;
  description: string;
  domain: string;
  level: string;
  novelty: number | null;
  label: string;
}

export interface RecommendationResponse {
  student_id: number;
  model_version: number | null;
  mode: "routed" | "off_topic" | "no_signal" | "smalltalk" | "generated";
  message: string;
  routed_domains: string[];
  routing_source: string;
  /** off_topic / no_signal: domains to suggest instead (no projects are returned) */
  suggested_domains: string[];
  scoring_formula: string;
  weights: Record<string, number>;
  faculty_matching_active: boolean;
  faculty_matching_note: string;
  recommendations: Recommendation[];
  refinement?: { negative: string[]; positive: string[] } | null;
  generated_ideas?: GeneratedIdea[];
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
  domain?: string | null;
  field?: string | null;
  difficulty?: string | null;
  source?: string | null;
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

/* ------------------------------------------------------------------ *
 * chat + session
 * ------------------------------------------------------------------ */
export interface Session {
  studentId: number;
  name: string;
  email: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  /** the raw, detailed backend message (routing confidence, parsed terms) -
   *  kept alongside the friendlier `text` shown by default, and revealed
   *  behind a "Routing details" toggle. */
  detail?: string;
  createdAt: string;
  result?: RecommendationResponse;
  pending?: boolean;
  error?: boolean;
}
