---
name: GitHub workflow writes
description: Permission constraint encountered when deploying server configuration through the repository workflow.
---

Updating ordinary repository files through the GitHub Data API can work while writes that include `.github/workflows/*` fail with a 404 or 403 when the OAuth grant lacks workflow permission. Reauthorization may still return only `repo` scope.

**Why:** The production URL redirect required an nginx include and a workflow command to install/reload it, but the available GitHub connector could not write the workflow file. The application files alone could not make nginx use `index.php` for directory requests.

**How to apply:** Treat server-config changes as blocked until the deployment workflow can be updated or the server configuration can be edited directly. Never report a directory redirect as fixed based only on a direct `index.php` endpoint; verify the exact slash URL live.