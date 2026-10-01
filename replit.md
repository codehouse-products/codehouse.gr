# codehouse.gr

Ιστοσελίδα του **Codehouse — Software & Digital Systems Studio** (codehouse.gr).

## Stack

- Static HTML / CSS / JS
- PHP 8.2 (για admin panel και lead capture)
- Zoho Mail API (για αποστολή email από φόρμες)

## Δομή

- `index.html` — Αρχική σελίδα
- `admin/` — Admin panel (PHP, password-protected)
- `lead.php` — Lead capture endpoint (νέες αιτήσεις εκτός webroot, στον γονικό φάκελο `.codehouse-leads/leads.jsonl` + Zoho email)
- `assets/studio/` — Κεντρικό bilingual manifest, SVG logos, screenshots και studio/legacy UI assets
- `services/`, `projects/`, `studio/`, `contact/` — Νέες σελίδες του studio
- `en/` — Αντίστοιχες αγγλικές σελίδες, περιλαμβανομένων των παλιών οδηγών/landings
- `blog/` — Blog άρθρα
- `douleies/` — Portfolio
- `qr-menu/` — QR menu service page
- `assets/` — CSS, JS, εικόνες

## Εκτέλεση

```bash
php -S 0.0.0.0:5000 router.php
```

## GitHub

Repo: `https://github.com/codehouse-products/codehouse.gr`

## Deployment

Το site κάνει deploy μέσω GitHub Actions → SSH στον production server.
Workflow: `.github/workflows/deploy.yml`

Το preview router δεν είναι production nginx configuration. Το `nginx-private.conf`
πρέπει να ενεργοποιηθεί στον υπάρχοντα production server πριν από την έκδοση,
ώστε να μην είναι δημόσια προσβάσιμα ιστορικά αρχεία `leads/`. Δεν μετακινούμε,
διαβάζουμε ή διαγράφουμε ιστορικές αιτήσεις κατά τον ανασχεδιασμό.

## Αναγέννηση και έλεγχοι

```bash
python3 scripts/generate-studio.py
python3 scripts/refresh_legacy.py
python3 scripts/sync_public_site.py
python3 scripts/check_public_site.py
python3 scripts/test_public_consistency.py
python3 scripts/test_portfolio.py
python3 scripts/test_latest_work.py
python3 scripts/test_lead.py
python3 scripts/test_studio_browser.py
```

Οι έλεγχοι browser απαιτούν τα development-only Python packages και Chromium·
η production ιστοσελίδα παραμένει static HTML/CSS/JS/PHP, χωρίς Python runtime.
Ο HTTP έλεγχος του backend τρέχει σε απομονωμένο προσωρινό φάκελο, χωρίς αποστολή
email ή εγγραφές στις πραγματικές αιτήσεις.

Ο χρήστης προσθέτει τις φωτογραφίες σταδιακά. Όσες θέσεις hero, υπηρεσιών και
project covers δεν έχουν ακόμη εικόνα μένουν κενές, χωρίς fallback ή κείμενα placeholder.
Διατηρούμε το layout και τα πραγματικά desktop/mobile screenshots μέσα στα case studies.
Οδηγίες: `docs/studio-assets-needed.md`.
Δεν επινοούμε παραδοτέα πελατών, αριθμούς αποτελεσμάτων ή social links.

## User preferences

- Επικοινωνία στα Ελληνικά
