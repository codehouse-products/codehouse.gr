#!/usr/bin/env python3
"""Generate the bilingual, indexable Codehouse studio routes from central data."""
from pathlib import Path
import html, json, re

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT

services=[
("web-design","WEB DESIGN & DEVELOPMENT","WEB DESIGN & DEVELOPMENT","Websites με ξεχωριστή ταυτότητα.","Websites with a distinct identity.","Σχεδιάζουμε και αναπτύσσουμε ιστοσελίδες που κάνουν την ταυτότητα μιας επιχείρησης κατανοητή, ξεχωριστή και εύχρηστη σε κάθε οθόνη.","We design and build websites that make a business identity clear, distinctive and easy to use on every screen.","Στρατηγική περιεχομένου, UX και UI design, responsive υλοποίηση, CMS και τεχνικό SEO.","Content structure, UX and UI design, responsive development, CMS and technical SEO.","Κατανόηση → δομή → σχεδιασμός → ανάπτυξη → έλεγχος και παράδοση.","Discovery → structure → design → development → testing and handover.",["high-hope","gerakos","kc-travel","akri"]),
("e-commerce","E-COMMERCE","E-COMMERCE","Ηλεκτρονικά καταστήματα με ολοκληρωμένη λειτουργικότητα.","Online stores with considered functionality.","Δημιουργούμε ηλεκτρονικά καταστήματα με σαφή πλοήγηση, προσεγμένη παρουσίαση προϊόντων και τις λειτουργίες που χρειάζεται η επιχείρησή σου.","We create online stores with clear navigation, considered product presentation and the functionality your business needs.","Δομή καταλόγου, σχεδιασμός σελίδων, καλάθι και checkout όπου απαιτούνται, mobile έλεγχος και εκπαίδευση.","Catalog structure, page design, cart and checkout where required, mobile testing and handover.","Χαρτογράφηση προϊόντων → ροές αγοράς → σχεδιασμός → υλοποίηση → έλεγχος.","Product mapping → shopping flows → design → development → testing.",[]),
("custom-apps","CUSTOM APPS & SOFTWARE","CUSTOM APPS & SOFTWARE","Εφαρμογές γύρω από τις ανάγκες της επιχείρησης.","Software shaped around business needs.","Αναπτύσσουμε προσαρμοσμένες εφαρμογές και εργαλεία που οργανώνουν συγκεκριμένες εργασίες και κάνουν την καθημερινή λειτουργία πιο ξεκάθαρη.","We develop tailored applications and tools that organise specific tasks and bring clarity to day-to-day operations.","Ανάλυση απαιτήσεων, ροές χρηστών, interfaces, integrations που ορίζονται στο scope και τεκμηρίωση.","Requirements mapping, user flows, interfaces, integrations defined in scope and documentation.","Ανακάλυψη → προδιαγραφές → πρωτότυπο → ανάπτυξη → δοκιμή και υποστήριξη.","Discovery → specification → prototype → development → testing and support.",[]),
("ai-automations","AI & AUTOMATIONS","AI & AUTOMATIONS","Σύνδεση εργαλείων και αυτοματοποίηση διαδικασιών.","Connected tools and automated workflows.","Εντοπίζουμε επαναλαμβανόμενες διαδικασίες και σχεδιάζουμε αυτοματισμούς που συνδέουν τα εργαλεία που ήδη χρησιμοποιεί η ομάδα σου.","We identify repetitive workflows and design automations that connect the tools your team already uses.","Χαρτογράφηση διαδικασιών, ορισμός triggers και κανόνων, integrations, έλεγχος και σαφής τεκμηρίωση.","Workflow mapping, trigger and rule definition, integrations, testing and clear documentation.","Καταγραφή διαδικασίας → επιλογή σημείων αυτοματοποίησης → σύνδεση → δοκιμή.","Workflow audit → automation opportunities → connection → testing.",[""]),
("booking-systems","BOOKING & DIGITAL SYSTEMS","BOOKING & DIGITAL SYSTEMS","Κρατήσεις, dashboards και εργαλεία διαχείρισης.","Bookings, dashboards and management tools.","Σχεδιάζουμε ψηφιακά συστήματα κρατήσεων και λειτουργικά interfaces, προσαρμοσμένα στον τρόπο που εξυπηρετείς πελάτες και οργανώνεις την ομάδα σου.","We design booking systems and operational interfaces tailored to how you serve customers and organise your team.","Ροή κράτησης, φόρμες, παρουσίαση επιλογών, προσαρμοσμένα dashboards όπου περιλαμβάνονται στο scope.","Booking flows, forms, option presentation and custom dashboards when included in scope.","Χαρτογράφηση χρηστών → σχεδιασμός ροών → υλοποίηση → δοκιμές σε πραγματικά σενάρια.","User mapping → flow design → development → real-scenario testing.",["kc-travel"]),
("branding","BRANDING & DIGITAL MARKETING","BRANDING & DIGITAL MARKETING","Οπτική ταυτότητα, περιεχόμενο και καμπάνιες.","Visual identity, content and campaigns.","Διαμορφώνουμε ψηφιακή ταυτότητα με συνέπεια από την πρώτη εντύπωση έως το περιεχόμενο και τα σημεία επαφής της επιχείρησης.","We shape a coherent digital identity from first impression through content and business touchpoints.","Κατεύθυνση ταυτότητας, οπτικό σύστημα, εφαρμογές για ψηφιακά μέσα και σχεδιασμός περιεχομένου.","Identity direction, visual system, digital applications and content design.","Κατανόηση brand → κατεύθυνση → σύστημα → εφαρμογές και παραδοτέα.","Brand discovery → direction → system → applications and deliverables.",[])
]
projects=[
("high-hope","HIGH HOPE","highhopeathens.gr","Specialty coffee · Glyfada","Specialty coffee · Glyfada","Website & QR menu","Ιστότοπος και QR μενού","Σχεδιάσαμε την ψηφιακή παρουσία του High Hope, specialty coffee spot στη Γλυφάδα, μαζί με το QR menu του. Η δουλειά συνδέει την εικόνα του brand με καθαρή πρόσβαση στο μενού.","We designed the digital presence for High Hope, a specialty coffee spot in Glyfada, together with its QR menu. The work connects the brand’s visual character with clear access to the menu.","highhopeathens.gr"),
("gerakos","GERAKOS","gerakos.gr","Παραδοσιακό σουβλάκι · Σαντορίνη","Traditional souvlaki · Santorini","Website, menu & contact","Ιστότοπος, μενού και επικοινωνία","Σχεδιάσαμε την ιστοσελίδα του Gerakos, παραδοσιακού ψητοπωλείου στη Σαντορίνη, με παρουσίαση του εστιατορίου, του μενού και των στοιχείων επικοινωνίας.","We designed the website for Gerakos, a traditional souvlaki restaurant in Santorini, presenting the restaurant, its menu and contact information.","gerakos.gr"),
("kc-travel","KC TRAVEL","kctravel.gr","Private transfers · Santorini","Private transfers · Santorini","Website & booking interface","Ιστότοπος και interface κράτησης","Για την KC Travel σχεδιάσαμε ιστότοπο ιδιωτικών μεταφορών στη Σαντορίνη και interface κράτησης που παρουσιάζει τη διαδρομή της υπηρεσίας με σαφή βήματα.","For KC Travel, we designed a website for private transfers in Santorini and a booking interface that presents the service flow in clear steps.","kctravel.gr"),
("akri","AKRI","akriprojects.gr","Matcha café, boulangerie, workshops & concept store · Akrotiri, Santorini","Matcha café, boulangerie, workshops & concept store · Akrotiri, Santorini","Website presentation","Παρουσίαση website","Σχεδιάσαμε την ιστοσελίδα του Akri, ενός matcha café, boulangerie, χώρου workshops και concept store στο Ακρωτήρι της Σαντορίνης, παρουσιάζοντας τον χώρο και τις δραστηριότητές του.","We designed the website for Akri, a matcha café, boulangerie, workshop space and concept store in Akrotiri, Santorini, presenting the venue and its activities.","akriprojects.gr")
]
service_visuals=["assets/studio/images/highhope-desktop.webp","assets/studio/images/kc-travel-desktop.webp","assets/studio/images/codehouse-desktop.webp","assets/studio/images/highhope-desktop.webp","assets/studio/images/kc-travel-desktop.webp","assets/studio/images/codehouse-desktop.webp"]
manifest_path=ROOT/"assets/studio/data.json"
had_project_facts=manifest_path.exists() and all("services" in item for item in json.loads(manifest_path.read_text()).get("projects",[]))
if manifest_path.exists():
    saved=json.loads(manifest_path.read_text())
    saved_services=saved.get("services",[])
    if len(saved_services)==len(service_visuals) and any(item.get("image")!="assets/studio/images/codehouse-desktop.webp" for item in saved_services):
        service_visuals=[item.get("image",default) for item,default in zip(saved_services,service_visuals)]
