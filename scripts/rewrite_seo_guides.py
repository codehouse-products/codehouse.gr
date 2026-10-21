#!/usr/bin/env python3
"""Apply the reviewed rewrite to hand-authored legacy pages, not the daily queue.

Existing shells, styles, forms and published dates are retained. This is a
workspace-only content migration: it never invokes Git or deployment tools.
"""
from datetime import date
from html import escape, unescape
import json
from pathlib import Path
import re
from xml.etree import ElementTree as ET

from seo_metadata import replace_metadata

ROOT = Path(__file__).resolve().parents[1]
TODAY = date.today().isoformat()
COST = "blog/kataskeyi-eshop-ellada-kostos/"
DIY = "blog/dorean-istoselida/"
CHECKLIST = "blog/checklist-dorean-istoselida-epixeirisi/"
MERGE_MARK = '<!-- consolidated-free-website -->'


def text(html):
    return unescape(re.sub(r"<[^>]+>", " ", html)).strip()


def schemas(source, transform):
    def replace(match):
        data = json.loads(match[1])
        transform(data)
        return '<script type="application/ld+json">' + json.dumps(
            data, ensure_ascii=False, indent=2) + "</script>"
    return re.sub(r'<script type="application/ld\+json">(.*?)</script>',
                  replace, source, flags=re.S)


def modified(source):
    def update(item):
        if isinstance(item, dict):
            if item.get("@type") in ("BlogPosting", "Article", "WebPage", "Offer"):
                item["dateModified"] = TODAY
            for value in list(item.values()):
                update(value)
        elif isinstance(item, list):
            for value in item:
                update(value)
    source = schemas(source, update)
    return re.sub(r'(<meta\b[^>]*(?:property|name)="article:modified_time"[^>]*content=")[^"]*',
                  lambda m: m[1] + TODAY, source)


def metadata(source, title, description):
    source = replace_metadata(source, title, description)
    for name, value in (("twitter:title", title), ("twitter:description", description)):
        source = re.sub(r'(<meta\b[^>]*name="' + name + r'"[^>]*content=")[^"]*',
                        lambda m: m[1] + escape(value, quote=True), source)
    return source


FACTORS = [
    ("Πλήθος προϊόντων", "Κατηγορίες, παραλλαγές, φίλτρα, εισαγωγή αρχείων και ποιότητα των διαθέσιμων δεδομένων.",
     "Product catalogue", "Categories, variants, filters, imports and the quality of existing product data."),
    ("Custom design ή template", "Προσαρμογή έτοιμης βάσης ή σχεδιασμός ειδικών σελίδων και ροών αγοράς.",
     "Custom design or template", "Adapting an existing foundation or designing specific pages and purchase journeys."),
    ("Πλατφόρμα", "Διαθέσιμες λειτουργίες, άδειες, περιορισμοί, επεκτάσεις και δυνατότητα μελλοντικής μεταφοράς.",
     "Platform", "Built-in features, licences, constraints, extensions and future portability."),
    ("Πληρωμές και τράπεζες", "Επιλογές πληρωμής, συμβατότητα παρόχων, εγκρίσεις και δοκιμές επιτυχίας και αποτυχίας.",
     "Payments and banks", "Payment methods, provider compatibility, approvals and successful and failed payment tests."),
    ("Μεταφορικά", "Ζώνες, βάρη, παραλαβή, αντικαταβολή και σύνδεση με courier όπου απαιτείται.",
     "Shipping", "Zones, weights, collection, cash on delivery and courier integration where required."),
    ("ERP, τιμολόγηση και myDATA", "Συγχρονισμός αποθήκης, παραστατικών και παραγγελιών, με έλεγχο του API και των υποχρεώσεων της επιχείρησης.",
     "ERP, invoicing and myDATA", "Stock, document and order synchronisation, subject to API availability and the business’s reporting obligations."),
    ("Πολυγλωσσικό κατάστημα", "Μεταφράσεις, περιεχόμενο ανά αγορά, νομίσματα και κανόνες αποστολής όπου χρειάζονται.",
     "Multiple languages", "Translations, market-specific content, currencies and shipping rules where needed."),
    ("Φωτογράφιση και κείμενα", "Ετοιμότητα φωτογραφιών, περιγραφών, χαρακτηριστικών και επιμέλεια υλικού.",
     "Photography and copy", "Availability of images, descriptions and specifications, plus content preparation."),
    ("SEO", "Δομή κατηγοριών, μοναδικό περιεχόμενο, metadata, structured data και τυχόν μεταφορά παλιών URLs.",
     "SEO", "Category structure, original content, metadata, structured data and migration of existing URLs."),
    ("Φιλοξενία και συντήρηση", "Υποδομή, ασφάλεια, backups, ενημερώσεις, παρακολούθηση και συμφωνημένη υποστήριξη.",
     "Hosting and maintenance", "Infrastructure, security, backups, updates, monitoring and agreed support."),
]

