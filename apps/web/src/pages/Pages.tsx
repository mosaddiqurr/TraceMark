import { type FormEvent, type ReactNode, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, Navigate, useLocation, useNavigate, useParams } from "react-router-dom";
import {
  ArrowRight, Check, ChevronRight, CircleHelp, Download,
  FileImage, FileOutput, Fingerprint, FlaskConical, Globe2, ImagePlus, Layers3, LockKeyhole,
  Plus, ScanSearch, Search, Shield, ShieldCheck, Sparkles, Upload, X,
} from "lucide-react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api/client";
import type {
  Asset, BenchmarkRun, Collection, DashboardSummary, Distribution, Evidence, Job, Page, Report, Scan, SessionResponse,
} from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { Logo } from "../components/Logo";
import { EmptyState, ErrorState, FullPageLoader, LoadingState, StatusBadge } from "../components/States";

const date = (value: string) => new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
const bytes = (value: number) => value < 1024 * 1024 ? `${(value / 1024).toFixed(1)} KB` : `${(value / 1024 / 1024).toFixed(1)} MB`;

function PageHeader({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: ReactNode }) {
  return <header className="page-header"><div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1><p>{description}</p></div>{action}</header>;
}

function Section({ title, description, children }: { title: string; description?: string; children: ReactNode }) {
  return <section className="panel"><div className="panel-head"><div><h2>{title}</h2>{description && <p>{description}</p>}</div></div>{children}</section>;
}

function MutationError({ error }: { error: unknown }) { return error ? <ErrorState error={error} /> : null; }

export function LandingPage() {
  const { user, loading } = useAuth();
  return <div className="public-page">
    <header className="public-nav"><Logo /><nav aria-label="Public navigation"><a href="#method">How it works</a><a href="#principles">Principles</a></nav><div className="nav-actions">{!loading && user ? <Link className="button primary" to="/app">Open workspace <ArrowRight /></Link> : <><Link className="button ghost" to="/login">Sign in</Link><Link className="button primary" to="/register">Create workspace</Link></>}</div></header>
    <main>
      <section className="hero">
        <div className="hero-copy"><p className="eyebrow"><span /> Image provenance, made inspectable</p><h1>Leave a mark.<br /><em>Follow the evidence.</em></h1><p className="hero-lead">TraceMark protects still images with authenticated, opaque watermarks—and explains every signal it finds without turning ambiguity into certainty.</p><div className="hero-actions"><Link className="button primary large" to={user ? "/app/protect" : "/register"}>Protect an image <ArrowRight /></Link><a className="button ghost large" href="#method">Explore the method</a></div><p className="fine-print"><ShieldCheck /> Local-first · no personal data embedded · evidence-led reports</p></div>
        <div className="hero-visual" aria-label="Illustration of an image being traced through evidence layers">
          <div className="image-card image-card-back"><span>registered original</span></div><div className="image-card image-card-front"><div className="scene-lines" /><span className="watermark-pulse"><i /><i /><i /></span><footer><div><small>Authenticated payload</small><strong>Integrity verified</strong></div><Check /></footer></div>
          <div className="evidence-chip chip-one"><Fingerprint /><span><small>Opaque token</small><strong>HMAC valid</strong></span></div><div className="evidence-chip chip-two"><Layers3 /><span><small>Transform evidence</small><strong>3 repetitions</strong></span></div>
        </div>
      </section>
      <section className="method-strip" id="method"><div><span>01</span><Shield /><h2>Protect</h2><p>Register an image and embed an authenticated ownership or distribution token.</p></div><ChevronRight /><div><span>02</span><ScanSearch /><h2>Verify</h2><p>Inspect cryptographic, exact-hash, visual-feature, and provenance evidence.</p></div><ChevronRight /><div><span>03</span><FileOutput /><h2>Report</h2><p>Export a versioned evidence snapshot with explicit limitations.</p></div></section>
      <section className="principles" id="principles"><div><p className="eyebrow">Built for careful conclusions</p><h2>Forensics without the black box.</h2></div><div className="principle-grid"><article><LockKeyhole /><h3>Authenticated by design</h3><p>Extracted identifiers are accepted only after error correction and cryptographic integrity verification.</p></article><article><CircleHelp /><h3>No mystery score</h3><p>Independent measurements stay independent, so a match can be examined instead of merely trusted.</p></article><article><FlaskConical /><h3>Test your assumptions</h3><p>Run repeatable transformations against robust and baseline methods, then inspect measured outcomes.</p></article></div></section>
    </main>
    <footer className="public-footer"><Logo /><p>Research and educational software. Findings are evidence—not legal proof or proof of intent.</p><Link to="/app/methodology">Read methodology</Link></footer>
  </div>;
}