project_facts={
"high-hope":{"goal":{"el":"Να γίνει η ταυτότητα του High Hope και η πρόσβαση στο μενού ευανάγνωστες σε ψηφιακή μορφή.","en":"Present High Hope’s identity and make its menu easy to access digitally."},"solution":{"el":"Ιστότοπος και QR μενού που φέρνουν την παρουσίαση του specialty coffee spot και το μενού στην ίδια ψηφιακή εμπειρία.","en":"A website and QR menu bringing the specialty coffee spot’s presentation and menu into one digital experience."},"services":["web-design"]},
"kc-travel":{"goal":{"el":"Να παρουσιάζονται καθαρά οι ιδιωτικές μεταφορές στη Σαντορίνη και τα βήματα κράτησης.","en":"Clearly present private Santorini transfers and the steps to book."},"solution":{"el":"Ιστότοπος και interface κράτησης που οργανώνουν τις πληροφορίες της υπηρεσίας σε σαφή βήματα.","en":"A website and booking interface that organise the service information into clear steps."},"services":["web-design","booking-systems"]},
"gerakos":{"goal":{"el":"Να παρουσιάζονται το παραδοσιακό ψητοπωλείο, το μενού και τα στοιχεία επικοινωνίας.","en":"Present the traditional souvlaki restaurant, its menu and contact information."},"solution":{"el":"Ιστότοπος με σαφή παρουσίαση του εστιατορίου, του μενού και της επικοινωνίας.","en":"A website clearly presenting the restaurant, its menu and contact information."},"services":["web-design"]},
"akri":{"goal":{"el":"Να παρουσιάζεται ψηφιακά ο χώρος και οι διαφορετικές δραστηριότητες του Akri.","en":"Present Akri’s venue and its different activities online."},"solution":{"el":"Ιστότοπος που παρουσιάζει το matcha café, τη boulangerie, τα workshops και το concept store στο Ακρωτήρι.","en":"A website presenting the matcha café, boulangerie, workshops and concept store in Akrotiri."},"services":["web-design"]}}
DATA={"services":[{"slug":s[0],"name":{"el":s[1],"en":s[2]},"descriptor":{"el":s[3],"en":s[4]},"description":{"el":s[5],"en":s[6]},"includes":{"el":s[7],"en":s[8]},"process":{"el":s[9],"en":s[10]},"projects":s[11],"image":service_visuals[i]} for i,s in enumerate(services)],
"projects":[{"slug":p[0],"name":p[1],"domain":p[2],"category":{"el":p[3],"en":p[4]},"deliverable":{"el":p[6],"en":p[5]},"description":{"el":p[7],"en":p[8]},"url":"https://"+p[9],"desktop":f"assets/studio/images/{'highhope' if p[0]=='high-hope' else p[0]}-desktop.webp","mobile":f"assets/studio/images/{'highhope' if p[0]=='high-hope' else p[0]}-mobile.webp","goal":project_facts[p[0]]["goal"],"solution":project_facts[p[0]]["solution"],"services":project_facts[p[0]]["services"],"visible":True,"caseStudyPath":"/projects/"+p[0]+"/","cover":f"assets/studio/images/project-{'highhope' if p[0]=='high-hope' else p[0]}.webp","coverWidth":819 if p[0]!="high-hope" else 1122,"coverHeight":1024 if p[0]!="high-hope" else 1402,"gallery":[]} for p in projects],
"images":{"hero":"assets/studio/images/codehouse-desktop.webp","logoBlack":"assets/studio/logo-wordmark-black.svg","logoWhite":"assets/studio/logo-wordmark-white.svg","favicon":"assets/studio/favicon.svg"},
"contact":{"email":"hello@codehouse.gr","phone":"+30 698 680 4138","services":["web","ecommerce","apps","ai","booking","branding"]}}
DATA["images"].setdefault("heroMode","screen")
for item in DATA["projects"]:
    item.setdefault("cover",item["desktop"])
    if item.get("visible"):
        item["cover"]=f'assets/studio/images/project-{"highhope-live" if item["slug"]=="high-hope" else item["slug"]}.webp'
        item.setdefault("coverWidth",819 if item["slug"]!="high-hope" else 1122)
        item.setdefault("coverHeight",1024 if item["slug"]!="high-hope" else 1402)
        item.setdefault("gallery",[])
        item.setdefault("desktopWidth",1440)
        item.setdefault("desktopHeight",1000)
        item.setdefault("mobileWidth",390)
        item.setdefault("mobileHeight",740 if item["slug"] in {"gerakos","akri"} else 844)

