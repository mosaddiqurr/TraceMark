# User guide

**Protect:** select a JPEG, PNG or WebP still image, optionally enter a recipient/reference label, and choose Protect. Download the protected PNG. Each copy gets a fresh identifier; labels are kept privately and never embedded in pixels.

**Verify:** select an image. TraceMark automatically extracts and authenticates supported watermarks, checks exact hashes and compares private visual references. VERIFIED needs both a valid watermark and an accessible private trace. An original source hash or similar image alone remains NOT VERIFIED. Authentic unresolved marks receive an explicit explanation.

**Evidence and reports:** the result shows the identifier/label when authorized, authenticity, exact hash and similarity. Expand details for file metadata and forensic measurements. Export PDF or JSON from that result; no report section is required.

**Privacy:** uploaded pixels are discarded. Temporary private downloads/reports expire after 15 minutes by default; registry metadata after 30 days. Keep the protected file and use the same browser to resolve its label. Cookie loss, another browser or expiry makes the mapping unavailable. About can explicitly clear this browser's traces.

**Limits:** default 20 MiB, 4 million pixels and 4096 px per side. Animation, invalid types, corrupt content and insufficient watermark capacity are rejected. Images need at least 256 px on each side; detailed images work best.

**Interpretation:** a recovered identifier traces a protected copy. It cannot prove legal ownership, who shared it or recipient intent. Resizing and everyday compression are tolerated within tested bounds; cropping, repainting, heavy compression and deliberate removal may defeat recovery. Visual similarity is supporting evidence.

**Finding copies:** use a reverse image search (Google Lens, TinEye, Bing), then paste any page or image link into **Check a link** on Verify. Save your trace records from About to keep labels beyond the browser's retention or move them to another browser; keep that file private.

## Demonstration walkthrough

1. Home → **Use sample image**.
2. Optionally enter a recipient/reference label.
3. **Protect image** → inspect filename, dimensions, identifier and success.
4. **Download protected image**; save the actual PNG.
5. Navigate to **Verify** and select that saved file. Checks start automatically.
6. Read **VERIFIED**, the matching identifier and private label, authenticity and exact hash.
7. Expand detailed evidence for SHA-256, ECC, pHash and ORB/RANSAC measurements.
8. Export PDF or JSON directly from the result.
9. Re-upload the unprotected sample to observe NOT VERIFIED.
10. Resize the protected image to 50% and verify; v3 still recovers it. Crop 5% from each edge and verify; recovery fails while visual evidence may remain.
11. A second browser workspace must not see the private label or download/report artifacts.

**Verify this image** offers a convenient follow-up using the protected bytes; the saved-file re-upload shows the full journey. Save outputs/reports within their 15-minute default window, and use the same browser within its private metadata retention window.