export function AuthPage({ mode }: { mode: "login" | "register" }) {
  const { user, loading, login, register } = useAuth();
  const [error, setError] = useState<unknown>(null);
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  if (loading) return <FullPageLoader />;
  if (user) return <Navigate to="/app" replace />;
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setError(null); setSubmitting(true);
    const data = new FormData(event.currentTarget);
    try {
      if (mode === "register") await register(String(data.get("display_name")), String(data.get("email")), String(data.get("password")));
      else await login(String(data.get("email")), String(data.get("password")));
      const state = location.state as { from?: string } | null;
      navigate(state?.from ?? "/app", { replace: true });
    } catch (reason) { setError(reason); } finally { setSubmitting(false); }
  };
  return <main className="auth-page"><section className="auth-brand"><Logo /><div><p className="eyebrow">Authenticated evidence workspace</p><h1>Know what survived.<br />Show how you know.</h1><p>Private assets, opaque identifiers, transparent measurements.</p></div><p className="auth-footnote"><ShieldCheck /> TraceMark never embeds recipient names or email addresses into image pixels.</p></section><section className="auth-form-wrap"><div className="auth-form"><p className="eyebrow">{mode === "login" ? "Welcome back" : "Start tracing carefully"}</p><h2>{mode === "login" ? "Sign in to TraceMark" : "Create your workspace"}</h2><p>{mode === "login" ? "Continue to your private evidence workspace." : "Register a private local account."}</p><form onSubmit={submit}>{mode === "register" && <label>Display name<input required name="display_name" autoComplete="name" /></label>}<label>Email address<input required type="email" name="email" autoComplete="email" /></label><label>Password<input required type="password" name="password" minLength={12} autoComplete={mode === "login" ? "current-password" : "new-password"} /><small>{mode === "register" && "Use at least 12 characters."}</small></label>{error !== null && <MutationError error={error} />}<button className="button primary full" disabled={submitting}>{submitting ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}<ArrowRight /></button></form><p className="form-switch">{mode === "login" ? "New to TraceMark?" : "Already registered?"} <Link to={mode === "login" ? "/register" : "/login"}>{mode === "login" ? "Create an account" : "Sign in"}</Link></p></div></section></main>;
}

export function DashboardPage() {
  const query = useQuery({ queryKey: ["dashboard"], queryFn: () => api<DashboardSummary>("/system/dashboard") });
  return <><PageHeader eyebrow="Workspace" title="Evidence overview" description="Your registered assets, active processing, and recent evidence activity." action={<Link className="button primary" to="/app/protect"><ImagePlus /> Protect image</Link>} />
    {query.isLoading ? <LoadingState label="Loading workspace summary" /> : query.isError ? <ErrorState error={query.error} onRetry={() => query.refetch()} /> : <>
      <div className="stat-grid"><Stat label="Registered assets" value={query.data!.asset_count} /><Stat label="Protected outputs" value={query.data!.protected_count} /><Stat label="Indexed collections" value={query.data!.collection_count} /><Stat label="Active jobs" value={query.data!.active_job_count} emphasis /></div>
      <Section title="Recent processing" description="The latest work started from this account.">{query.data!.recent_jobs.length ? <JobTable jobs={query.data!.recent_jobs} /> : <EmptyState title="No processing activity yet" detail="Protect or verify an image to begin creating evidence." action={<Link className="text-link" to="/app/protect">Protect your first image <ArrowRight /></Link>} />}</Section>
    </>}
  </>;
}