T={
"el":{"services":"Υπηρεσίες","projects":"Έργα","studio":"Studio","contact":"Επικοινωνία","start":"Ξεκίνα ένα project","heroLabel":"THINK BEYOND THE ORDINARY.","heroDesc":"Σχεδιάζουμε websites, custom εφαρμογές και ψηφιακά συστήματα που συνδυάζουν αισθητική, τεχνολογία και πραγματική λειτουργικότητα.","selected":"Επιλεγμένα έργα","aboutLabel":"ABOUT CODEHOUSE","aboutTitle":"ΕΚΕΙ ΠΟΥ Η ΔΗΜΙΟΥΡΓΙΚΟΤΗΤΑ ΣΥΝΑΝΤΑ ΤΗΝ ΤΕΧΝΟΛΟΓΙΑ.","about":"Η Codehouse είναι ένα Software & Digital Systems Studio. Δημιουργούμε websites, e-shops, custom εφαρμογές και αυτοματισμούς γύρω από τις ανάγκες κάθε επιχείρησης. Συνδέουμε τον σχεδιασμό με την ανάπτυξη και το marketing, δημιουργώντας μια ολοκληρωμένη ψηφιακή παρουσία και εργαλεία που υποστηρίζουν την καθημερινή λειτουργία της επιχείρησής σου.","meet":"ΓΝΩΡΙΣΕ ΤΟ STUDIO","digitalLabel":"DIGITAL WITHOUT LIMITS","digitalTitle":"ΙΔΕΕΣ ΧΩΡΙΣ ΣΥΝΟΡΑ. ΨΗΦΙΑΚΕΣ ΕΜΠΕΙΡΙΕΣ ΜΕ ΤΑΥΤΟΤΗΤΑ.","digital":"Συνεργαζόμαστε με επιχειρήσεις στην Ελλάδα και το εξωτερικό, σχεδιάζοντας λύσεις γύρω από το brand, το κοινό και τις πραγματικές τους ανάγκες.","all":"ΟΛΑ ΤΑ ΕΡΓΑ","view":"ΔΕΣ ΤΟ PROJECT","website":"ΔΕΣ ΤΟ WEBSITE","cta":"LET’S BUILD SOMETHING THAT MATTERS.","ctaSub":"Έχεις μια ιδέα; Ας της δώσουμε μορφή.","ctaButton":"ΞΕΚΙΝΑ ΕΝΑ PROJECT","process":"ΠΩΣ ΔΟΥΛΕΥΟΥΜΕ","includes":"ΤΙ ΠΕΡΙΛΑΜΒΑΝΕΙ","related":"ΣΧΕΤΙΚΑ ΕΡΓΑ","goal":"ΣΤΟΧΟΣ","solution":"Η ΛΥΣΗ","next":"ΕΠΟΜΕΝΟ PROJECT","name":"Όνομα","company":"Εταιρεία","email":"Email","kind":"Είδος υπηρεσίας","description":"Περιγραφή project","budget":"Εύρος budget (προαιρετικό)","send":"ΑΠΟΣΤΟΛΗ ΜΗΝΥΜΑΤΟΣ","select":"Επίλεξε υπηρεσία","budgetOptions":["Δεν έχω ορίσει ακόμη","Έως €2.500","€2.500–€5.000","€5.000–€10.000","€10.000+"],"follow":"Δεν υπάρχουν δημοσιευμένα κανάλια","legal":"Νομικά","serviceTitle":"Οι υπηρεσίες μας","projectsTitle":"Επιλεγμένα έργα","studioTitle":"Ένα studio ανάμεσα στη δημιουργικότητα και την τεχνολογία.","contactTitle":"Ας δώσουμε μορφή στην ιδέα σου.","websiteTitle":"Ιστότοπος","mobileTitle":"Κινητή εμπειρία","serviceCTA":"ΣΥΖΗΤΗΣΕ ΤΟ PROJECT ΣΟΥ","detailIncludes":"Τι περιλαμβάνει","emptyRelated":"Περισσότερα έργα σύντομα."},
"en":{"services":"Services","projects":"Projects","studio":"Studio","contact":"Contact","start":"Start a project","heroLabel":"THINK BEYOND THE ORDINARY.","heroDesc":"We design websites, custom applications and digital systems that bring together aesthetics, technology and real utility.","selected":"Selected projects","aboutLabel":"ABOUT CODEHOUSE","aboutTitle":"WHERE CREATIVITY MEETS TECHNOLOGY.","about":"Codehouse is a Software & Digital Systems Studio. We create websites, e-commerce, custom applications and automations around the needs of each business. We connect design with development and marketing, building a coherent digital presence and tools that support the everyday work of your business.","meet":"MEET THE STUDIO","digitalLabel":"DIGITAL WITHOUT LIMITS","digitalTitle":"IDEAS WITHOUT BORDERS. DIGITAL EXPERIENCES WITH IDENTITY.","digital":"We work with businesses in Greece and abroad, shaping solutions around their brand, audience and real needs.","all":"ALL PROJECTS","view":"VIEW PROJECT","website":"VIEW WEBSITE","cta":"LET’S BUILD SOMETHING THAT MATTERS.","ctaSub":"Have an idea? Let’s give it form.","ctaButton":"START A PROJECT","process":"HOW WE WORK","includes":"WHAT’S INCLUDED","related":"RELATED PROJECTS","goal":"THE GOAL","solution":"THE WORK","next":"NEXT PROJECT","name":"Name","company":"Company","email":"Email","kind":"Service type","description":"Project description","budget":"Budget range (optional)","send":"SEND MESSAGE","select":"Select a service","budgetOptions":["Not decided yet","Up to €2,500","€2,500–€5,000","€5,000–€10,000","€10,000+"],"follow":"No published channels","legal":"Legal","serviceTitle":"Our services","projectsTitle":"Selected projects","studioTitle":"A studio where creativity meets technology.","contactTitle":"Let’s give your idea form.","websiteTitle":"Website","mobileTitle":"Mobile experience","serviceCTA":"LET’S DISCUSS YOUR PROJECT","detailIncludes":"What’s included","emptyRelated":"More projects soon."}
}
def merge_defaults(default,saved):
    if isinstance(default,dict) and isinstance(saved,dict):
        merged={key:merge_defaults(value,saved.get(key,value)) for key,value in default.items()}
        merged.update({key:value for key,value in saved.items() if key not in default})
        return merged
    if isinstance(default,list) and isinstance(saved,list):
        if default and all(isinstance(item,dict) and "slug" in item for item in default):
            old={item["slug"]:item for item in saved if isinstance(item,dict) and "slug" in item}
            known={item["slug"] for item in default}
            merged=[merge_defaults(item,old.get(item["slug"],item)) for item in default]
            for item in saved:
                if isinstance(item,dict) and "slug" in item and item["slug"] not in known:
                    archived=dict(item)
                    archived.setdefault("visible",False)
                    merged.append(archived)
            return merged
        return saved
    return saved
if manifest_path.exists():
    saved_manifest=json.loads(manifest_path.read_text())
    saved_services=saved_manifest.get("services",[])
    if saved_services and all(item.get("image")=="assets/studio/images/codehouse-desktop.webp" for item in saved_services):
        for item in saved_services:item.pop("image",None)
    DATA=merge_defaults(DATA,{key:value for key,value in saved_manifest.items() if key!="translations"})
    T=merge_defaults(T,saved_manifest.get("translations",{}))
    # Homepage selection is deliberate and never inherits legacy cover overrides.
    DATA["homeProjects"]=[{"slug":item["slug"]} for item in DATA["projects"] if item.get("visible")]
for item in DATA["projects"]:
    if item.get("visible"):
        item["cover"]=f'assets/studio/images/project-{"highhope-live" if item["slug"]=="high-hope" else item["slug"]}.webp'
        item.setdefault("coverWidth",1122 if item["slug"]=="high-hope" else 819)
        item.setdefault("coverHeight",1402 if item["slug"]=="high-hope" else 1024)
        item.setdefault("desktopWidth",1440)
        item.setdefault("desktopHeight",1000)
        item.setdefault("mobileWidth",390)
        item.setdefault("mobileHeight",740 if item["slug"] in {"gerakos","akri"} else 844)
if [item["slug"] for item in DATA["projects"] if item.get("visible")] != ["high-hope","gerakos","kc-travel","akri"]:
    raise ValueError("The visible portfolio must be High Hope, Gerakos, KC Travel and Akri, in that order")
for service in DATA["services"]:
    service["projects"]=[project["slug"] for project in DATA["projects"] if project.get("visible") and service["slug"] in project.get("services",[])]
if not had_project_facts:
    factual_projects={"web-design":["high-hope","gerakos","kc-travel","akri"],"e-commerce":[],"custom-apps":[],"ai-automations":[],"booking-systems":["kc-travel"],"branding":[]}
    for item in DATA["services"]:item["projects"]=factual_projects[item["slug"]]
manifest_path.write_text(json.dumps({**DATA,"translations":T},ensure_ascii=False,indent=2)+"\n")
def esc(s):return html.escape(str(s),quote=True)
def page_url(path,lang):
    return "/en"+path if lang=="en" else path
def route(path,lang): return page_url(path,lang)
def asset_prefix(depth): return "../"*depth
def document(path,lang,title,desc,body,depth):
    canonical="https://codehouse.gr"+route(path,lang)
    opposite="en" if lang=="el" else "el"
    altpath=page_url(path,opposite)
    prefix=asset_prefix(depth)
    return f'''<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)} · Codehouse</title><meta name="description" content="{esc(desc)}"><link rel="canonical" href="{canonical}"><link rel="alternate" hreflang="el" href="https://codehouse.gr{page_url(path,'el')}"><link rel="alternate" hreflang="en" href="https://codehouse.gr{page_url(path,'en')}"><link rel="alternate" hreflang="x-default" href="https://codehouse.gr{page_url(path,'el')}"><meta property="og:type" content="website"><meta property="og:locale" content="{'el_GR' if lang=='el' else 'en_US'}"><meta property="og:title" content="{esc(title)} · Codehouse"><meta property="og:description" content="{esc(desc)}"><meta property="og:url" content="{canonical}"><meta property="og:image" content="https://codehouse.gr/assets/studio/images/codehouse-desktop.webp"><link rel="icon" href="{prefix}assets/studio/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="{prefix}assets/studio/studio.css"><script defer src="{prefix}assets/studio/studio.js"></script></head><body>{header(lang,path,depth)}{body}{footer(lang,depth)}</body></html>'''
