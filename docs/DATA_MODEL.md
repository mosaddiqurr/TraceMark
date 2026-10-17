# Focused data model

Two SQLite tables replace the enterprise schema:

| Table | Stored fields |
|---|---|
| browser_workspaces | Random workspace ID, HMAC digest of capability cookie, CSRF value, absolute expiry |
| image_traces | Opaque watermark identifier, owner workspace ID, safe source filename, private label, payload kind, original/output SHA-256, compact fingerprint/ORB descriptor, UTC creation timestamp |

Trace owner is a cascading foreign key. All trace queries filter the active workspace. No image bytes, master/report keys or plaintext cookie values are stored. Descriptors are private derived data, not anonymized.

Protected PNGs and sealed reports use random artifact IDs in private bounded process memory with independent expiry. Artifact IDs are not watermark identifiers. Downloads require the owner cookie. Restarting the API loses transient artifacts while SQLite traces survive.

Expired workspace deletion and explicit clearing remove logical records. Disk pages/WAL/backup copies can retain remnants; no secure-erasure claim is made. There is no migration from the old account schema; the new registry has its own filename/root.

