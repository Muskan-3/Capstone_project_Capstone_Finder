"use client";

import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { fmt, shortDate } from "@/lib/format";
import type {
  CorpusPage,
  FacultyPreferenceList,
  ModelStatus,
  ProblemStatement,
} from "@/lib/types";

type Tab = "corpus" | "review" | "model" | "faculty";

export default function AdminPage() {
  const [tab, setTab] = useState<Tab>("review");
  const [status, setStatus] = useState<ModelStatus | null>(null);
  const [statusErr, setStatusErr] = useState<string | null>(null);

  const loadStatus = useCallback(async () => {
    try {
      setStatus(await api.modelStatus());
      setStatusErr(null);
    } catch (e) {
      setStatusErr(e instanceof ApiError ? e.message : "Could not load model status.");
    }
  }, []);

  useEffect(() => {
    void loadStatus();
  }, [loadStatus]);

  return (
    <div className="mx-auto max-w-chart px-4 py-10 sm:px-6">
      <p className="text-sm text-deep-teal">Admin &amp; faculty</p>
      <h1 className="mt-1 font-display text-3xl">Catalogue &amp; model control</h1>
      <p className="mt-2 max-w-2xl text-sm text-charcoal-text/70">
        Mirrors the department&rsquo;s existing manual review process: dirty rows land in a review
        queue, get fixed here, and the model is retrained on the whole catalogue when you choose.
      </p>

      {statusErr && (
        <p role="alert" className="chart-card mt-4 border-l-2 border-l-brass p-3 text-sm">
          {statusErr}
        </p>
      )}

      {status && (
        <div className="panel mt-5 grid grid-cols-2 gap-px overflow-hidden bg-hairline sm:grid-cols-4">
          <Stat label="Catalogue size" value={String(status.corpus_size)} />
          <Stat label="Active pool" value={String(status.active_corpus_size)} />
          <Stat label="Needs review" value={String(status.flagged_count)} tone="brass" />
          <Stat
            label="Active model"
            value={status.active_version != null ? `v${status.active_version}` : "-"}
          />
        </div>
      )}

      <div className="mt-6 flex flex-wrap gap-1 border-b border-hairline">
        {(
          [
            ["review", "Needs review"],
            ["corpus", "Corpus browser"],
            ["model", "Model & batches"],
            ["faculty", "Faculty preferences"],
          ] as [Tab, string][]
        ).map(([t, label]) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            aria-current={tab === t ? "page" : undefined}
            className={`-mb-px border-b-2 px-3 py-2 text-sm transition-colors ${
              tab === t
                ? "border-brass text-charcoal-text"
                : "border-transparent text-charcoal-text/60 hover:text-charcoal-text"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="mt-6">
        {tab === "review" && <ReviewQueue onChanged={loadStatus} />}
        {tab === "corpus" && <CorpusBrowser />}
        {tab === "model" && <ModelPanel status={status} onChanged={loadStatus} />}
        {tab === "faculty" && <FacultyPanel />}
      </div>
    </div>
  );
}

function Stat({ label, value, tone }: { label: string; value: string; tone?: "brass" }) {
  return (
    <div className="bg-parchment-raised p-4">
      <p className="readout-label">{label}</p>
      <p className={`data-token mt-1 text-2xl ${tone === "brass" ? "text-brass" : ""}`}>{value}</p>
    </div>
  );
}

/* ------------------------------------------------------------------ *
 * Needs Review queue - exactly the Section 3 flagged rows
 * ------------------------------------------------------------------ */
function ReviewQueue({ onChanged }: { onChanged: () => void }) {
  const [rows, setRows] = useState<ProblemStatement[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setRows(await api.flagged());
      setErr(null);
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Could not load the review queue.");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (err) return <p className="chart-card border-l-2 border-l-brass p-3 text-sm">{err}</p>;
  if (!rows) return <p className="text-sm text-charcoal-text/60">Loading…</p>;
  if (rows.length === 0)
    return (
      <p className="chart-card p-5 text-sm text-charcoal-text/70">
        The review queue is empty &mdash; every catalogue row is clean and in the active pool.
      </p>
    );

  return (
    <div className="space-y-3">
      <p className="text-sm text-charcoal-text/70">
        {rows.length} row{rows.length > 1 ? "s" : ""} excluded from recommendations until fixed.
        Reasons: <span className="data-token">missing_title</span>,{" "}
        <span className="data-token">missing_statement</span>,{" "}
        <span className="data-token">duplicate_project_id</span>.
      </p>
      {rows.map((r) => (
        <FlaggedRow
          key={r.id}
          row={r}
          onSaved={() => {
            void load();
            onChanged();
          }}
        />
      ))}
    </div>
  );
}

function FlaggedRow({ row, onSaved }: { row: ProblemStatement; onSaved: () => void }) {
  const [title, setTitle] = useState(row.title ?? "");
  const [statement, setStatement] = useState(row.statement ?? "");
  const [projectId, setProjectId] = useState(row.project_id);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const save = async () => {
    setBusy(true);
    setErr(null);
    try {
      await api.patchCorpus(row.id, {
        project_id: projectId,
        title,
        statement,
        clear_flag: true,
      });
      onSaved();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Save failed.");
      setBusy(false);
    }
  };

  return (
    <details className="chart-card border-l-2 border-l-brass p-4">
      <summary className="flex cursor-pointer flex-wrap items-center gap-2 text-sm">
        <span className="data-token pill">{row.project_id}</span>
        <span className="pill text-brass">{row.flag_reason}</span>
        <span className="truncate text-charcoal-text/80">{row.title || "— no title —"}</span>
      </summary>

      <div className="mt-4 space-y-3">
        <label className="block text-sm">
          <span className="readout-label">Project ID</span>
          <input
            value={projectId}
            onChange={(e) => setProjectId(e.target.value)}
            className="chart-card mt-1 w-full bg-parchment px-2 py-1.5 text-sm outline-none"
          />
        </label>
        <label className="block text-sm">
          <span className="readout-label">Title</span>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="chart-card mt-1 w-full bg-parchment px-2 py-1.5 text-sm outline-none"
          />
        </label>
        <label className="block text-sm">
          <span className="readout-label">Problem statement</span>
          <textarea
            value={statement}
            onChange={(e) => setStatement(e.target.value)}
            rows={5}
            className="chart-card mt-1 w-full bg-parchment px-2 py-1.5 text-sm outline-none"
          />
        </label>
        {err && <p className="text-sm text-brass">{err}</p>}
        <div className="flex items-center gap-2">
          <button type="button" onClick={save} className="btn btn-primary !py-1.5 text-xs" disabled={busy}>
            {busy ? "Saving…" : "Save & clear flag if valid"}
          </button>
          <span className="text-xs text-charcoal-text/55">
            Re-flags automatically if the title or statement is still missing. Retrain to fold it
            back in.
          </span>
        </div>
      </div>
    </details>
  );
}

/* ------------------------------------------------------------------ *
 * Corpus browser
 * ------------------------------------------------------------------ */
function CorpusBrowser() {
  const [data, setData] = useState<CorpusPage | null>(null);
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    const id = setTimeout(async () => {
      try {
        setData(await api.corpus({ page, page_size: 20, q }));
        setErr(null);
      } catch (e) {
        setErr(e instanceof ApiError ? e.message : "Could not load the corpus.");
      }
    }, 200);
    return () => clearTimeout(id);
  }, [page, q]);

  return (
    <div>
      <input
        value={q}
        onChange={(e) => {
          setPage(1);
          setQ(e.target.value);
        }}
        placeholder="Search title, statement or Project ID…"
        className="chart-card w-full bg-parchment-raised px-3 py-2 text-sm outline-none sm:max-w-sm"
      />
      {err && <p className="mt-3 text-sm text-brass">{err}</p>}

      <div className="mt-4 overflow-x-auto rounded-card border border-hairline">
        <table className="w-full min-w-[720px] border-collapse text-sm">
          <thead>
            <tr className="bg-parchment-raised text-left">
              <th className="p-2.5 font-medium">Project ID</th>
              <th className="p-2.5 font-medium">Title</th>
              <th className="p-2.5 font-medium">Cluster</th>
              <th className="p-2.5 font-medium">Batch</th>
              <th className="p-2.5 font-medium">State</th>
            </tr>
          </thead>
          <tbody>
            {data?.items.map((r) => (
              <tr key={r.id} className="border-t border-hairline align-top">
                <td className="data-token p-2.5 text-xs">{r.project_id}</td>
                <td className="p-2.5">{r.title || <span className="text-charcoal-text/50">—</span>}</td>
                <td className="p-2.5 text-xs text-charcoal-text/70">{r.cluster_label ?? "—"}</td>
                <td className="p-2.5 text-xs text-charcoal-text/60">{r.source_batch}</td>
                <td className="p-2.5">
                  {r.is_flagged ? (
                    <span className="pill text-brass">{r.flag_reason}</span>
                  ) : (
                    <span className="pill text-deep-teal">active</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {data && (
        <div className="mt-3 flex items-center justify-between text-sm">
          <span className="text-charcoal-text/60">
            {data.total} rows &middot; page {data.page}/{data.pages}
          </span>
          <div className="flex gap-2">
            <button
              type="button"
              className="btn btn-ghost !py-1 text-xs"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
            >
              Prev
            </button>
            <button
              type="button"
              className="btn btn-ghost !py-1 text-xs"
              disabled={page >= data.pages}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ *
 * Model & batches
 * ------------------------------------------------------------------ */
function ModelPanel({
  status,
  onChanged,
}: {
  status: ModelStatus | null;
  onChanged: () => void;
}) {
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const upload = async (file: File) => {
    setBusy("upload");
    setErr(null);
    setMsg(null);
    try {
      const r = await api.uploadBatch(file);
      setMsg(
        `Batch “${r.source_batch}”: ${r.inserted} rows added, ` +
          `${(r.report as { flagged_rows?: number }).flagged_rows ?? 0} flagged for review. ` +
          `Retrain to fold them into the model.`,
      );
      onChanged();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Upload failed.");
    } finally {
      setBusy(null);
    }
  };

  const retrain = async () => {
    setBusy("retrain");
    setErr(null);
    setMsg(null);
    try {
      const mv = await api.retrain("admin retrain");
      setMsg(`Trained model v${mv.version} on ${mv.corpus_size} statements (k=${mv.cluster_count}).`);
      onChanged();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Retrain failed.");
    } finally {
      setBusy(null);
    }
  };

  const activate = async (v: number) => {
    setBusy(`activate-${v}`);
    setErr(null);
    try {
      await api.activate(v);
      setMsg(`Rolled the active model back to v${v}.`);
      onChanged();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Activation failed.");
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="chart-card p-5">
        <h3 className="font-display text-lg">Upload a new batch</h3>
        <p className="mt-1 text-sm text-charcoal-text/70">
          .xlsx or .csv with <span className="data-token">ProjectID</span>,{" "}
          <span className="data-token">Title</span>,{" "}
          <span className="data-token">Problem Statement</span> columns (a title block above the
          header is fine). Same cleaning rules run automatically.
        </p>
        <label className="btn btn-ghost mt-3 cursor-pointer text-sm">
          {busy === "upload" ? "Uploading…" : "Choose file"}
          <input
            type="file"
            accept=".xlsx,.xls,.csv"
            className="sr-only"
            onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])}
          />
        </label>
      </div>

      <div className="chart-card chart-card--primary p-5">
        <h3 className="font-display text-lg">Retrain the model</h3>
        <p className="mt-1 text-sm text-charcoal-text/70">
          Re-runs vectorize → cluster (silhouette sweep) → route over the entire current active
          pool, writes a new version and makes it live. Previous versions stay for rollback.
        </p>
        <button
          type="button"
          onClick={retrain}
          className="btn btn-primary mt-3 text-sm"
          disabled={busy === "retrain"}
        >
          {busy === "retrain" ? "Retraining…" : "Retrain now"}
        </button>
      </div>

      {msg && <p className="chart-card border-l-2 border-l-deep-teal p-3 text-sm">{msg}</p>}
      {err && <p className="chart-card border-l-2 border-l-brass p-3 text-sm">{err}</p>}

      <div>
        <h3 className="font-display text-lg">Version history</h3>
        {status?.silhouette_by_k && Object.keys(status.silhouette_by_k).length > 0 && (
          <p className="mt-1 text-xs text-charcoal-text/60">
            silhouette by k:{" "}
            {Object.entries(status.silhouette_by_k)
              .map(([k, v]) => `k${k}=${v.toFixed(3)}`)
              .join("  ")}
          </p>
        )}
        <div className="mt-3 overflow-x-auto rounded-card border border-hairline">
          <table className="w-full min-w-[640px] border-collapse text-sm">
            <thead>
              <tr className="bg-parchment-raised text-left">
                <th className="p-2.5 font-medium">Version</th>
                <th className="p-2.5 font-medium">Corpus</th>
                <th className="p-2.5 font-medium">Clusters</th>
                <th className="p-2.5 font-medium">Silhouette</th>
                <th className="p-2.5 font-medium">Trained</th>
                <th className="p-2.5 font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {status?.versions.map((v) => (
                <tr key={v.version} className="border-t border-hairline">
                  <td className="data-token p-2.5">
                    v{v.version}
                    {v.is_active && <span className="ml-2 pill text-deep-teal">active</span>}
                  </td>
                  <td className="data-token p-2.5">{v.corpus_size}</td>
                  <td className="data-token p-2.5">{v.cluster_count}</td>
                  <td className="data-token p-2.5">{fmt(v.silhouette)}</td>
                  <td className="p-2.5 text-xs text-charcoal-text/65">{shortDate(v.trained_at)}</td>
                  <td className="p-2.5">
                    {!v.is_active && (
                      <button
                        type="button"
                        onClick={() => activate(v.version)}
                        className="btn btn-ghost !py-1 text-xs"
                        disabled={busy === `activate-${v.version}`}
                      >
                        Roll back to this
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ *
 * Faculty preferences - ready, inactive
 * ------------------------------------------------------------------ */
function FacultyPanel() {
  const [list, setList] = useState<FacultyPreferenceList | null>(null);
  const [form, setForm] = useState({ faculty_name: "", domain: "", notes: "" });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setList(await api.facultyPreferences());
      setErr(null);
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Could not load faculty preferences.");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const add = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      await api.addFacultyPreference(form);
      setForm({ faculty_name: "", domain: "", notes: "" });
      void load();
    } catch (e2) {
      setErr(e2 instanceof ApiError ? e2.message : "Could not save.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-5">
      <div className="chart-card border-l-2 border-l-brass p-4 text-sm">
        <p className="font-medium">Faculty matching: not yet active — no preference data collected.</p>
        <p className="mt-1 text-charcoal-text/75">
          {list?.note ??
            "The FACULTY DETAILS sheet in the source workbook is a review-assignment tracker, not preference data."}{" "}
          Entries added here are stored but stay weighted at 0 in the scoring formula until the team
          switches the weight on.
        </p>
      </div>

      <form onSubmit={add} className="chart-card grid gap-3 p-4 sm:grid-cols-3">
        <input
          required
          placeholder="Faculty name"
          value={form.faculty_name}
          onChange={(e) => setForm((f) => ({ ...f, faculty_name: e.target.value }))}
          className="chart-card bg-parchment px-2 py-1.5 text-sm outline-none"
        />
        <input
          required
          placeholder="Preferred domain / topic"
          value={form.domain}
          onChange={(e) => setForm((f) => ({ ...f, domain: e.target.value }))}
          className="chart-card bg-parchment px-2 py-1.5 text-sm outline-none"
        />
        <input
          placeholder="Notes (optional)"
          value={form.notes}
          onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
          className="chart-card bg-parchment px-2 py-1.5 text-sm outline-none"
        />
        <div className="sm:col-span-3">
          <button type="submit" className="btn btn-ghost text-sm" disabled={busy}>
            {busy ? "Saving…" : "Add preference"}
          </button>
        </div>
      </form>

      {err && <p className="text-sm text-brass">{err}</p>}

      <ul className="space-y-2">
        {list?.items.map((p) => (
          <li key={p.id} className="chart-card flex flex-wrap items-center gap-2 p-3 text-sm">
            <span className="font-medium">{p.faculty_name}</span>
            <span className="pill">{p.domain}</span>
            {p.notes && <span className="text-charcoal-text/60">{p.notes}</span>}
          </li>
        ))}
        {list && list.items.length === 0 && (
          <li className="text-sm text-charcoal-text/55">No preferences entered yet.</li>
        )}
      </ul>
    </div>
  );
}