EL_SECTIONS = [
    ("megethos", "Ποιο e-shop ταιριάζει στο μέγεθος της επιχείρησής σου;",
     "<h3>Μικρός κατάλογος</h3><p>Μια δοκιμασμένη πλατφόρμα με σαφείς κατηγορίες, λειτουργικό checkout, τις απαραίτητες πληρωμές και απλούς κανόνες αποστολής μπορεί να καλύπτει την αρχή. Δώσε προτεραιότητα σε καλές σελίδες προϊόντων και εύκολη διαχείριση, όχι σε λειτουργίες που δεν χρησιμοποιείς.</p>"
     "<h3>Μεσαίος κατάλογος</h3><p>Όταν αυξάνονται κατηγορίες και παραλλαγές, χρειάζονται χρήσιμα φίλτρα, οργανωμένη αναζήτηση, μαζικές ενημερώσεις και έλεγχος αποθέματος. Εξετάζουμε αν μια σύνδεση ERP ή τιμολόγησης μειώνει πραγματικά τη χειροκίνητη εργασία.</p>"
     "<h3>Μεγάλος ή σύνθετος κατάλογος</h3><p>Πολλαπλές αποθήκες, B2B ροές, ειδικοί τιμοκατάλογοι, μεγάλες εισαγωγές και διαφορετικές αγορές απαιτούν ανάλυση αρχιτεκτονικής και δοκιμές συγχρονισμού και απόδοσης. Ο αριθμός προϊόντων δεν αρκεί μόνος του για να επιλεγεί custom λύση: μετρά και η πολυπλοκότητα των διαδικασιών.</p>"),
    ("epanalamvanomena", "Μηνιαία και επαναλαμβανόμενα κόστη που πρέπει να υπολογίσεις",
     "<p>Χώρισε την αρχική κατασκευή από τη λειτουργία μετά το λανσάρισμα. Δεν είναι όλες οι χρεώσεις μηνιαίες ούτε ισχύουν όλες σε κάθε πλατφόρμα. Ζήτησε να διευκρινίζονται η συχνότητα ανανέωσης και ο υπεύθυνος πληρωμής.</p>"
     "<ul><li>Domain, φιλοξενία ή συνδρομή πλατφόρμας και επαγγελματικό email.</li><li>Άδειες theme, plugins, εφαρμογών και υπηρεσιών διασύνδεσης.</li><li>Προμήθειες παρόχων πληρωμών, τραπεζών και έξοδα αποστολών ή επιστροφών.</li><li>Τεχνική συντήρηση, ενημερώσεις ασφαλείας, backups και υποστήριξη.</li><li>Καταχώριση προϊόντων, φωτογραφίες, κείμενα, μεταφράσεις και διαχείριση παραγγελιών.</li><li>Συνεχής εργασία SEO, μέτρηση αποτελεσμάτων και προαιρετικές καμπάνιες, εφόσον συμφωνηθούν.</li></ul>"),
    ("lathi", "Λάθη που αυξάνουν το κόστος κατασκευής e-shop",
     "<ul><li>Επιλογή πλατφόρμας πριν ελεγχθούν οι απαραίτητες διασυνδέσεις και η δυνατότητα εξαγωγής δεδομένων.</li><li>Ελλιπή ή ασυνεπή στοιχεία προϊόντων που χρειάζονται εκ νέου καταχώριση.</li><li>Προσθήκη λειτουργιών και αλλαγή design αφού εγκριθεί η υλοποίηση, χωρίς επανεξέταση του scope.</li><li>Παράλειψη δοκιμών checkout, αποτυχημένων πληρωμών, μεταφορικών και mobile εμπειρίας.</li><li>Αντιγραφή περιγραφών, ακατάλληλη δομή κατηγοριών ή αλλαγή παλιών URLs χωρίς redirects.</li><li>Προσφορά που δεν ξεχωρίζει τις εργασίες κατασκευής από άδειες, συνδρομές και υποστήριξη.</li></ul>"
     "<p>Ένα σαφές brief και συμφωνημένα κριτήρια αποδοχής περιορίζουν τις επαναλήψεις. Μια χαμηλότερη αρχική προσφορά δεν σημαίνει απαραίτητα χαμηλότερο συνολικό κόστος.</p>"),
    ("enarxi", "Τι χρειάζεται για να ανοίξεις e-shop;",
     "<p>Πριν δεχτείς παραγγελίες, συζήτησε με τον λογιστή σου για ΑΦΜ, έναρξη ή μεταβολή δραστηριότητας, κατάλληλους ΚΑΔ, παραστατικά και τις υποχρεώσεις διαβίβασης στο myDATA που ισχύουν για την επιχείρησή σου. Η τεχνική κατασκευή δεν αντικαθιστά τη φορολογική οργάνωση.</p>"
     "<p>Χρειάζεσαι σαφή στοιχεία επιχείρησης, όρους χρήσης και πώλησης, πολιτική αποστολών και επιστροφών, ενημέρωση για το δικαίωμα υπαναχώρησης όπου εφαρμόζεται, πολιτική απορρήτου και κατάλληλη διαχείριση cookies και προσωπικών δεδομένων σύμφωνα με τον GDPR. Οι ακριβείς απαιτήσεις εξαρτώνται από τα προϊόντα και τις αγορές σου· ζήτησε έλεγχο από λογιστή και νομικό σύμβουλο.</p>"
     "<p>Συγκέντρωσε φωτογραφίες, περιγραφές, κωδικούς και απόθεμα. Επιβεβαίωσε λογαριασμούς και συμβάσεις με τράπεζα ή πάροχο πληρωμών, courier και τυχόν ERP. Δοκίμασε την πλήρη διαδρομή από το προϊόν μέχρι την επιβεβαίωση παραγγελίας πριν ανοίξει το κατάστημα.</p>"),
    ("codehouse", "Πώς δουλεύει η Codehouse και πώς ζητάς προσφορά",
     "<p>Η Codehouse δεν έχει σταθερή τιμή για e-shop: η τιμή διαφέρει ανάλογα με το μέγεθος του project και τις συμφωνημένες απαιτήσεις. Ξεκινάμε καταγράφοντας κατάλογο, κοινό, πληρωμές, αποστολές, περιεχόμενο και διασυνδέσεις. Προτείνουμε λύση με βάση αυτά τα στοιχεία, όχι ένα ίδιο πακέτο για όλους.</p>"
     "<p>Στην πρόταση ξεχωρίζουμε τις εργασίες που περιλαμβάνονται, όσα μένουν εκτός, τις εξαρτήσεις από τρίτους και τα επαναλαμβανόμενα έξοδα. Ακολουθούν συμφωνία scope, σχεδιασμός, ανάπτυξη, έλεγχοι και παράδοση με την υποστήριξη που έχει συμφωνηθεί. Η εκτίμηση χρόνου δίνεται αφού καταγραφούν οι ανάγκες και η ετοιμότητα του υλικού.</p>"
     "<p>Δες την υπηρεσία <a href=\"/services/e-commerce/\">κατασκευής e-shop</a>. Για χρήσιμη προσφορά, στείλε το μέγεθος του καταλόγου, παραδείγματα προϊόντων, τις απαιτούμενες συνδέσεις και ποιος θα διαχειρίζεται το κατάστημα. Η <a href=\"/prosfora/\">προσφορά ιστοσελίδας με μηνιαία συνδρομή</a> αφορά ιστοσελίδα-βιτρίνα, όχι αυτόματα e-shop.</p>"),
    ("seo-geo", "SEO και GEO από τη δομή του καταστήματος",
     "<p>Σωστές κατηγορίες, χρήσιμα φίλτρα, μοναδικές περιγραφές και σαφείς πληροφορίες αγοράς βοηθούν πελάτες και μηχανές αναζήτησης να κατανοήσουν το κατάστημα. Metadata, canonical, sitemap, structured data που συμφωνούν με το περιεχόμενο και έλεγχος mobile απόδοσης πρέπει να περιλαμβάνονται στο συμφωνημένο τεχνικό scope.</p>"
     "<p>Περιεχόμενο που απαντά σε πραγματικές ερωτήσεις υποστηρίζει και την κατανόηση από συστήματα AI. Η δημοσίευση δεν εγγυάται πωλήσεις, συγκεκριμένη κατάταξη ή αναφορές σε AI απαντήσεις. Η συνεχιζόμενη <a href=\"/seo/\">εργασία SEO/GEO</a> χρειάζεται ξεχωριστό πλάνο, μέτρηση και προσαρμογή.</p>"),
]
EN_SECTIONS = [
    ("megethos", "Which online store fits your business?",
     "<h3>Small catalogue</h3><p>An established platform with clear categories, a reliable checkout, essential payment methods and simple delivery rules may be enough to start. Prioritise useful product pages and easy management over unused features.</p>"
     "<h3>Medium catalogue</h3><p>More categories and variants call for relevant filters, organised search, bulk updates and stock control. Assess whether an ERP or invoicing integration actually reduces manual work.</p>"
     "<h3>Large or complex catalogue</h3><p>Multiple warehouses, B2B journeys, special pricing, large imports and different markets need architecture planning and synchronisation and performance tests. Product count alone does not determine whether custom development is needed; operational complexity matters too.</p>"),
    ("epanalamvanomena", "Monthly and recurring costs to plan for",
     "<p>Separate development from ongoing operations. Not every charge is monthly or applies to every platform. Confirm renewal frequency and who pays each provider.</p>"
     "<ul><li>Domain, hosting or platform subscription and business email.</li><li>Theme, plugin, app and integration service licences.</li><li>Payment provider and bank fees, delivery and returns.</li><li>Maintenance, security updates, backups and support.</li><li>Product entry, photography, copy, translations and order management.</li><li>Ongoing SEO, measurement and optional campaigns if agreed.</li></ul>"),
    ("lathi", "Mistakes that increase development costs",
     "<ul><li>Choosing a platform before checking required integrations and data exports.</li><li>Incomplete product information that needs to be entered again.</li><li>Adding features or redesigning approved work without reviewing scope.</li><li>Skipping checkout, failed-payment, shipping and mobile tests.</li><li>Copying descriptions, confusing categories or changing old URLs without redirects.</li><li>Not separating development from licences, subscriptions and support in the quote.</li></ul>"
     "<p>A clear brief and agreed acceptance criteria reduce rework. The lowest initial quote is not necessarily the lowest overall cost.</p>"),
    ("enarxi", "What do you need to open an e-shop in Greece?",
     "<p>Before taking orders, consult your accountant about a tax identification number (AFM), starting or updating your business activity, appropriate activity codes, invoices and the myDATA reporting obligations that apply to your business. Building a website does not replace tax preparation.</p>"
     "<p>Prepare business details, terms of use and sale, shipping and returns policies, information about withdrawal rights where applicable, a privacy notice and suitable cookie and personal-data handling under GDPR. Requirements depend on your products and markets; ask your accountant and legal adviser to review them.</p>"
     "<p>Prepare images, descriptions, product codes and stock data. Confirm bank or payment provider, courier and ERP accounts and agreements. Test the entire journey from product selection to order confirmation before launch.</p>"),
    ("codehouse", "How Codehouse works and how to request a quote",
     "<p>Codehouse does not have a fixed e-shop price: pricing depends on project size and agreed requirements. We first document your catalogue, audience, payments, shipping, content and integrations, then recommend a suitable solution rather than one package for everyone.</p>"
     "<p>The proposal separates included work, exclusions, third-party dependencies and recurring costs. Agreed scope is followed by design, development, testing and handover with the support agreed for your project. Timing is estimated after reviewing requirements and content readiness.</p>"
     "<p>Explore our <a href=\"/en/services/e-commerce/\">e-commerce development service</a>. For a useful quote, share catalogue size, sample products, required integrations and who will manage the store. The <a href=\"/en/prosfora/\">monthly-subscription website offer</a> covers a business brochure website, not automatically an e-shop.</p>"),
    ("seo-geo", "SEO and GEO start with store structure",
     "<p>Clear categories, useful filters, original descriptions and accurate purchase information help customers and search engines understand your store. Metadata, canonicals, a sitemap, structured data matching visible content and mobile performance checks belong in the agreed technical scope.</p>"
     "<p>Answers to genuine customer questions also support understanding by AI systems. Launching a store does not guarantee sales, rankings or AI citations. Ongoing <a href=\"/en/seo/\">SEO/GEO work</a> needs a separate plan, measurement and adaptation.</p>"),
]
FAQ_EL = [
    ("Πόσο κοστίζει η κατασκευή ενός e-shop;", "Δεν υπάρχει σταθερή τιμή στην Codehouse. Το κόστος εξαρτάται από το μέγεθος του project, τον κατάλογο, το design, την πλατφόρμα, τις πληρωμές, τα μεταφορικά, το περιεχόμενο και τις διασυνδέσεις. Η προσφορά δίνεται μετά την καταγραφή των απαιτήσεων."),
    ("Τι πρέπει να περιλαμβάνει μια προσφορά e-shop;", "Ζήτησε αναλυτικό scope με σχεδιασμό, προϊόντα, checkout, πληρωμές, αποστολές, SEO, δοκιμές και παράδοση. Να ξεχωρίζουν οι εξαιρέσεις, οι χρεώσεις τρίτων και τα επαναλαμβανόμενα έξοδα."),
    ("Είναι πιο οικονομικό ένα template ή custom design;", "Ένα template μπορεί να περιορίσει την αρχική εργασία όταν ταιριάζει στις ανάγκες σου. Ειδικές ροές ή απαιτητικές συνδέσεις μπορεί να χρειάζονται custom ανάπτυξη. Σύγκρινε το συνολικό κόστος λειτουργίας και αλλαγών, όχι μόνο την κατασκευή."),
    ("Ποια έξοδα συνεχίζονται μετά το λανσάρισμα;", "Ανάλογα με τη λύση, υπολόγισε domain, hosting ή συνδρομή πλατφόρμας, άδειες, χρεώσεις πληρωμών, συντήρηση, υποστήριξη και ενημέρωση περιεχομένου. Η συχνότητα και οι όροι συμφωνούνται ανά πάροχο."),
    ("Χρειάζομαι ERP και σύνδεση με myDATA;", "Η ανάγκη ERP εξαρτάται από τη διαχείριση αποθέματος και παραγγελιών. Για τιμολόγηση και υποχρεώσεις myDATA συμβουλεύσου τον λογιστή σου. Οι τεχνικές συνδέσεις επιβεβαιώνονται με τους αντίστοιχους παρόχους πριν κοστολογηθούν."),
    ("Η δωρεάν κατασκευή ιστοσελίδας περιλαμβάνει e-shop;", "Η προσφορά με μηνιαία συνδρομή αφορά εταιρική ιστοσελίδα-βιτρίνα. Ένα e-shop χρειάζεται ξεχωριστή προσφορά λόγω καταλόγου, checkout, πληρωμών, αποστολών και πιθανών διασυνδέσεων."),
]
FAQ_EN = [
    ("How much does e-shop development cost?", "Codehouse has no fixed e-shop price. Cost depends on project size, catalogue, design, platform, payments, shipping, content and integrations. A quote follows a review of your requirements."),
    ("What should an e-shop quote include?", "Request a clear scope covering design, products, checkout, payments, shipping, SEO, testing and handover. Exclusions, third-party fees and recurring expenses should be separate."),
    ("Is a template cheaper than custom design?", "A template can reduce initial work when it fits your needs. Specific journeys or complex integrations may need custom development. Compare operating and change costs, not just the build."),
    ("Which costs continue after launch?", "Depending on the solution, allow for a domain, hosting or platform subscription, licences, payment fees, maintenance, support and content updates. Frequency and terms vary by provider."),
    ("Do I need ERP and myDATA integrations?", "ERP needs depend on stock and order management. Ask your accountant about invoicing and myDATA obligations. Technical integrations must be confirmed with the relevant providers before quoting."),
    ("Does the free website offer include an e-shop?", "The monthly-subscription offer covers a business brochure website. An e-shop needs a separate quote because of its catalogue, checkout, payments, shipping and possible integrations."),
]


