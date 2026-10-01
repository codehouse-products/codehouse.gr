---
name: Durable sandbox globals
description: Avoid assuming browser globals exist when composing callback calls.
---

Do not assume the durable callback sandbox provides browser globals such as the `URL` constructor.

**Why:** URL construction in a durable block failed before the canvas update could execute, although the app and preview were already verified.

**How to apply:** Use plain string operations for simple additions to a verified URL, or isolate URL parsing in an impure function. Keep callback calls in the durable scope.