def header(lang,path,depth):
    t=dict(T[lang],blog="Blog"); pre=asset_prefix(depth); labels=[("services",route("/services/",lang)),("projects",route("/projects/",lang)),("studio",route("/studio/",lang)),("blog",route("/blog/",lang)),("contact",route("/contact/",lang))]
    switch=route(path,"en" if lang=="el" else "el")
    nav="".join(f'<a href="{u}">{t[k]}</a>' for k,u in labels)
    return f'''<header class="site-header"><a class="brand" href="{route('/',lang)}" aria-label="Codehouse home"><img src="{pre}{DATA["images"]["logoBlack"]}" alt="Codehouse"></a><nav class="nav-links" aria-label="Main navigation">{nav}<a class="header-cta" href="{route('/contact/',lang)}">{t['start']}</a><span class="language"><a class="{'active' if lang=='el' else ''}" href="{route(path,'el')}">GR</a><a class="{'active' if lang=='en' else ''}" href="{route(path,'en')}">EN</a></span></nav><button class="menu-toggle" aria-expanded="false" aria-controls="mobile-menu">MENU +</button></header><nav class="menu-panel" id="mobile-menu" aria-hidden="true" aria-label="Mobile navigation"><div class="menu-top"><span class="eyebrow">CODEHOUSE / NAVIGATION</span><span class="menu-lang"><a href="{route(path,'el')}">GR</a><a href="{route(path,'en')}">EN</a></span><button class="menu-close" style="font:10px var(--mono);border:0;background:none;padding:7px;cursor:pointer" type="button" aria-label="Close menu">CLOSE ×</button></div>{nav}<a href="{route('/contact/',lang)}">{t['start']}</a></nav>'''
def footer(lang,depth):
    t=T[lang]; p=asset_prefix(depth)
    groups=[("SERVICES",[("Web design","/services/web-design/"),("E-commerce","/services/e-commerce/"),("Booking","/services/booking-systems/")]),("STUDIO",[(t["studio"],"/studio/"),("Blog","/blog/")]),("CONTACT",[(t["contact"],"/contact/")]),("FOLLOW",[(t["follow"],None)]),("LEGAL",[("Privacy","/aporrito/")])]
    cols="".join(f'<div><h3>{a}</h3>'+(''.join(f'<a href="{route(u,lang)}">{esc(label)}</a>' if u else f'<p>{esc(label)}</p>' for label,u in links) or '<p>—</p>')+'</div>' for a,links in groups)
    return f'''<section class="cta-band"><div><span class="eyebrow">{t['ctaSub']}</span><h2>{t['cta']}</h2></div><a class="button-link" href="{route('/contact/',lang)}">{t['ctaButton']} <span class="arrow">↗</span></a></section><footer class="site-footer"><div class="footer-top"><a href="{route('/',lang)}"><img class="footer-logo" src="{p}{DATA["images"]["logoWhite"]}" alt="Codehouse"></a><div class="footer-cols">{cols}</div></div><div class="footer-bottom"><span>© CODEHOUSE · {lang.upper()}</span><a href="{route('/contact/',lang)}">HELLO@CODEHOUSE.GR</a><span>GREECE · DIGITAL STUDIO</span></div></footer>'''
def project_cards(lang,depth,which=None,items=None):
    t=T[lang]; p=asset_prefix(depth)
    if items is None:
        items=[x for x in DATA["projects"] if x.get("visible") and (which is None or x["slug"] in which)]
    else:
        items=[x for x in items if x.get("visible",True)]
    cards=""
    for x in items:
        im=asset_prefix(depth)+x.get("cover",x["desktop"])
        cover_alt=esc(x.get("coverAlt",{}).get(lang,x["name"]+(" — εξώφυλλο έργου" if lang=="el" else " — project cover")))
        case_path=x.get("caseStudyPath",'/projects/'+x['slug']+'/')
        card_url=route(case_path,lang) if case_path else x["url"]
        card_target='' if case_path else ' target="_blank" rel="noopener"'
        card_label=t["view"] if case_path else t["website"]
        case_link=f'<a class="project-link" href="{route(case_path,lang)}">{t["view"]} <span class="arrow">↗</span></a>' if case_path else ''
        cards+=f'''<article class="project-card"><a href="{card_url}"{card_target} aria-label="{card_label} {x['name']}"><div class="project-image"><img src="{im}" alt="{cover_alt}" loading="lazy" width="{x.get('coverWidth',1440)}" height="{x.get('coverHeight',1000)}"></div></a><div class="project-info"><div><h3>{x['name']}</h3><p>{x['category'][lang]} · {x['domain']}</p></div><span class="tiny">{x['deliverable'][lang]}</span><div class="project-actions"><a class="project-link" href="{x['url']}" target="_blank" rel="noopener">{t['website']} <span class="arrow">↗</span></a>{case_link}</div></div></article>'''
    return cards
def project_gallery(project,lang,depth):
    images=[{"image":project["cover"],"width":project.get("coverWidth",1440),"height":project.get("coverHeight",1000),"alt":project.get("coverAlt",{})}]+project["gallery"]
    slides="".join(
        f'<img data-gallery-slide src="{asset_prefix(depth)}{image["image"]}" alt="{esc(image["alt"].get(lang,project["name"]))}" loading="lazy" decoding="async" width="{image["width"]}" height="{image["height"]}"'+(' hidden' if index else '')+'>'
        for index,image in enumerate(images)
    )
    previous="Προηγούμενη εικόνα" if lang=="el" else "Previous image"
    following="Επόμενη εικόνα" if lang=="el" else "Next image"
    label="εικόνες του project" if lang=="el" else "project images"
    error="Δεν φορτώθηκε η εικόνα. Δοκίμασε ξανά." if lang=="el" else "The image could not load. Please try again."
    return f'''<div class="project-image project-gallery" data-project-gallery data-gallery-error="{esc(error)}" role="region" aria-roledescription="carousel" aria-label="{esc(project["name"])} — {label}"><a class="project-gallery-link" href="{route('/projects/'+project["slug"]+'/',lang)}" aria-label="{T[lang]["view"]} {esc(project["name"])}">{slides}</a><div class="project-gallery-controls" hidden><button class="project-gallery-button" type="button" data-gallery-direction="prev" aria-label="{previous} — {esc(project["name"])}"><span aria-hidden="true">←</span></button><span class="project-gallery-position" data-gallery-position aria-live="polite" aria-atomic="true">01 / {len(images):02}</span><button class="project-gallery-button" type="button" data-gallery-direction="next" aria-label="{following} — {esc(project["name"])}"><span aria-hidden="true">→</span></button></div><p class="project-gallery-error" data-gallery-status role="alert" hidden></p></div>'''
def service_image(service,lang,depth,lazy=True):
    alt=service.get("imageAlt",{}).get(lang,service["name"][lang])
    loading='loading="lazy"' if lazy else 'fetchpriority="high"'
    return f'<img {loading} decoding="async" src="{asset_prefix(depth)}{service["image"]}" alt="{esc(alt)}" width="{service.get("imageWidth",1440)}" height="{service.get("imageHeight",1000)}">'