function Stat({ label, value, emphasis = false }: { label: string; value: number; emphasis?: boolean }) { return <article className={`stat-card ${emphasis ? "emphasis" : ""}`}><span>{label}</span><strong>{value.toLocaleString()}</strong><small>Current workspace</small></article>; }

export function ProtectPage() {
  const client = useQueryClient();
  const profiles = useQuery({ queryKey: ["profiles"], queryFn: () => api<Page<{ id: string; name: string; type: string; description?: string }>>("/profiles") });
  const mutation = useMutation({ mutationFn: async (data: FormData) => {
    const asset = await api<Asset>("/assets", { method: "POST", body: data });
    return api<Job>(`/assets/${asset.id}/protect`, { method: "POST", body: JSON.stringify({ profile_id: data.get("profile_id"), visible_text: data.get("visible_text") || null }) });
  }, onSuccess: () => client.invalidateQueries({ queryKey: ["dashboard"] }) });
  const submit = (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); mutation.mutate(new FormData(event.currentTarget)); };
  return <><PageHeader eyebrow="Protection" title="Protect an image" description="Register an original, choose a watermark profile, and create a private protected output." />
    <div className="split-layout"><form className="panel form-panel" onSubmit={submit}><div className="step-title"><span>1</span><div><h2>Original image</h2><p>JPEG, PNG, or WebP. The server validates decoded content and removes metadata.</p></div></div><label className="dropzone"><Upload /><strong>Choose an image</strong><span>Maximum limits are enforced by the server</span><input required type="file" name="file" accept="image/jpeg,image/png,image/webp" /></label><div className="step-title"><span>2</span><div><h2>Protection profile</h2><p>Profiles control the real embedding method and quality tradeoffs.</p></div></div>{profiles.isLoading ? <LoadingState label="Loading protection profiles" /> : profiles.isError ? <ErrorState error={profiles.error} onRetry={() => profiles.refetch()} /> : profiles.data!.items.length ? <label>Watermark profile<select required name="profile_id" defaultValue=""><option value="" disabled>Select a profile</option>{profiles.data!.items.map((profile) => <option value={profile.id} key={profile.id}>{profile.name} · {profile.type}</option>)}</select></label> : <EmptyState title="No profiles configured" detail="Create a watermark profile before protecting an image." />}<label>Optional visible label<input name="visible_text" maxLength={120} placeholder="e.g. Preview — not for redistribution" /><small>Visible text is separate from the opaque invisible payload.</small></label><MutationError error={mutation.error} />{mutation.data ? <div className="success-callout"><Check /><div><strong>Protection job queued</strong><p>Job {mutation.data.id} is {mutation.data.state}.</p><Link to="/app/jobs">Track progress</Link></div></div> : <button className="button primary" disabled={mutation.isPending || !profiles.data?.items.length}>{mutation.isPending ? "Submitting securely…" : "Create protected output"}<ArrowRight /></button>}</form>
      <aside className="panel guidance-panel"><Sparkles /><h2>What gets embedded?</h2><p>Only a random opaque token and version/integrity fields. Asset names, recipient labels, and personal information stay in private storage.</p><hr /><h3>Acceptance rules</h3><ul className="check-list"><li><Check /> Capacity is checked before processing.</li><li><Check /> Extracted tokens require a valid HMAC.</li><li><Check /> Quality evidence is measured, never estimated.</li></ul></aside></div>
  </>;
}

export function AssetsPage() {
  const query = useQuery({ queryKey: ["assets"], queryFn: () => api<Page<Asset>>("/assets?sort=-created_at") });
  return <><PageHeader eyebrow="Library" title="Registered assets" description="Private originals and their protection history." action={<Link className="button primary" to="/app/protect"><Plus /> Add asset</Link>} /><Section title="All assets">{query.isLoading ? <LoadingState /> : query.isError ? <ErrorState error={query.error} onRetry={() => query.refetch()} /> : query.data!.items.length ? <div className="asset-grid">{query.data!.items.map((asset) => <Link className="asset-card" to={`/app/assets/${asset.id}`} key={asset.id}><div className="asset-thumb">{asset.thumbnail_url ? <img src={asset.thumbnail_url} alt="" /> : <FileImage />}</div><div><strong>{asset.name}</strong><p>{asset.width} × {asset.height} · {bytes(asset.size_bytes)}</p><small>{date(asset.created_at)}</small></div><ChevronRight /></Link>)}</div> : <EmptyState title="Your library is empty" detail="Register an original image to inspect and protect it." action={<Link className="button subtle" to="/app/protect">Protect an image</Link>} />}</Section></>;
}

