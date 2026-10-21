# Portfolio discussion

Demonstrate the complete still-image journey before discussing implementation. The four-page app makes a real protected PNG, recovers an authenticated identifier, shows independent evidence and exports a concise report.

Engineering topics worth explaining:

- Why random identifiers and private label mappings protect personal data.
- The distinction between CRC/error correction, HMAC authentication and authorized provenance resolution.
- Blind classical DWT/DCT/QIM on a resolution-independent canonical grid: resize/JPEG/WebP survival measured against the legacy engine, and an honest crop failure.
- SSRF-safe link checks, signed trace export/import and an editorial, performance-measured interface.
- Why exact hashes, perceptual hashes and ORB/RANSAC are separate evidence.
- Preserving browser-workspace isolation after removing accounts.
- Discarding uploaded pixels while retaining sparse descriptors; privacy limits of those descriptors.
- Hard process termination versus a thread/request timeout that leaves CPU work running.
- Reducing infrastructure to a static client, one API process and a SQLite metadata directory.
- Reproducible negative controls, browser downloads/re-uploads and honest unavailable deployment gates.

Do not present universal robustness, legal ownership, recipient intent, public hosting acceptance without live deployment checks, or a statistically meaningful false-positive rate from the small benchmark.