def home(lang):
    t=T[lang]; services_html=""; assetroot="../" if lang=="en" else ""; root_depth=1 if lang=="en" else 0
    for i,s in enumerate(DATA["services"]):
        services_html+=f'''<a class="service-card" href="{route('/services/'+s['slug']+'/',lang)}"><div class="service-image">{service_image(s,lang,root_depth)}</div><div class="service-head"><div><span class="mono">[{i+1:02}]</span><h3 class="service-title">{esc(s['name'][lang])}</h3><p>{esc(s['descriptor'][lang])}</p></div><span class="arrow" aria-hidden="true">↗</span></div></a>'''
    body=f'''<main><section class="hero"><div class="hero-art"><img class="hero-image" src="{assetroot}{DATA['images']['hero']}" alt="" fetchpriority="high"><img class="hero-logo" src="{assetroot}{DATA['images']['logoBlack']}" alt="Codehouse"></div><div class="hero-bottom"><div class="hero-intro"><span class="eyebrow">{t['heroLabel']}</span><p>{t['heroDesc']}</p></div><a class="hero-feature" href="{route('/projects/high-hope/',lang)}"><span class="eyebrow">SELECTED PROJECT</span><strong>HIGH HOPE</strong><span class="mono">WEBSITE & QR MENU ↗</span></a></div></section><section class="section about-grid reveal"><div><span class="eyebrow">{t['aboutLabel']}</span><h1>{t['aboutTitle']}</h1></div><div class="about-copy"><p>{t['about']}</p><a class="text-link" href="{route('/studio/',lang)}">{t['meet']} <span class="arrow">↗</span></a></div></section><section class="section"><div class="section-heading"><div><span class="eyebrow">01 / WHAT WE DO</span><h2>{t['services']}</h2></div><div class="service-controls"><button class="slider-button" aria-label="Previous services" data-rail-control="#service-rail" data-dir="prev">←</button><button class="slider-button" aria-label="Next services" data-rail-control="#service-rail" data-dir="next">→</button></div></div><div id="service-rail" class="horizontal-rail service-rail" tabindex="0">{services_html}</div><p class="mono" style="margin-top:20px">01 — 06 &nbsp; / &nbsp; {t['services']}</p></section><section class="section statement"><div><span class="eyebrow">{t['digitalLabel']}</span><h2>{t['digitalTitle']}</h2></div><p class="body-copy">{t['digital']}<br><br>{'Athens time' if lang=='en' else 'Ώρα Αθήνας'} <span data-athens-clock>—</span></p></section><section class="section" style="padding-top:35px"><div class="section-heading"><div><span class="eyebrow">02 / SELECTED WORK</span><h2>{t['selected']}</h2></div><a class="text-link" href="{route('/projects/',lang)}">{t['all']} <span class="arrow">↗</span></a></div><div class="horizontal-rail" tabindex="0">{project_cards(lang,root_depth)}</div></section><section class="section" style="padding-top:50px"><div class="section-heading"><div><span class="eyebrow">03 / THE STUDIO</span><h2>{t['studioTitle']}</h2></div></div><div class="about-grid"><p class="body-copy">{t['about']}</p><a class="text-link" href="{route('/studio/',lang)}">{t['meet']} <span class="arrow">↗</span></a></div></section></main>'''
    body=body.replace(f'<h1>{t["aboutTitle"]}</h1>',f'<h1 class="border-t-[0px] border-r-[0px] border-b-[0px] border-l-[0px] text-[color:var(--ink)] font-extrabold">{t["aboutTitle"]}</h1>',1)
    originals={project["slug"]:project for project in DATA["projects"]}
    home_projects=[{**originals.get(project["slug"],{}),**project} for project in DATA["homeProjects"]]
    if [project["slug"] for project in home_projects] != ["high-hope","gerakos","kc-travel","akri"]:
        raise ValueError("The homepage must feature High Hope, Gerakos, KC Travel and Akri in order")
    body=body.replace(project_cards(lang,root_depth),project_cards(lang,root_depth,items=home_projects),1)
    work_title="Οι τελευταίες μας δουλειές" if lang=="el" else "Our latest work"
    body=body.replace(f'<h2>{t["selected"]}</h2>',f'<h2>{work_title}</h2>',1)
    body=body.replace("02 / SELECTED WORK","02 / LATEST WORK",1)
    body=body.replace('<span class="eyebrow">SELECTED PROJECT</span>','<span class="eyebrow">LAST PROJECT</span>',1)
    body=body.replace(f'href="{route("/projects/",lang)}">{t["all"]}',f'href="{route("/douleies/",lang)}">{t["all"]}',1)
    body=body.replace(f'<a class="text-link" href="{route("/studio/",lang)}">',f'<a class="text-link text-[15px]" href="{route("/studio/",lang)}">',1)
    if DATA["images"].get("heroLogo"):
        body=body.replace(f'src="{assetroot}{DATA["images"]["logoBlack"]}"',f'src="{assetroot}{DATA["images"]["heroLogo"]}"',1)
    if DATA["images"].get("heroMode")=="photo" and DATA["images"].get("hero"):
        body=body.replace(f'src="{assetroot}{DATA["images"]["logoBlack"]}"',f'src="{assetroot}{DATA["images"]["logoWhite"]}"',1)
    page=document("/",lang,"Software & Digital Systems Studio",t["heroDesc"],body,root_depth)
    # Move the existing CTA immediately after Services on homepages only.
    cta=re.search(r'<section class="cta-band">.*?</section>',page,re.S).group(0)
    destination='<section class="section statement">'
    if destination not in page:
        raise ValueError("Homepage Services/statement boundary is missing")
    return page.replace(cta,"",1).replace(destination,cta+destination,1)
def service_page(lang,s,depth):
    t=T[lang]; related=s["projects"] or []
    images=f'<div class="detail-hero">{service_image(s,lang,depth,lazy=False)}</div>'
    legacy=[("dimioyrgia-site","Website creation","Κατασκευή ιστοσελίδας"),("seo","SEO","SEO"),("qr-menu","QR menu","QR menu"),("prosfora","Project brief","Φόρμα project"),("blog","Blog","Blog"),("douleies","Previous work","Παλαιότερα έργα")]
    legacy_links=' &nbsp; '.join(f'<a href="{route("/"+slug+"/",lang)}">{label[1] if lang=="el" else label[0]} ↗</a>' for slug,*label in legacy)
    cost_guide=f'<p class="mono"><a class="text-link" href="{route("/blog/kataskeyi-eshop-ellada-kostos/",lang)}">{"ΟΔΗΓΟΣ ΚΟΣΤΟΥΣ ΚΑΤΑΣΚΕΥΗΣ E-SHOP" if lang=="el" else "E-COMMERCE WEBSITE COST GUIDE"} <span class="arrow">↗</span></a></p>' if s["slug"]=="e-commerce" else ""
    body=f'''<main><header class="page-intro"><span class="eyebrow">SERVICE / {DATA['services'].index(s)+1:02}</span><h1>{esc(s['name'][lang])}</h1><p>{esc(s['descriptor'][lang])} {esc(s['description'][lang])}</p></header>{images}{cost_guide}<section class="detail-grid"><div><span class="eyebrow">{t['detailIncludes']}</span><h2>{esc(s['name'][lang])}, {'built around your business.' if lang=='en' else 'σχεδιασμένο γύρω από τη δική σου επιχείρηση.'}</h2></div><div><p class="detail-copy">{esc(s['includes'][lang])}</p><ul class="list-lines">{''.join('<li>▪ &nbsp;'+esc(piece.strip())+'</li>' for piece in s['includes'][lang].replace(' και ',', ').split(',') if piece.strip())}</ul></div></section><section class="detail-grid" style="padding-top:0"><div><span class="eyebrow">{t['process']}</span><h2>{'Μια καθαρή διαδρομή από την ανάγκη στην υλοποίηση.' if lang=='el' else 'A clear path from need to delivery.'}</h2></div><div><ol class="list-lines steps">{''.join('<li>'+esc(step)+'</li>' for step in s['process'][lang].split(' → '))}</ol><a class="text-link" href="{route('/contact/',lang)}">{t['serviceCTA']} <span class="arrow">↗</span></a></div></section><section class="section"><span class="eyebrow">{'MORE FROM CODEHOUSE' if lang=='en' else 'ΠΕΡΙΣΣΟΤΕΡΑ ΑΠΟ ΤΗΝ CODEHOUSE'}</span><p class="mono legacy-links">{legacy_links}</p></section><section class="section"><div class="section-heading"><div><span class="eyebrow">{t['related']}</span><h2>{t['selected']}</h2></div></div><div class="horizontal-rail">{project_cards(lang,depth,related) if related else f'<p class="body-copy">{t["emptyRelated"]}</p>'}</div></section></main>'''
    return document('/services/'+s["slug"]+'/',lang,s["name"][lang],s["description"][lang],body,depth)
