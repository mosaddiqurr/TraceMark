# Data Model

Users own assets, jobs, verifications, collections, scans, benchmarks, and reports. Assets reference immutable original metadata and have profiles, protected outputs, distributions, verification history, and benchmark history.

A distribution stores an opaque embedded token and optional database-only label/reference. Verification records immutable evidence snapshots and may resolve to an authorized asset/distribution. Collection items and scan candidates share indexed-media fingerprints while retaining source and first/last-seen evidence.

All externally visible identifiers are UUIDs. Watermark tokens are independent random 128-bit values. Database records store key versions, never raw master keys. Audit events are append-only and contain actor, action, object reference, correlation ID, safe metadata, and timestamp.