export function AssetDetailPage() {
  const { assetId } = useParams();
  const query = useQuery({ queryKey: ["asset", assetId], queryFn: () => api<Asset & { sha256?: string; perceptual_hashes?: Record<string, string>; protected_outputs?: { id: string; type: string; created_at: string; download_url?: string }[] }>(`/assets/${assetId}`), enabled: Boolean(assetId) });
  if (query.isLoading) return <LoadingState label="Loading asset evidence" />;
  if (query.isError) return <ErrorState error={query.error} onRetry={() => query.refetch()} />;
  if (!query.data) return null;
  const asset = query.data;
  return <><PageHeader eyebrow="Asset detail" title={asset.name} description={`${asset.media_type} · ${asset.width} × ${asset.height} · ${bytes(asset.size_bytes)}`} action={<Link className="button primary" to="/app/distributions">Create distribution copy</Link>} /><div className="detail-grid"><Section title="Registered original"><dl className="evidence-list"><div><dt>Registered</dt><dd>{date(asset.created_at)}</dd></div><div><dt>SHA-256</dt><dd className="mono">{asset.sha256 ?? "Not available"}</dd></div>{Object.entries(asset.perceptual_hashes ?? {}).map(([key, value]) => <div key={key}><dt>{key}</dt><dd className="mono">{value}</dd></div>)}</dl></Section><Section title="Protected outputs">{asset.protected_outputs?.length ? <ul className="row-list">{asset.protected_outputs.map((output) => <li key={output.id}><div><StatusBadge value={output.type} /><strong>{date(output.created_at)}</strong></div>{output.download_url && <a className="button subtle" href={output.download_url}><Download /> Download</a>}</li>)}</ul> : <EmptyState title="No protected outputs" detail="This original has not been watermarked yet." />}</Section></div></>;
}

export function DistributionsPage() {
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["distributions"], queryFn: () => api<Page<Distribution>>("/distributions?sort=-created_at") });
  const assets = useQuery({ queryKey: ["assets", "choices"], queryFn: () => api<Page<Asset>>("/assets?page_size=100") });
  const mutation = useMutation({ mutationFn: (body: unknown) => api<Job>("/distributions", { method: "POST", body: JSON.stringify(body) }), onSuccess: () => client.invalidateQueries({ queryKey: ["distributions"] }) });
  const submit = (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); const data = new FormData(event.currentTarget); mutation.mutate({ asset_id: data.get("asset_id"), recipient_label: data.get("recipient_label"), reference: data.get("reference") || null }); };
  return <><PageHeader eyebrow="Controlled distribution" title="Distribution copies" description="Create separately tokenized copies. Recipient context stays in the database, never in pixels." /><div className="split-layout"><Section title="Copies" description="Only copies owned by this account are shown.">{query.isLoading ? <LoadingState /> : query.isError ? <ErrorState error={query.error} onRetry={() => query.refetch()} /> : query.data!.items.length ? <ul className="row-list">{query.data!.items.map((item) => <li key={item.id}><div><strong>{item.recipient_label}</strong><p>{item.reference || "No reference"} · {date(item.created_at)}</p></div>{item.download_url && <a className="button subtle" href={item.download_url}><Download /> Download</a>}</li>)}</ul> : <EmptyState title="No distribution copies" detail="Create a traceable copy from a registered asset." />}</Section><form className="panel form-panel compact" onSubmit={submit}><p className="eyebrow">New copy</p><h2>Create distribution copy</h2><label>Source asset<select required name="asset_id" defaultValue=""><option value="" disabled>Select an asset</option>{assets.data?.items.map((asset) => <option key={asset.id} value={asset.id}>{asset.name}</option>)}</select></label><label>Recipient label<input required name="recipient_label" maxLength={120} /><small>Stored privately; not embedded.</small></label><label>Internal reference<input name="reference" maxLength={120} /></label><MutationError error={mutation.error} />{mutation.data ? <div className="success-callout"><Check /><div><strong>Copy job queued</strong><p>Follow its measured progress in Jobs.</p></div></div> : <button className="button primary" disabled={mutation.isPending || !assets.data?.items.length}>Create copy</button>}</form></div></>;
}

