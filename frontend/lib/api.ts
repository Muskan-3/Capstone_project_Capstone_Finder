import type {
  CorpusPage,
  FacultyPreference,
  FacultyPreferenceList,
  ModelStatus,
  ModelVersion,
  ProblemStatement,
  RecommendationResponse,
  StudentProfile,
} from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") || "http://127.0.0.1:8000";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
      cache: "no-store",
    });
  } catch {
    throw new ApiError(
      0,
      `Can't reach the Capstone Compass API at ${API_BASE}. Start the backend: ` +
        `cd backend && uvicorn app.main:app --port 8000`,
    );
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      /* keep statusText */
    }
    throw new ApiError(res.status, typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

export const api = {
  health: () => req<{ status: string; offline: boolean }>("/api/health"),

  saveStudent: (s: StudentProfile) =>
    req<StudentProfile & { id: number }>("/api/students", {
      method: "POST",
      body: JSON.stringify(s),
    }),

  recommend: (student_id: number, filters: Record<string, unknown> = {}) =>
    req<RecommendationResponse>("/api/recommendations", {
      method: "POST",
      body: JSON.stringify({ student_id, filters }),
    }),

  refine: (student_id: number, constraint: string, exclude_project_ids: string[] = []) =>
    req<RecommendationResponse>("/api/recommendations/refine", {
      method: "POST",
      body: JSON.stringify({ student_id, constraint, exclude_project_ids }),
    }),

  feedback: (recommendation_id: number, verdict: "accept" | "reject") =>
    req<unknown>("/api/feedback", {
      method: "POST",
      body: JSON.stringify({ recommendation_id, verdict }),
    }),

  modelStatus: () => req<ModelStatus>("/api/model/status"),
  retrain: (notes = "") =>
    req<ModelVersion>("/api/model/retrain", { method: "POST", body: JSON.stringify({ notes }) }),
  activate: (version: number) =>
    req<ModelVersion>("/api/model/activate", {
      method: "POST",
      body: JSON.stringify({ version }),
    }),

  corpus: (params: {
    page?: number;
    page_size?: number;
    q?: string;
    cluster_id?: number;
    flagged?: boolean;
  }) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => v !== undefined && v !== "" && qs.set(k, String(v)));
    return req<CorpusPage>(`/api/corpus?${qs.toString()}`);
  },
  flagged: () => req<ProblemStatement[]>("/api/corpus/flagged"),
  patchCorpus: (
    id: number,
    patch: { project_id?: string; title?: string; statement?: string; clear_flag?: boolean },
  ) =>
    req<ProblemStatement>(`/api/corpus/${id}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    }),

  uploadBatch: async (file: File, source_batch?: string) => {
    const fd = new FormData();
    fd.append("file", file);
    if (source_batch) fd.append("source_batch", source_batch);
    const res = await fetch(`${API_BASE}/api/corpus/upload`, { method: "POST", body: fd });
    if (!res.ok) throw new ApiError(res.status, (await res.json()).detail ?? res.statusText);
    return res.json() as Promise<{
      source_batch: string;
      inserted: number;
      report: Record<string, unknown>;
      retrain_recommended: boolean;
    }>;
  },

  facultyPreferences: () => req<FacultyPreferenceList>("/api/faculty-preferences"),
  addFacultyPreference: (p: { faculty_name: string; domain: string; notes: string }) =>
    req<FacultyPreference>("/api/faculty-preferences", {
      method: "POST",
      body: JSON.stringify(p),
    }),
};
