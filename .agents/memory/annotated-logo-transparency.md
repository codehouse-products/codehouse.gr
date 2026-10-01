---
name: Annotated logo transparency
description: Preserve a complete annotated logo illustration when making its paper background transparent.
---

Treat construction lines, handwritten labels, and the wordmark as part of the artwork, not as background.

**Why:** Foreground segmentation of the supplied logo isolated only the CH monogram and discarded surrounding lettering. The annotated hero illustration needs the complete graphic preserved.

**How to apply:** For a light paper background, derive transparency from pencil-to-paper luminance contrast rather than object segmentation. Estimate local paper brightness on a downsampled copy, then upsample that estimate and derive alpha from the full-resolution original. Large Pillow maximum-filter kernels at full resolution can time out. Inspect the result against the actual target background and retain the original source.