export function VerifyPage() {
  const mutation = useMutation({ mutationFn: (body: FormData) => api<Evidence>("/verification", { method: "POST", body }) });
  const submit = (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); mutation.mutate(new FormData(event.currentTarget)); };
  return <><PageHeader eyebrow="Forensic inspection" title="Verify an image" description="Layer authenticated watermark, exact hash, visual similarity, local-feature, and provenance evidence." /><div className="split-layout"><form className="panel form-panel" onSubmit={submit}><h2>Image under examination</h2><label className="dropzone"><ScanSearch /><strong>Choose the image to verify</strong><span>JPEG, PNG, or WebP</span><input required type="file" name="file" accept="image/jpeg,image/png,image/webp" /></label><MutationError error={mutation.error} /><button className="button primary" disabled={mutation.isPending}>{mutation.isPending ? "Examining evidence…" : "Verify image"}<ArrowRight /></button></form><aside>{mutation.data ? <EvidenceCard evidence={mutation.data} /> : <div className="panel guidance-panel"><ShieldCheck /><h2>Evidence stays separate</h2><p>TraceMark does not collapse unrelated signals into a confidence percentage. The result explains cryptographic validity, image similarity, and provenance independently.</p></div>}</aside></div></>;
}

function EvidenceCard({ evidence }: { evidence: Evidence }) { return <section className="panel evidence-card" aria-live="polite"><p className="eyebrow">Verification result</p><div className="classification"><ShieldCheck /><div><small>Classification</small><h2>{evidence.classification.replaceAll("_", " ")}</h2></div></div><p className="disclaimer">This classification is forensic evidence, not legal proof or proof of intent.</p><dl className="evidence-list"><div><dt>Exact registered hash</dt><dd>{evidence.exact_hash_match ? "Match" : "No match"}</dd></div><div><dt>Watermark integrity</dt><dd>{evidence.watermark?.valid ? "Valid" : "Not validated"}</dd></div><div><dt>Corrected symbols</dt><dd>{evidence.watermark?.corrected_symbols ?? "Not available"}</dd></div><div><dt>pHash distance</dt><dd>{evidence.visual?.phash_distance ?? "Not available"}</dd></div><div><dt>RANSAC inliers</dt><dd>{evidence.visual?.ransac_inliers ?? "Not available"}</dd></div><div><dt>Provenance</dt><dd>{evidence.provenance?.state ?? "Not available"}</dd></div></dl><small>Evidence record {evidence.id} · {date(evidence.created_at)}</small></section>; }

export function TracePage() {
  const [term, setTerm] = useState("");
  const [submitted, setSubmitted] = useState("");
  const query = useQuery({ queryKey: ["search", submitted], queryFn: () => api<Page<{ id: string; title: string; classification: string; detail: string; href?: string }>>(`/searches?q=${encodeURIComponent(submitted)}`), enabled: Boolean(submitted) });
  return <><PageHeader eyebrow="Workspace search" title="Trace search" description="Search your authorized evidence by opaque token, asset reference, or record identifier." /><form className="search-bar" onSubmit={(event) => { event.preventDefault(); setSubmitted(term.trim()); }}><Search /><label className="sr-only" htmlFor="trace-query">Search evidence</label><input id="trace-query" value={term} onChange={(event) => setTerm(event.target.value)} placeholder="Token, asset, reference, or record ID" /><button className="button primary" disabled={!term.trim()}>Search</button></form><Section title="Search results">{!submitted ? <EmptyState title="Enter a trace reference" detail="Results are constrained to records this account can access." /> : query.isLoading ? <LoadingState label="Searching evidence" /> : query.isError ? <ErrorState error={query.error} onRetry={() => query.refetch()} /> : query.data!.items.length ? <ul className="result-list">{query.data!.items.map((item) => <li key={item.id}><div><StatusBadge value={item.classification} /><h3>{item.title}</h3><p>{item.detail}</p></div>{item.href && <Link to={item.href}><ArrowRight /><span className="sr-only">Open {item.title}</span></Link>}</li>)}</ul> : <EmptyState title="No authorized evidence found" detail="No accessible record matches this query. This does not prove that the image or token never existed." />}</Section></>;
}

