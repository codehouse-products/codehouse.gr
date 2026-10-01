---
name: Generated photo framing
description: Preserve foreground neon when finishing generated service photography.
---

Treat aspect-ratio instructions in image prompts as a composition request, not a guarantee of the returned file dimensions.

**Why:** Portrait prompts for service photography returned square images. Assuming the requested dimensions would produce misleading HTML metadata and could crop out the foreground LED effect.

**How to apply:** Inspect the actual output dimensions before resizing, set HTML dimensions from the finished asset, and check the foreground neon remains visible in both desktop and mobile card crops.