def rewrite_cost(prefix):
    el = not prefix
    path = ROOT / (prefix + COST + "index.html")
    source = path.read_text()
    title = ("Κόστος Κατασκευής E-shop: Από τι Εξαρτάται η Τιμή | Codehouse" if el
             else "E-shop Development Cost: What Determines the Price | Codehouse")
    description = ("Από τι εξαρτάται το κόστος κατασκευής e-shop; Προϊόντα, design, πλατφόρμα, διασυνδέσεις και έξοδα λειτουργίας. Ζήτα προσφορά για το project σου." if el
                   else "What determines e-shop development cost? Explore catalogue, design, platform, integrations and ongoing costs. Request a quote for your project.")
    heading = ("Κόστος κατασκευής e-shop: από τι εξαρτάται η τιμή;" if el
               else "E-shop development cost: what determines the price?")
    intro = ("<p><strong>Το κόστος κατασκευής e-shop εξαρτάται από το μέγεθος και τις απαιτήσεις του project.</strong> Το καθορίζουν το πλήθος και οι παραλλαγές προϊόντων, το design, η πλατφόρμα, οι πληρωμές, τα μεταφορικά, οι διασυνδέσεις και το διαθέσιμο περιεχόμενο. Η Codehouse δεν έχει σταθερή τιμή: κάθε ηλεκτρονικό κατάστημα κοστολογείται με ξεχωριστή προσφορά, αφού καταγραφούν οι ανάγκες του.</p>"
             if el else "<p><strong>E-shop development cost depends on the size and requirements of the project.</strong> Product count and variants, design, platform, payments, shipping, integrations and available content determine the work involved. Codehouse has no fixed e-shop price: each online store receives an individual quote after requirements are documented.</p>")
    sections = EL_SECTIONS if el else EN_SECTIONS
    faq = FAQ_EL if el else FAQ_EN
    old_article = re.search(r'<article\b[^>]*>.*?</article>', source, re.S)[0]
    opening = re.match(r'<article\b[^>]*>', old_article)[0]
    meta = re.search(r'<div class="ameta">.*?</div>', old_article, re.S)[0]
    label = "Τελευταία ενημέρωση" if el else "Last updated"
    # Published date remains in ameta and structured data.
    intro_html = (opening + '<p class="bkicker">// <a href="/' + prefix + 'blog/">BLOG</a> · E-SHOP</p>'
                  + f"<h1>{heading}</h1>" + meta
                  + f'<p>{label}: <time datetime="{TODAY}">{TODAY}</time></p>' + intro)
    table_title = "Παράγοντες που επηρεάζουν το κόστος e-shop" if el else "Factors that affect e-shop cost"
    body = f'<h2 id="kostos">{table_title}</h2><div class="legacy-table-scroll" role="region" tabindex="0" aria-label="' + ("Πίνακας παραγόντων κόστους" if el else "Cost factors table") + '"><table><thead><tr><th>' + ("Παράγοντας" if el else "Factor") + "</th><th>" + ("Τι καθορίζει την εργασία" if el else "What determines the work") + "</th></tr></thead><tbody>"
    for gr_name, gr_copy, en_name, en_copy in FACTORS:
        body += "<tr><th scope=\"row\">" + (gr_name if el else en_name) + "</th><td>" + (gr_copy if el else en_copy) + "</td></tr>"
    body += "</tbody></table></div>"
    toc = '<nav class="toc" aria-label="' + ("Περιεχόμενα" if el else "Contents") + '"><b>' + ("Περιεχόμενα" if el else "Contents") + f'</b><a href="#kostos">{table_title}</a>'
    for anchor, name, copy in sections:
        toc += f'<a href="#{anchor}">{name}</a>'
        body += f'<h2 id="{anchor}">{name}</h2>{copy}'
    faq_label = "Συχνές ερωτήσεις για το κόστος e-shop" if el else "E-shop cost FAQ"
    toc += f'<a href="#faq">{faq_label}</a></nav>'
    body += f'<h2 id="faq">{faq_label}</h2><div class="article-faq">'
    body += "".join(f"<details><summary>{escape(q)}</summary><p>{escape(a)}</p></details>" for q, a in faq)
    cta = "Ζήτα προσφορά για το δικό σου e-shop" if el else "Request a quote for your e-shop"
    body += f'</div><div class="cta-box"><h3>{cta}</h3><p>' + (
        "Πες μας τι πουλάς και ποιες λειτουργίες χρειάζεσαι για να σχεδιάσουμε το κατάλληλο project." if el
        else "Tell us what you sell and which features you need so we can plan the right project.") + f'</p><a class="btn" href="/{prefix}contact/">{cta} →</a></div></article>'
    source = source.replace(old_article, intro_html + toc + body, 1)
    def update(data):
        if isinstance(data, dict):
            if data.get("@type") == "FAQPage":
                data["mainEntity"] = [{"@type": "Question", "name": q,
                                      "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]
            if data.get("@type") == "BlogPosting":
                data.update(headline=heading, description=description)
            for value in list(data.values()):
                update(value)
        elif isinstance(data, list):
            for item in data:
                update(item)
    source = schemas(source, update)
    path.write_text(modified(metadata(source, title, description)))


def merge_free(prefix):
    el = not prefix
    diy = ROOT / (prefix + DIY + "index.html")
    source = diy.read_text()
    checklist = (ROOT / (prefix + CHECKLIST + "index.html")).read_text()
    if MERGE_MARK not in source:
        article = re.search(r'<article\b[^>]*>.*?</article>', checklist, re.S)[0]
        content = article[article.index('<h2 id="meaning">'):article.rindex("</article>")]
        # Keep the complete checklist and supporting explanations/FAQ, not its
        # duplicate sales CTA. The destination retains its own shell and CTA.
        content = re.sub(r'<div class="cta-box">.*?</div>', "", content, flags=re.S).rstrip() + "\n"
        source = source.replace("</article>", MERGE_MARK + content + "</article>", 1)
        for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', checklist, re.S):
            def find_faq(item):
                if isinstance(item, dict):
                    if item.get("@type") == "FAQPage":
                        yield item
                    for value in item.values():
                        yield from find_faq(value)
                elif isinstance(item, list):
                    for value in item:
                        yield from find_faq(value)
            for faq in find_faq(json.loads(block)):
                faq.pop("@id", None)
                faq["@context"] = "https://schema.org"
                source = source.replace("</head>", '<script type="application/ld+json">' + json.dumps(faq, ensure_ascii=False) + "</script></head>", 1)
        label = ("Θέλεις επαγγελματική ιστοσελίδα χωρίς αρχικό κόστος;" if el
                 else "Want a professional website without an upfront build cost?")
        source = source.replace("</article>", f'<div class="cta-box"><h3><a href="/{prefix}prosfora/">{label}</a></h3><p>' + (
            "Η δωρεάν κατασκευή αφορά ιστοσελίδα-βιτρίνα με μηνιαία συνδρομή και τους όρους της προσφοράς, όχι δωρεάν λειτουργία για πάντα."
            if el else "The no-upfront-build offer covers a brochure website with a monthly subscription under its terms, not free operation forever.") + "</p></div></article>", 1)
    # Replace the old checklist link with the actual merged section.
    source = source.replace(f'/{prefix}{CHECKLIST}', "#checklist")
    def faq_context(item):
        if isinstance(item, dict):
            if item.get("@type") == "FAQPage":
                item["@context"] = "https://schema.org"
            for value in list(item.values()):
                faq_context(value)
        elif isinstance(item, list):
            for value in item:
                faq_context(value)
    source = schemas(source, faq_context)
    diy.write_text(modified(source))

    offer = ROOT / (prefix + "prosfora/index.html")
    source = offer.read_text()
    old = (ROOT / (prefix + "dorean-istoselida/index.html")).read_text()
    if MERGE_MARK not in source:
        content = MERGE_MARK + '<section class="pf-terms" id="what-free-means"><h2>' + (
            "Τι ισχύει πραγματικά για τη δωρεάν κατασκευή" if el else "What a free website build really means") + "</h2>"
        # Preserve the source's unique decision guidance and FAQ text inside
        # the offer's established typography. Do not import the old layout.
        for section in re.findall(r'<section\b[^>]*aria-labelledby="[^"]+"[^>]*>.*?</section>', old, re.S):
            heading = re.search(r'<h2\b[^>]*>(.*?)</h2>', section, re.S)
            if not heading:
                continue
            if 'aria-labelledby="faq-heading"' in section:
                content += "<h3>" + text(heading[1]) + "</h3>"
                for question, answer in re.findall(r'<summary[^>]*>(.*?)</summary>\s*<p[^>]*>(.*?)</p>', section, re.S):
                    content += "<h4>" + text(question) + "</h4><p>" + answer + "</p>"
            else:
                content += "<h3>" + text(heading[1]) + "</h3>"
                for paragraph in re.findall(r'<p\b[^>]*>(.*?)</p>', section, re.S):
                    # Kicker labels are decorative, not substantive content.
                    if len(text(paragraph)) > 65:
                        content += "<p>" + paragraph + "</p>"
                for listing in re.findall(r'<ul\b[^>]*>.*?</ul>', section, re.S):
                    content += re.sub(r'\sclass="[^"]*"', "", listing)
                for table in re.findall(r'<table\b[^>]*>.*?</table>', section, re.S):
                    content += '<div class="legacy-table-scroll" role="region" tabindex="0" aria-label="' + ("Σύγκριση επιλογών ιστοσελίδας" if el else "Website options comparison") + '">' + table + "</div>"
        label = ("Θέλεις να το φτιάξεις μόνος σου; Δες τον οδηγό δωρεάν ιστοσελίδας με Wix, WordPress.com και Google Sites."
                 if el else "Prefer to build it yourself? Read the free website guide to Wix, WordPress.com and Google Sites.")
        content += f'<p><a href="/{prefix}{DIY}">{label}</a></p></section>'
        source = source.replace("</main>", content + "</main>", 1)
    title = ("Δωρεάν Κατασκευή Ιστοσελίδας με Μηνιαία Συνδρομή | Codehouse" if el
             else "Website Build with a Monthly Subscription | Codehouse")
    desc = ("Δωρεάν κατασκευή εταιρικής ιστοσελίδας με μηνιαία συνδρομή. Δες τι περιλαμβάνει, τους όρους, τη συντήρηση και τις διαφορές από ένα DIY website." if el
            else "A business website with no upfront build fee and a monthly subscription. See inclusions, terms, maintenance and how it differs from DIY.")
    source = metadata(source, title, desc)
    source = schemas(source, lambda data: data.update(dateModified=TODAY) if data.get("@type") == "Offer" else None)
    offer.write_text(source)


def consolidate_links():
    replacements = {}
    for prefix in ("", "en/"):
        replacements["/" + prefix + CHECKLIST] = "/" + prefix + DIY
        replacements["/" + prefix + "dorean-istoselida/"] = "/" + prefix + "prosfora/"
        replacements["/" + prefix + "blog/checklist-dorean-istoselida/"] = "/" + prefix + DIY
    from server_release_prerequisites import REDIRECTS
    redirected = {path for path, _ in REDIRECTS}
    files = []
    for folder in ("blog", "en", "services", "projects", "studio", "contact",
                   "douleies", "seo", "qr-menu", "prosfora", "dimioyrgia-site",
                   "dorean-istoselida", "aporrito"):
        files.extend((ROOT / folder).rglob("*.html"))
    files.append(ROOT / "index.html")
    for path in sorted(set(files)):
        source = path.read_text()
        original = source
        route = "/" + path.relative_to(ROOT).parent.as_posix().strip("/") + "/"
        # Retired HTML is a noindex fallback if nginx has not yet been updated.
        # Actual 301s are supplied by the preview router and production nginx.
        if route in redirected:
            target = dict(REDIRECTS)[route]
            source = re.sub(r'<link\b[^>]*rel="alternate"[^>]*>\s*', "", source)
            source = re.sub(r'<link\b[^>]*rel="canonical"[^>]*>',
                            f'<link rel="canonical" href="{target}">', source)
            source = re.sub(r'<meta\b[^>]*name="robots"[^>]*>', "", source)
            source = source.replace("</head>", '<meta name="robots" content="noindex, follow"></head>', 1)
        # Only link destinations are migrated; no free-text/global URL replace.
        def href(match):
            value = match[2]
            for old, new in replacements.items():
                for base in ("", "https://codehouse.gr", "https://www.codehouse.gr"):
                    if value == base + old or value.startswith(base + old + "#") or value.startswith(base + old + "?"):
                        value = base + new + value[len(base + old):]
                        break
            return match[1] + value + match[3]
        source = re.sub(r'(\bhref=["\'])(.*?)(["\'])', href, source)
        # Remove duplicate Blog cards created by merging two published guides.
        if path in (ROOT / "blog/index.html", ROOT / "en/blog/index.html"):
            # Keep the existing DIY card (the last occurrence) rather than
            # relabelling the old checklist card as a different article.
            cards = re.findall(r'<a\b[^>]*class="bcard"[^>]*>.*?</a>', source, re.S)
            for candidate in cards:
                url = re.search(r'href="([^"]+)"', candidate)
                if url and sum(f'href="{url[1]}"' in other for other in cards) > 1:
                    if any(f'href="{url[1]}"' in other for other in cards[cards.index(candidate) + 1:]):
                        source = source.replace(candidate, "", 1)
            source = re.sub(r"\n[ \t]+\n", "\n\n", source)
            prefix = "en/" if path == ROOT / "en/blog/index.html" else ""
            def cost_card(match):
                card = match[0]
                if f'href="/{prefix}{COST}"' not in card:
                    return card
                label = ("Κόστος κατασκευής e-shop: από τι εξαρτάται η τιμή;" if not prefix
                         else "E-shop development cost: what determines the price?")
                copy = ("Οι παράγοντες που διαμορφώνουν την προσφορά, τα επαναλαμβανόμενα έξοδα και τι χρειάζεται πριν ξεκινήσεις."
                        if not prefix else "What determines your quote, which operating costs to plan for and what to prepare before starting.")
                card = re.sub(r"<h2>.*?</h2>", f"<h2>{label}</h2>", card, count=1, flags=re.S)
                return re.sub(r"<p>.*?</p>", f"<p>{copy}</p>", card, count=1, flags=re.S)
            source = re.sub(r'<a\b[^>]*class="bcard"[^>]*>.*?</a>', cost_card, source, flags=re.S)
        if source != original:
            path.write_text(source)
    sitemap = ROOT / "sitemap.xml"
    tree = ET.parse(sitemap)
    root = tree.getroot()
    ns = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    ET.register_namespace("", ns[1:-1])
    updated = {"/" + prefix + route for prefix in ("", "en/")
               for route in (COST, DIY, "prosfora/", "services/e-commerce/",
                             "blog/", "dimioyrgia-site/",
                             "blog/dorean-ergaleia-aftomatismoi-eleftheros-epaggelmatias/")}
    for entry in list(root):
        url = entry.findtext(ns + "loc")
        route = url.removeprefix("https://codehouse.gr")
        if route in redirected:
            root.remove(entry)
        elif route in updated:
            entry.find(ns + "lastmod").text = TODAY
    ET.indent(tree, space="  ")
    tree.write(sitemap, encoding="UTF-8", xml_declaration=True)


def main():
    for prefix in ("", "en/"):
        rewrite_cost(prefix)
        merge_free(prefix)
    consolidate_links()
    print("Updated bilingual hand-authored guides, offers, links and sitemap; no Git or deployment operations.")


if __name__ == "__main__":
    main()