export function CollectionsPage() {
  const client = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const query = useQuery({ queryKey: ["collections"], queryFn: () => api<Page<Collection>>("/collections?sort=-updated_at") });
  const mutation = useMutation({ mutationFn: (name: string) => api<Collection>("/collections", { method: "POST", body: JSON.stringify({ name }) }), onSuccess: () => { setShowCreate(false); client.invalidateQueries({ queryKey: ["collections"] }); } });
  return <><PageHeader eyebrow="Indexed media" title="Collections" description="Build private, searchable image sets with measured fingerprints and safe batch ingestion." action={<button className="button primary" onClick={() => setShowCreate(true)}><Plus /> New collection</button>} />{showCreate && <form className="inline-create panel" onSubmit={(event) => { event.preventDefault(); mutation.mutate(String(new FormData(event.currentTarget).get("name"))); }}><label>Collection name<input autoFocus required name="name" maxLength={100} /></label><button className="button primary" disabled={mutation.isPending}>Create</button><button className="icon-button" type="button" onClick={() => setShowCreate(false)} aria-label="Cancel"><X /></button></form>}<Section title="Your collections">{query.isLoading ? <LoadingState /> : query.isError ? <ErrorState error={query.error} onRetry={() => query.refetch()} /> : query.data!.items.length ? <div className="collection-grid">{query.data!.items.map((collection) => <article className="collection-card" key={collection.id}><div className="collection-icon"><Layers3 /></div><div><StatusBadge value={collection.state ?? "ready"} /><h3>{collection.name}</h3><p>{collection.item_count.toLocaleString()} indexed images</p><small>Updated {date(collection.updated_at)}</small></div></article>)}</div> : <EmptyState title="No collections yet" detail="Create a collection to index images for similarity search." />}</Section></>;
}

export function ScannerPage() {
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["scans"], queryFn: () => api<Page<Scan>>("/scans?sort=-created_at") });
  const mutation = useMutation({ mutationFn: (url: string) => api<Job>("/scans", { method: "POST", body: JSON.stringify({ url }) }), onSuccess: () => client.invalidateQueries({ queryKey: ["scans"] }) });
  return <><PageHeader eyebrow="Controlled public sources" title="Source scanner" description="Inspect one explicitly supplied public image or page. TraceMark does not crawl websites." /><div className="split-layout"><form className="panel form-panel compact" onSubmit={(event) => { event.preventDefault(); mutation.mutate(String(new FormData(event.currentTarget).get("url"))); }}><Globe2 /><h2>Scan a public URL</h2><label>HTTP(S) image or page URL<input type="url" required name="url" placeholder="https://example.org/image.jpg" /></label><div className="notice"><Shield /><p>Private, local, reserved, redirected-to-private, oversized, and disallowed resources are rejected.</p></div><MutationError error={mutation.error} /><button className="button primary" disabled={mutation.isPending}>{mutation.isPending ? "Validating source…" : "Start bounded scan"}</button></form><Section title="Recent scans">{query.isLoading ? <LoadingState /> : query.isError ? <ErrorState error={query.error} onRetry={() => query.refetch()} /> : query.data!.items.length ? <ul className="row-list">{query.data!.items.map((scan) => <li key={scan.id}><div><StatusBadge value={scan.state} /><strong className="truncate">{scan.url}</strong><p>{scan.candidate_count} candidates · {scan.match_count} matches · {date(scan.created_at)}</p></div></li>)}</ul> : <EmptyState title="No source scans" detail="Submitted sources and measured matches will appear here." />}</Section></div></>;
}

