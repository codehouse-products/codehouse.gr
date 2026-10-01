---
name: Git API path normalization
description: Safeguard for creating Git trees from shell output through the connector sandbox.
---

Normalize carriage returns from every path returned by shell commands before using that path in Git Data API tree entries, and verify the final remote tree has no path containing control characters.

**Why:** Shell callback output may use CRLF line endings. Splitting only on `\n` can leave a hidden `\r` in filenames, creating duplicate malformed paths instead of updating the intended files.

**How to apply:** When transferring commits through the GitHub Git Data API, strip `\r` from parsed paths, compare the final remote diff to the intended path list, and scan the recursive tree for control characters before deployment verification.