def project_page(lang,p,depth):
    t=T[lang]; visible_projects=[project for project in DATA["projects"] if project.get("visible")]
    current_visible=next((index for index,project in enumerate(visible_projects) if project["slug"]==p["slug"]),-1)
    nextp=visible_projects[(current_visible+1)%len(visible_projects)] if current_visible>=0 else visible_projects[0]
    cover_alt=esc(p.get("coverAlt",{}).get(lang,p["name"]+(" — εξώφυλλο έργου" if lang=="el" else " — project cover")))
    cover_image=p.get("cover") or p["desktop"]
    body=f'''<main><header class="page-intro"><span class="eyebrow">SELECTED PROJECT / {current_visible+1 if current_visible>=0 else 0:02}</span><h1>{p['name']}</h1><p>{p['category'][lang]} · {p['domain']}<br>{p['description'][lang]}</p></header><div class="detail-hero project-cover"><img src="{asset_prefix(depth)}{cover_image}" alt="{cover_alt}" width="{p.get('coverWidth',1440)}" height="{p.get('coverHeight',1000)}"></div><section class="detail-grid"><div><span class="eyebrow">{t['goal']}</span><h2>{p['category'][lang]}</h2><p class="detail-copy">{p['goal'][lang]}</p></div><div><span class="eyebrow">{t['solution']}</span><h2>{p['deliverable'][lang]}</h2><p class="detail-copy">{p['solution'][lang]}</p><p class="mono">{'REAL SCREENS · NO DEVICE MOCKUPS' if lang=='en' else 'ΠΡΑΓΜΑΤΙΚΑ SCREENS · ΧΩΡΙΣ MOCKUP ΣΥΣΚΕΥΩΝ'}</p></div></section><section class="case-visuals"><figure><img src="{asset_prefix(depth)}{p['desktop']}" alt="{p['name']} desktop website screenshot" loading="lazy" width="{p.get('desktopWidth',1440)}" height="{p.get('desktopHeight',1000)}"><figcaption>{t['websiteTitle']} · Desktop</figcaption></figure><figure><img src="{asset_prefix(depth)}{p['mobile']}" alt="{p['name']} mobile website screenshot" loading="lazy" width="{p.get('mobileWidth',390)}" height="{p.get('mobileHeight',844)}"><figcaption>{t['mobileTitle']} · Mobile</figcaption></figure></section><section class="detail-grid"><div><span class="eyebrow">{t['includes']}</span><h2>{p['deliverable'][lang]}</h2></div><div><ul class="list-lines">{''.join('<li>▪ &nbsp;'+esc(DATA['services'][i]['name'][lang])+'</li>' for i,slug in enumerate([x['slug'] for x in DATA['services']]) if slug in p['services'])}</ul><a class="text-link" href="{p['url']}" target="_blank" rel="noopener">{t['website']} {p['domain']} <span class="arrow">↗</span></a></div></section><section class="section"><span class="eyebrow">{t['next']}</span><h2 style="font-size:clamp(36px,6vw,78px);font-weight:500;letter-spacing:-.06em"><a href="{route('/projects/'+nextp['slug']+'/',lang)}">{nextp['name']} ↗</a></h2></section></main>'''
    body=body.replace("REAL SCREENS · NO DEVICE MOCKUPS","REAL LANDING PAGES · MOBILE & DESKTOP").replace("ΠΡΑΓΜΑΤΙΚΑ SCREENS · ΧΩΡΙΣ MOCKUP ΣΥΣΚΕΥΩΝ","ΠΡΑΓΜΑΤΙΚΕΣ ΑΡΧΙΚΕΣ ΣΕΛΙΔΕΣ · MOBILE & DESKTOP")
    if not p.get("visible",True):
        body=body.replace("SELECTED PROJECT / 00","PROJECT ARCHIVE",1)
    return document('/projects/'+p["slug"]+'/',lang,p["name"],p["description"][lang],body,depth)
def services_listing(lang):
    t=T[lang];cards="";depth=1+(lang=="en");pre=asset_prefix(depth)
    for i,s in enumerate(DATA["services"]):
        cards+=f'<a class="service-card" href="{route("/services/"+s["slug"]+"/",lang)}"><div class="service-image">{service_image(s,lang,depth)}</div><div class="service-head"><div><span class="mono">[{i+1:02}]</span><h3 class="service-title">{esc(s["name"][lang])}</h3><p>{esc(s["descriptor"][lang])}</p></div><span class="arrow">↗</span></div></a>'
    body=f'<main><header class="page-intro"><span class="eyebrow">CODEHOUSE / SERVICES</span><h1>{t["serviceTitle"]}</h1><p>{t["heroDesc"]}</p></header><section class="section" id="services" style="padding-top:20px"><div class="section-heading"><div><span class="eyebrow">01 — 06</span><h2>{t["services"]}</h2></div><div class="service-controls"><button class="slider-button" aria-label="Previous services" data-rail-control="#service-list-rail" data-dir="prev">←</button><button class="slider-button" aria-label="Next services" data-rail-control="#service-list-rail" data-dir="next">→</button></div></div><div id="service-list-rail" class="horizontal-rail service-rail" tabindex="0">{cards}</div></section><section class="section statement"><div><span class="eyebrow">{t["digitalLabel"]}</span><h2>{t["digitalTitle"]}</h2></div><p class="body-copy">{t["digital"]}</p></section><div class="section"><p class="mono"><a href="{route('/dimioyrgia-site/',lang)}">WEBSITE CREATION ↗</a> &nbsp; <a href="{route('/seo/',lang)}">SEO ↗</a> &nbsp; <a href="{route('/qr-menu/',lang)}">QR MENU ↗</a> &nbsp; <a href="{route('/prosfora/',lang)}">PROJECT BRIEF ↗</a> &nbsp; <a href="{route('/blog/',lang)}">BLOG ↗</a> &nbsp; <a href="{route('/douleies/',lang)}">PREVIOUS WORK ↗</a></p></div></main>'
    return document('/services/',lang,t["serviceTitle"],t["heroDesc"],body,depth)
def projects_listing(lang):
    t=T[lang];depth=1+(lang=="en")
    body=f'<main><header class="page-intro"><span class="eyebrow">CODEHOUSE / SELECTED WORK</span><h1>{t["projectsTitle"]}</h1><p>{t["digital"]}</p></header><section class="section" style="padding-top:20px"><div class="horizontal-rail">{project_cards(lang,depth)}</div></section></main>'
    return document('/projects/',lang,t["projectsTitle"],t["digital"],body,depth)
def studio_page(lang):
    t=T[lang];depth=1+(lang=="en")
    body=f'<main><header class="page-intro"><span class="eyebrow">CODEHOUSE / STUDIO</span><h1>{t["studioTitle"]}</h1><p>{t["about"]}</p></header><section class="section about-grid"><div><span class="eyebrow">{t["digitalLabel"]}</span><h2>{t["digitalTitle"]}</h2></div><div class="about-copy"><p>{t["about"]}</p><p>{t["digital"]}</p></div></section><section class="section"><div class="section-heading"><div><span class="eyebrow">SELECTED / 01—04</span><h2>{t["selected"]}</h2></div></div><div class="horizontal-rail">{project_cards(lang,depth)}</div></section><section class="section"><p class="mono legacy-links"><a href="{route("/douleies/",lang)}">ARCHIVE / PREVIOUS WORK ↗</a> &nbsp; <a href="{route("/blog/",lang)}">NOTES / BLOG ↗</a> &nbsp; <a href="{route("/prosfora/",lang)}">PROJECT BRIEF ↗</a></p></section></main>'
    return document('/studio/',lang,t["studioTitle"],t["about"],body,1+(lang=="en"))