export function BenchmarksPage() {
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["benchmarks"], queryFn: () => api<Page<BenchmarkRun>>("/benchmarks?sort=-created_at") });
  const mutation = useMutation({ mutationFn: (profile: string) => api<Job>("/benchmarks", { method: "POST", body: JSON.stringify({ profile }) }), onSuccess: () => client.invalidateQueries({ queryKey: ["benchmarks"] }) });
  const latest = query.data?.items.find((run) => run.results?.length);
  const chart = latest?.results?.map((result) => ({ name: `${result.transformation} ${result.parameter}`.trim(), Robust: result.robust_detected ? 1 : 0, LSB: result.lsb_detected ? 1 : 0 }));
  return <><PageHeader eyebrow="Measured resilience" title="Robustness laboratory" description="Run deterministic transformations and compare authenticated extraction—not estimated durability." action={<select aria-label="Start benchmark profile" defaultValue="" onChange={(event) => { if (event.target.value) mutation.mutate(event.target.value); }} disabled={mutation.isPending}><option value="" disabled>{mutation.isPending ? "Starting…" : "Run benchmark…"}</option><option value="quick">Quick</option><option value="standard">Standard</option><option value="aggressive">Aggressive</option></select>} /><div className="detail-grid"><Section title="Latest measured results" description={latest ? `${latest.name} · ${latest.profile}` : "Completed benchmark extraction outcomes."}>{chart?.length ? <div className="chart-wrap" role="img" aria-label="Detection outcomes by image transformation"><ResponsiveContainer width="100%" height={320}><BarChart data={chart}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="name" hide /><YAxis domain={[0, 1]} ticks={[0, 1]} /><Tooltip /><Legend /><Bar dataKey="Robust" fill="#cf5c36" radius={[4, 4, 0, 0]} /><Bar dataKey="LSB" fill="#436f66" radius={[4, 4, 0, 0]} /></BarChart></ResponsiveContainer></div> : <EmptyState title="No measured results" detail="Complete a benchmark to populate this chart. TraceMark does not display sample results as if they were measurements." />}</Section><Section title="Benchmark runs">{query.isLoading ? <LoadingState /> : query.isError ? <ErrorState error={query.error} onRetry={() => query.refetch()} /> : query.data!.items.length ? <ul className="row-list">{query.data!.items.map((run) => <li key={run.id}><div><StatusBadge value={run.state} /><strong>{run.name}</strong><p>{run.profile} · {date(run.created_at)}</p></div></li>)}</ul> : <EmptyState title="No benchmark runs" detail="Choose a profile to test supported transformations and negative controls." />}</Section></div></>;
}

export function ReportsPage() {
  const query = useQuery({ queryKey: ["reports"], queryFn: () => api<Page<Report>>("/reports?sort=-created_at") });
  return <><PageHeader eyebrow="Immutable snapshots" title="Evidence reports" description="Download versioned, integrity-authenticated records of verification or benchmark evidence." /><Section title="Generated reports">{query.isLoading ? <LoadingState /> : query.isError ? <ErrorState error={query.error} onRetry={() => query.refetch()} /> : query.data!.items.length ? <div className="report-table"><div className="table-head"><span>Report</span><span>Type</span><span>Generated</span><span>Formats</span></div>{query.data!.items.map((report) => <div className="table-row" key={report.id}><div><FileOutput /><strong>{report.title}</strong></div><StatusBadge value={report.kind} /><span>{date(report.created_at)}</span><div className="format-links">{report.formats.map((format) => <a key={format} href={`/api/v1/reports/${report.id}/download?format=${format}`} aria-label={`Download ${report.title} as ${format}`}><Download />{format.toUpperCase()}</a>)}</div></div>)}</div> : <EmptyState title="No reports generated" detail="Generate a report from completed verification or benchmark evidence." />}</Section></>;
}

