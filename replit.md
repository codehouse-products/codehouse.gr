# codehouse.gr

Ιστοσελίδα της εταιρείας web design **Codehouse** (codehouse.gr).

## Stack

- Static HTML / CSS / JS
- PHP 8.2 (για admin panel και lead capture)
- Zoho Mail API (για αποστολή email από φόρμες)

## Δομή

- `index.html` — Αρχική σελίδα
- `admin/` — Admin panel (PHP, password-protected)
- `lead.php` — Lead capture endpoint (αποθηκεύει σε `leads/leads.jsonl` + email)
- `blog/` — Blog άρθρα
- `douleies/` — Portfolio
- `qr-menu/` — QR menu service page
- `assets/` — CSS, JS, εικόνες

## Εκτέλεση

```bash
php -S 0.0.0.0:5000
```

## GitHub

Repo: `https://github.com/codehouse-products/codehouse.gr`

## Deployment

Το site κάνει deploy μέσω GitHub Actions → SSH στον production server.
Workflow: `.github/workflows/deploy.yml`

## User preferences

- Επικοινωνία στα Ελληνικά