def contact_page(lang):
    t=T[lang];opts=list(zip(DATA["contact"]["services"],["Web design & development","E-commerce","Custom apps & software","AI & automations","Booking & digital systems","Branding & digital marketing"] if lang=="en" else ["Σχεδιασμός & ανάπτυξη ιστοσελίδων","E-commerce","Custom εφαρμογές & software","AI & αυτοματισμοί","Συστήματα κρατήσεων","Branding & digital marketing"]))
    opts_html=''.join(f'<option value="{v}">{n}</option>' for v,n in opts)
    budgets=''.join(f'<option>{x}</option>' for x in t["budgetOptions"])
    contact_heading='Good work starts with a conversation.' if lang=='en' else 'Οι καλές συνεργασίες ξεκινούν με μια συζήτηση.'
    body=f'''<main><section class="contact-layout"><div class="contact-details"><span class="eyebrow">SAY HELLO</span><h1>{contact_heading}</h1><a href="mailto:hello@codehouse.gr">hello@codehouse.gr</a><a href="tel:+306986804138">+30 698 680 4138</a><p class="mono">{'GREECE · REMOTE COLLABORATION' if lang=='en' else 'ΕΛΛΑΔΑ · ΣΥΝΕΡΓΑΣΙΑ ΑΠΟ ΑΠΟΣΤΑΣΗ'}</p></div><form class="contact-form" data-contact-form data-locale="{lang}"><input class="visually-hidden" tabindex="-1" autocomplete="off" name="website" aria-hidden="true"><div class="field"><label for="name">{t["name"]} *</label><input id="name" name="name" autocomplete="name" required></div><div class="field"><label for="company">{t["company"]}</label><input id="company" name="company" autocomplete="organization"></div><div class="field full"><label for="email">{t["email"]} *</label><input id="email" name="email" type="email" autocomplete="email" required></div><div class="field full"><label for="service">{t["kind"]} *</label><select id="service" name="service" required><option value="">{t["select"]}</option>{opts_html}</select></div><div class="field full"><label for="description">{t["description"]} *</label><textarea id="description" name="description" minlength="10" required></textarea></div><div class="field full"><label for="budget">{t["budget"]}</label><select id="budget" name="budget"><option value=""></option>{budgets}</select></div><button class="form-submit" type="submit">{t["send"]} ↗</button><p class="form-status" aria-live="polite"></p></form></section><section class="section"><p class="mono legacy-links"><a href="{route('/dimioyrgia-site/',lang)}">WEBSITE CREATION ↗</a> &nbsp; <a href="{route('/seo/',lang)}">SEO ↗</a> &nbsp; <a href="{route('/qr-menu/',lang)}">QR MENU ↗</a> &nbsp; <a href="{route('/prosfora/',lang)}">PROJECT BRIEF ↗</a> &nbsp; <a href="{route('/blog/',lang)}">BLOG ↗</a> &nbsp; <a href="{route('/douleies/',lang)}">PREVIOUS WORK ↗</a></p></section></main>'''
    return document('/contact/',lang,t["start"],contact_heading,body,1+(lang=="en"))