export function JobsPage() {
  const query = useQuery({ queryKey: ["jobs"], queryFn: () => api<Page<Job>>("/jobs?sort=-created_at"), refetchInterval: (state) => state.state.data?.items.some((job) => ["queued", "running"].includes(job.state)) ? 2000 : false });
  return <><PageHeader eyebrow="Processing" title="Jobs" description="Transparent progress for protection, verification, indexing, scanning, reports, and benchmarks." /><Section title="All jobs">{query.isLoading ? <LoadingState /> : query.isError ? <ErrorState error={query.error} onRetry={() => query.refetch()} /> : query.data!.items.length ? <JobTable jobs={query.data!.items} /> : <EmptyState title="No jobs" detail="Long-running operations will expose status and safe failure details here." />}</Section></>;
}

function JobTable({ jobs }: { jobs: Job[] }) { return <div className="job-table"><div className="table-head"><span>Status</span><span>Stage</span><span>Progress</span><span>Updated</span></div>{jobs.map((job) => <div className="table-row" key={job.id}><StatusBadge value={job.state} /><div><strong>{job.stage}</strong>{job.error && <small className="error-text">{job.error.message}</small>}</div><div className="progress-cell"><div className="progress-track"><i style={{ width: `${Math.max(0, Math.min(100, job.progress))}%` }} /></div><span>{Math.round(job.progress)}%</span></div><span>{date(job.updated_at)}</span></div>)}</div>; }

export function SettingsPage() {
  const query = useQuery({ queryKey: ["settings"], queryFn: () => api<{ scanning_enabled: boolean; provenance_state: string; active_key_version: number; supported_formats: string[] }>("/settings") });
  return <><PageHeader eyebrow="Configuration" title="Settings" description="Inspect security-sensitive capabilities. Secrets and key material are never exposed here." />{query.isLoading ? <LoadingState /> : query.isError ? <ErrorState error={query.error} onRetry={() => query.refetch()} /> : <div className="detail-grid"><Section title="System capabilities"><dl className="evidence-list"><div><dt>Public URL scanning</dt><dd><StatusBadge value={query.data!.scanning_enabled ? "enabled" : "disabled"} /></dd></div><div><dt>Provenance adapter</dt><dd><StatusBadge value={query.data!.provenance_state} /></dd></div><div><dt>Active key version</dt><dd>Version {query.data!.active_key_version}</dd></div><div><dt>Accepted formats</dt><dd>{query.data!.supported_formats.join(", ")}</dd></div></dl></Section><aside className="panel guidance-panel"><LockKeyhole /><h2>Key separation</h2><p>The master key and derived authentication keys remain outside the database and browser. Only non-secret version metadata is displayed.</p></aside></div>}</>;
}

export function MethodologyPage() { return <><PageHeader eyebrow="Transparent by design" title="Methodology & limits" description="How TraceMark reaches classifications—and where those conclusions stop." /><article className="methodology panel"><section><span className="method-number">01</span><div><h2>Authenticated pixel evidence</h2><p>Ownership and distribution watermarks carry opaque random tokens with version information, error correction, CRC, and a truncated HMAC. A decoded token is never accepted until its HMAC validates.</p></div></section><section><span className="method-number">02</span><div><h2>Independent visual evidence</h2><p>Exact hashes, perceptual hash distances, and ORB/RANSAC local-feature checks remain visible as separate measurements. They are not averaged into a confidence score.</p></div></section><section><span className="method-number">03</span><div><h2>Deterministic classification</h2><p>Strong authenticated or exact evidence takes precedence over calibrated derivative matches, possible visual matches, no evidence, and inconclusive outcomes.</p></div></section><section><span className="method-number">04</span><div><h2>Explicit limitations</h2><p>Severe crop, rotation, recompression, resampling, overlays, and noise can destroy a classical watermark. A missing signal is not proof that an image was never protected. Results are not legal proof or evidence of recipient intent.</p></div></section></article></>; }

export function NotFoundPage() { return <main className="full-state"><Logo /><h1>Page not found</h1><p>The address does not point to a TraceMark view.</p><Link className="button primary" to="/">Return home</Link></main>; }

// Keeps the API contract exported in generated declaration analysis without coupling page rendering to it.
export type AuthSessionContract = SessionResponse;