def write(path,content):
    content=content.replace("hello@codehouse.gr",DATA["contact"]["email"]).replace("+30 698 680 4138",DATA["contact"]["phone"])
    content=re.sub(r'(<nav class="nav-links"[^>]*>)(.*?)(?=<a class="header-cta")',lambda m:m.group(1)+m.group(2).replace('<a ', '<a class="text-[15px]" '),content,count=1,flags=re.S)
    assetroot="../"*len(path.parent.parts)
    lang="en" if path.parts[0]=="en" else "el"
    settings="Privacy settings" if lang=="en" else "Ρυθμίσεις απορρήτου"
    if path in (Path("index.html"),Path("en/index.html")) and DATA["images"].get("heroMode")=="photo" and DATA["images"].get("hero"):
        content=content.replace("<body>","<body class=\"photo-hero\">",1)
    content=content.replace('<section class="cta-band">','<section class="cta-band reveal">',1).replace('<footer class="site-footer">','<footer class="site-footer reveal">',1)
    content=content.replace("01 / WHAT WE DO","01 / OUR SERVICES",1)
    content=content.replace("</head>",f'<link rel="stylesheet" href="{assetroot}assets/studio/refinements.css"><link rel="stylesheet" href="{assetroot}assets/studio/privacy.css"><link rel="apple-touch-icon" href="/assets/img/favicon-512.png"><script defer src="{assetroot}assets/studio/privacy.js"></script></head>',1)
    skip="Skip to content" if lang=="en" else "Μετάβαση στο περιεχόμενο"
    content=content.replace("<body>",f'<body><a class="skip-link" href="#main-content">{skip}</a>',1)
    content=content.replace("<main>","<main id=\"main-content\">",1)
    content=content.replace("</footer>",f'<button class="privacy-reopen" data-privacy-settings type="button">{settings}</button></footer>',1)
    business={"@context":"https://schema.org","@type":"ProfessionalService","@id":"https://codehouse.gr/#business","name":"Codehouse","url":"https://codehouse.gr/","description":T[lang]["heroDesc"],"email":DATA["contact"]["email"],"telephone":DATA["contact"]["phone"],"logo":"https://codehouse.gr/assets/studio/logo-wordmark-black.svg","areaServed":{"@type":"Country","name":"Greece"},"hasOfferCatalog":{"@type":"OfferCatalog","name":T[lang]["services"],"itemListElement":[{"@type":"OfferCatalog","name":service["name"][lang]} for service in DATA["services"]]}}
    ld=json.dumps(business,ensure_ascii=False,separators=(",",":")).replace("</","<\\/")
    content=content.replace("</head>",f'<script type="application/ld+json">{ld}</script></head>',1)
    if path in (Path("index.html"),Path("en/index.html")):
        for project in DATA["projects"]:
            if not project.get("cover") or not project.get("gallery"):
                continue
            image_link=re.compile(r'<a href="'+re.escape(route('/projects/'+project["slug"]+'/',lang))+r'" aria-label="[^"]*"><div class="project-image"><img\b[^>]*></div></a>')
            content=image_link.sub(lambda m:project_gallery(project,lang,len(path.parent.parts)),content,count=1)
        content=content.replace("</head>",f'<link rel="stylesheet" href="{assetroot}assets/studio/project-gallery.css"><script defer src="{assetroot}assets/studio/project-gallery.js"></script></head>',1)
        faq=('<section class="section" id="faq"><span class="eyebrow">QUESTIONS / ANSWERS</span><h2 style="font-size:clamp(34px,5vw,62px);font-weight:500;letter-spacing:-.06em">A few useful answers.</h2><div class="faq-list"><details><summary>What does Codehouse build?</summary><p>Websites, e-commerce, custom applications and digital systems, scoped around the needs of each business.</p></details><details><summary>How does a project begin?</summary><p>Share the idea and requirements through the project form or by email. We discuss the needs and a clear scope.</p></details><details><summary>Can you work with businesses outside Greece?</summary><p>Yes. Codehouse collaborates with businesses in Greece and abroad.</p></details></div></section>') if lang=="en" else ('<section class="section" id="faq"><span class="eyebrow">ΕΡΩΤΗΣΕΙΣ / ΑΠΑΝΤΗΣΕΙΣ</span><h2 style="font-size:clamp(34px,5vw,62px);font-weight:500;letter-spacing:-.06em">Μερικές χρήσιμες απαντήσεις.</h2><div class="faq-list"><details><summary>Τι αναλαμβάνει η Codehouse;</summary><p>Ιστοσελίδες, e-commerce, custom εφαρμογές και ψηφιακά συστήματα, με scope γύρω από τις ανάγκες κάθε επιχείρησης.</p></details><details><summary>Πώς ξεκινά ένα project;</summary><p>Στείλε την ιδέα και τις ανάγκες από τη φόρμα project ή με email. Συζητάμε το ζητούμενο και το κατάλληλο scope.</p></details><details><summary>Συνεργάζεστε με επιχειρήσεις εκτός Ελλάδας;</summary><p>Ναι. Η Codehouse συνεργάζεται με επιχειρήσεις στην Ελλάδα και το εξωτερικό.</p></details></div></section>')
        content=content.replace("</main>",faq+"</main>",1)
        content=re.sub(r'<section class="cta-band(?: reveal)?">',lambda m:m.group(0)[:-1]+' id="quiz">',content,count=1)
        content=content.replace('class="button-link"','class="button-link" id="contact"',1)
        content=content.replace('<section class="section"><div class="section-heading"><div><span class="eyebrow">01 / WHAT WE DO','<section class="section" id="services"><div class="section-heading" id="process"><div><span class="eyebrow">01 / WHAT WE DO',1)
        content=content.replace('<section class="section" id="process"><div class="section-heading">','<section class="section" id="services"><div class="section-heading" id="process">',1)
        content=content.replace('<section class="section" style="padding-top:35px">','<section class="section" id="work" style="padding-top:35px">',1)
        content=content.replace('<div class="horizontal-rail" tabindex="0"><article class="project-card">','<div class="project-carousel-controls"><button class="slider-button" aria-label="Previous projects" data-rail-control="#project-rail" data-dir="prev">←</button><span class="rail-position" data-rail-position="#project-rail" aria-live="polite">01 / 03</span><button class="slider-button" aria-label="Next projects" data-rail-control="#project-rail" data-dir="next">→</button></div><div id="project-rail" class="horizontal-rail" tabindex="0"><article class="project-card">',1)
    if path in (Path("index.html"),Path("en/index.html")):
        content=content.replace('aria-live="polite">01 / 03</span>',f'aria-live="polite">01 / {len(DATA["homeProjects"]):02}</span>',1)
    content=re.sub(r'<img class="hero-logo" src="([^"]+)" alt="Codehouse">',lambda m:f'<div class="hero-mark"><img class="hero-logo" src="{m.group(1)}" alt="Codehouse"><svg class="hero-brackets" viewBox="0 0 1000 600" aria-hidden="true"><path d="M42 116V42h92M866 42h92v74M42 484v74h92M866 558h92v-74"/></svg></div>',content, count=1)
    content=content.replace('<span class="arrow">↗</span>','<svg class="arrow-icon" viewBox="0 0 20 20" aria-hidden="true"><path d="M4 16 16 4M6 4h10v10"/></svg>')
    content=content.replace('<span class="arrow" aria-hidden="true">↗</span>','<svg class="arrow-icon" viewBox="0 0 20 20" aria-hidden="true"><path d="M4 16 16 4M6 4h10v10"/></svg>')
    # Empty editorial image fields retain their layout without an empty-src
    # image (which would request a directory or the current page).
    empty_photo=re.compile(
        r'<div class="(hero-art|service-image|project-image|detail-hero(?: project-cover)?)">'
        r'<img\b[^>]*\bsrc="'+re.escape(assetroot)+r'"[^>]*>'
    )
    content=empty_photo.sub(lambda m:f'<div class="{m.group(1)} photo-empty">',content)
    if path in (Path("index.html"),Path("en/index.html")) and DATA["images"].get("heroLogo"):
        content=re.sub(r'<body(?: class="([^"]*)")?>',lambda m:f'<body class="{((m.group(1) or "")+" hero-artwork").strip()}">',content,count=1)
    if path in (Path("index.html"),Path("en/index.html")) and DATA["images"].get("heroVideos"):
        clips=[{"src":assetroot+clip["src"],"webm":assetroot+clip["webm"],"poster":assetroot+clip["poster"],"label":clip["label"][lang]} for clip in DATA["images"]["heroVideos"]]
        playlist=esc(json.dumps(clips,ensure_ascii=False))
        error="Δεν φορτώθηκε το βίντεο. Δοκίμασε ξανά." if lang=="el" else "The video could not load. Please try again."
        content=re.sub(r'<body(?: class="([^"]*)")?>',lambda m:f'<body class="{((m.group(1) or "")+" video-hero").strip()}">',content,count=1)
        content=content.replace('<section class="hero">',f'<section class="hero" data-hero-videos data-hero-autoinit data-hero-intro data-intro-lang="{lang}" data-playlist="{playlist}" data-error-label="{error}">',1)
        layer=f'<div class="hero-video-layer" aria-hidden="true"><video class="hero-video is-active" muted playsinline preload="metadata" src="{clips[0]["src"]}" poster="{clips[0]["poster"]}"></video><video class="hero-video" muted playsinline preload="none"></video></div>'
        content=content.replace('<div class="hero-art photo-empty">','<div class="hero-art photo-empty">'+layer,1)
        film_info=f'<div class="hero-video-info" hidden><span class="hero-video-position" data-video-position>01 / {len(clips):02} — {clips[0]["label"]}</span></div><p class="hero-video-status" data-video-status role="status" hidden></p>'
        content=content.replace('<div class="hero-bottom">',film_info+'<div class="hero-bottom">',1)
        intro_skip="ΕΙΣΟΔΟΣ ΣΤΟ SITE" if lang=="el" else "ENTER THE SITE"
        intro_label="Προετοιμασία του site" if lang=="el" else "Preparing the site"
        intro=f'<div class="hero-loading-screen" data-hero-intro-loader role="dialog" aria-modal="true" aria-labelledby="hero-intro-label"><div class="hero-intro-panel"><div class="hero-intro-caption"><span id="hero-intro-label">LOADING</span><span data-intro-percent aria-hidden="true">00%</span></div><div class="hero-intro-bar" role="progressbar" aria-label="{intro_label}" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0"><span data-intro-fill></span></div><button type="button" data-intro-skip onclick="document.documentElement.classList.remove(\'intro-pending\')">{intro_skip} ↗</button></div></div>'
        content=re.sub(r'(<body\b[^>]*>)',lambda match:match.group(1)+intro,content,count=1)
        # Paint the film/poster and intro before the deferred player initializes.
        # The independent watchdog also releases the page if that module fails.
        bootstrap='<script>if(!location.hash&&!matchMedia("(prefers-reduced-motion: reduce)").matches){document.documentElement.classList.add("intro-pending");setTimeout(()=>document.documentElement.classList.remove("intro-pending"),10000)}</script>'
        content=content.replace('</head>',f'<link rel="stylesheet" href="{assetroot}assets/studio/hero-video.css">{bootstrap}<script type="module" src="{assetroot}assets/studio/hero-video.js"></script></head>',1)
    dest=OUT/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(content,encoding="utf-8")
for l in ("el","en"):
    write(Path("index.html") if l=="el" else Path("en/index.html"),home(l))
    write(Path("services/index.html") if l=="el" else Path("en/services/index.html"),services_listing(l))
    write(Path("projects/index.html") if l=="el" else Path("en/projects/index.html"),projects_listing(l))
    write(Path("studio/index.html") if l=="el" else Path("en/studio/index.html"),studio_page(l))
    write(Path("contact/index.html") if l=="el" else Path("en/contact/index.html"),contact_page(l))
    for s in DATA["services"]:
        write(Path(("services/" if l=="el" else "en/services/")+s["slug"]+"/index.html"),service_page(l,s,2+(l=="en")))
    for p in DATA["projects"]:
        write(Path(("projects/" if l=="el" else "en/projects/")+p["slug"]+"/index.html"),project_page(l,p,2+(l=="en")))
print("Generated 28 bilingual static HTML routes from assets/studio/data.json")