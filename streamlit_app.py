import streamlit as st, sqlite3, hashlib, secrets, re, os, datetime as dt
import pandas as pd
from html import escape as esc

DB = "croc2.db"
STATUTS = ["Commande reçue", "Commande confirmée", "En préparation", "Expédiée", "Livrée"]
BORDEAUX, ROSE, BEIGE, CHOCO = "#6D0F2B", "#F3D5D8", "#F7EFE3", "#4A2C1A"

# Ingrédients disponibles -> allergène associé (à vérifier avec les étiquettes réelles de vos fournisseurs)
INGREDIENTS = {
    "Dattes": "", "Amandes": "amandes", "Noix": "noix", "Avoine": "gluten (avoine)",
    "Abricots secs": "sulfites possibles", "Figues séchées": "", "Noix de cajou": "noix de cajou",
    "Pistaches": "pistaches", "Chocolat noir 70%": "traces de lait", "Chocolat blanc": "lait",
    "Cacao en poudre": "",
}

def compo_text(items):
    """Renvoie (texte des ingrédients, texte des allergènes) pour une liste d'ingrédients."""
    ing = ", ".join(items)
    al = ", ".join(dict.fromkeys(INGREDIENTS[i] for i in items if INGREDIENTS.get(i)))
    return ing, al

# Recettes proposées au départ : (nom, ingrédients, (prix boîte 6, 12, 24), description)
RECETTES = [
    ("Dattes Fondantes, Amandes & Chocolat Noir", ["Dattes", "Amandes", "Chocolat noir 70%", "Cacao en poudre"], (30, 55, 110),
     "Le goût du désert : dattes fondantes, amandes croquantes et chocolat noir 70%."),
    ("Noix Croquantes, Dattes & Chocolat Noir", ["Dattes", "Noix", "Chocolat noir 70%", "Cacao en poudre"], (35, 65, 130),
     "Intense et royale : noix, dattes et chocolat noir 70%."),
    ("Avoine Gourmande, Amandes & Chocolat Noir", ["Avoine", "Dattes", "Amandes", "Chocolat noir 70%", "Cacao en poudre"], (30, 55, 110),
     "La boule d'énergie du matin : avoine, dattes, amandes et chocolat noir."),
    ("Cajou Crémeux, Pistache & Avoine Dorée", ["Avoine", "Noix de cajou", "Pistaches", "Chocolat noir 70%"], (55, 105, 205),
     "Précieuse et gourmande : pistaches, noix de cajou, avoine et chocolat noir."),
    ("Abricot Soleil, Pistache & Avoine Croquante", ["Avoine", "Abricots secs", "Pistaches", "Chocolat noir 70%"], (45, 90, 180),
     "Fruitée et croquante : abricot sec, pistaches et avoine."),
    ("Figues Moelleuses, Amandes & Chocolat Noir", ["Figues séchées", "Amandes", "Chocolat noir 70%", "Cacao en poudre"], (45, 90, 180),
     "Figues moelleuses et amandes, un jardin dans une bouchée."),
    ("Cajou Onctueux & Chocolat Blanc Soyeux", ["Noix de cajou", "Dattes", "Chocolat blanc"], (40, 80, 160),
     "Onctueuse et douce : noix de cajou, dattes et chocolat blanc."),
]

# Changez ce numéro quand vous modifiez RECETTES : le catalogue sera rechargé au prochain lancement
CATALOG_VERSION = "3"

st.set_page_config(page_title="CROC – Small Bites. Big Energy.", page_icon="🍫", layout="wide")
st.markdown(f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Poppins:wght@300;400;500;600&display=swap');
.stApp, .stApp p, .stApp label, .stApp li, .stApp input, .stApp textarea {{font-family:'Poppins',sans-serif;}}
.stApp {{background:linear-gradient(180deg,{BEIGE} 0%,#FBF6EE 100%);}}
h1,h2,h3 {{font-family:'Playfair Display',serif !important;color:{BORDEAUX};}}
#MainMenu, footer, [data-testid="stToolbar"] {{visibility:hidden;}}
header[data-testid="stHeader"] {{background:transparent;}}
.block-container {{padding-top:2rem;max-width:1200px;}}

/* Boutons */
.stButton>button, .stDownloadButton>button, .stLinkButton>a {{background:{BORDEAUX};color:white;border-radius:999px;
  border:0;padding:.5rem 1.4rem;font-weight:500;transition:all .2s ease;box-shadow:0 3px 10px rgba(109,15,43,.25);}}
.stButton>button:hover, .stDownloadButton>button:hover {{background:{CHOCO};color:white;transform:translateY(-2px);}}

/* Barre latérale */
[data-testid="stSidebar"] {{background:linear-gradient(180deg,{BORDEAUX} 0%,#4A0A1D 100%);}}
[data-testid="stSidebar"] * {{color:white !important;}}
[data-testid="stSidebar"] label {{padding:.25rem .4rem;border-radius:10px;transition:background .2s;}}
[data-testid="stSidebar"] label:hover {{background:rgba(255,255,255,.12);}}
.brand {{text-align:center;padding:1rem 0 .5rem;}}
.brand .b1 {{font-family:'Playfair Display',serif;font-size:42px;letter-spacing:6px;font-weight:700;}}
.brand .b1 span {{color:{ROSE} !important;}}
.brand .b2 {{font-size:12px;letter-spacing:2px;opacity:.8;text-transform:uppercase;}}

/* Cartes, métriques, champs */
div[data-testid="stVerticalBlockBorderWrapper"] {{background:white;border-radius:18px;border:1px solid {ROSE};
  box-shadow:0 4px 18px rgba(109,15,43,.07);transition:box-shadow .2s ease;}}
div[data-testid="stVerticalBlockBorderWrapper"]:hover {{box-shadow:0 8px 26px rgba(109,15,43,.16);}}
[data-testid="stMetric"] {{background:white;border-radius:16px;padding:14px 18px;border-left:5px solid {BORDEAUX};
  box-shadow:0 3px 12px rgba(109,15,43,.08);}}
[data-baseweb="input"], [data-baseweb="select"]>div, [data-baseweb="textarea"] {{border-radius:12px !important;}}
[data-testid="stAlert"] {{border-radius:14px;}}
button[role="tab"][aria-selected="true"] {{color:{BORDEAUX};font-weight:600;}}

/* Accueil */
.hero {{background:linear-gradient(135deg,{BORDEAUX} 0%,#9C2347 100%);border-radius:26px;padding:3.2rem 2.5rem;
  text-align:center;color:white;box-shadow:0 12px 34px rgba(109,15,43,.3);margin-bottom:1.6rem;}}
.hero .logo {{font-family:'Playfair Display',serif;font-size:84px;letter-spacing:12px;font-weight:700;line-height:1;color:white;}}
.hero .logo span {{color:{ROSE};}}
.hero .tag {{font-family:'Playfair Display',serif;font-size:28px;font-style:italic;margin:.6rem 0 .8rem;color:{ROSE};}}
.hero p {{font-size:17px;font-weight:300;margin:0;color:white;}}
.feat {{background:white;border-radius:18px;padding:1.3rem 1rem;text-align:center;
  box-shadow:0 4px 18px rgba(109,15,43,.08);height:100%;}}
.feat .ic {{font-size:34px;}} .feat b {{color:{BORDEAUX};}} .feat span {{font-size:14px;color:{CHOCO};opacity:.85;}}
.flav {{background:white;border-radius:16px;padding:1rem 1.2rem;margin-bottom:.9rem;border-left:6px solid {BORDEAUX};
  box-shadow:0 3px 12px rgba(109,15,43,.07);font-weight:500;color:{CHOCO};}}
.flav .em {{font-size:24px;margin-right:.5rem;}}
.pill {{display:inline-block;background:{ROSE};color:{BORDEAUX};border-radius:999px;padding:.15rem .8rem;font-size:13px;font-weight:600;}}
.chip {{display:inline-block;background:{ROSE};color:{BORDEAUX};border-radius:999px;padding:.12rem .7rem;
  margin:.2rem .25rem 0 0;font-size:13px;font-weight:500;}}
.compo {{margin:.3rem 0 .4rem;font-size:14px;color:{CHOCO};}}
.allerg {{font-size:12.5px;color:#8a6d5a;margin-bottom:.5rem;}}
.flav .sub {{font-size:12.5px;font-weight:400;opacity:.75;margin-top:.2rem;}}
.footer {{text-align:center;color:{CHOCO};opacity:.65;font-size:13px;margin-top:3rem;padding:1.5rem 0;border-top:1px solid {ROSE};}}
</style>""", unsafe_allow_html=True)

# ---------------------------------------------------------------- BASE DE DONNÉES
def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def q(sql, args=(), one=False):
    c = conn()
    try:
        rows = c.execute(sql, args).fetchall()
    finally:
        c.close()
    return (rows[0] if rows else None) if one else rows

def run(sql, args=()):
    c = conn()
    try:
        cur = c.execute(sql, args)
        c.commit()
        return cur.lastrowid
    finally:
        c.close()

def df(sql, args=()):
    c = conn()
    try:
        return pd.read_sql(sql, c, params=args)
    finally:
        c.close()

def seed_catalog(c):
    """(Re)charge le catalogue de départ. Sans commandes : on remplace tout. Avec commandes : on désactive l'ancien."""
    if c.execute("SELECT COUNT(*) FROM orders").fetchone()[0] > 0:
        c.execute("UPDATE products SET active=0")
    else:
        c.execute("DELETE FROM variants")
        c.execute("DELETE FROM products")
    for n, comp, (p6, p12, p24), desc in RECETTES:
        ing, al = compo_text(comp)
        pid = c.execute("INSERT INTO products(name,description,ingredients,allergens) VALUES(?,?,?,?)",
                        (n, desc, ing, al)).lastrowid
        for pcs, pr in ((6, p6), (12, p12), (24, p24)):
            # stock initial de 100 = valeur de départ à ajuster dans l'admin
            c.execute("INSERT INTO variants(product_id,pieces,price,stock) VALUES(?,?,?,100)", (pid, pcs, pr))
    # Box Découverte : désactivée tant que l'admin n'a pas fixé le prix
    pid = c.execute("INSERT INTO products(name,description,active) VALUES(?,?,0)",
                    ("Box Découverte CROC", "Toutes les saveurs, une boule par saveur.")).lastrowid
    c.execute("INSERT INTO variants(product_id,pieces,price,stock) VALUES(?,6,0,100)", (pid,))
    c.execute("INSERT OR IGNORE INTO promos VALUES('CROC10',10,'','',0,0,1)")
    c.execute("INSERT OR REPLACE INTO settings VALUES('catalog_version',?)", (CATALOG_VERSION,))

def init_db():
    c = conn()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, first TEXT, last TEXT, phone TEXT,
        email TEXT UNIQUE, salt TEXT, pw TEXT, address TEXT, city TEXT);
    CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY, name TEXT, description TEXT,
        ingredients TEXT, allergens TEXT, active INTEGER DEFAULT 1, cost_ball REAL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS variants(id INTEGER PRIMARY KEY, product_id INTEGER, pieces INTEGER,
        price REAL, stock INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS promos(code TEXT PRIMARY KEY, percent REAL, start TEXT, end TEXT,
        min_amount REAL DEFAULT 0, max_uses INTEGER DEFAULT 0, active INTEGER DEFAULT 1);
    CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY, user_id INTEGER, name TEXT, phone TEXT,
        email TEXT, city TEXT, address TEXT, notes TEXT, subtotal REAL, discount REAL, delivery_fee REAL,
        delivery_cost REAL, total REAL, cogs REAL, promo_code TEXT, free_first INTEGER, payment TEXT,
        status TEXT, admin_notes TEXT, created TEXT);
    CREATE TABLE IF NOT EXISTS order_items(id INTEGER PRIMARY KEY, order_id INTEGER, variant_id INTEGER,
        product_name TEXT, pieces INTEGER, qty INTEGER, unit_price REAL, unit_cost REAL);
    CREATE TABLE IF NOT EXISTS status_history(id INTEGER PRIMARY KEY, order_id INTEGER, status TEXT, at TEXT);
    CREATE TABLE IF NOT EXISTS promo_usages(id INTEGER PRIMARY KEY, code TEXT, order_id INTEGER, at TEXT);
    """)
    defaults = {"delivery_fee": 10, "delivery_cost": 15, "target_margin": 20, "packaging_6": 0,
                "packaging_12": 0, "packaging_24": 0, "allow_stack": 0, "free_first": 1,
                "whatsapp": "", "other_charges": 0, "low_stock": 10}
    for k, v in defaults.items():
        c.execute("INSERT OR IGNORE INTO settings VALUES(?,?)", (k, str(v)))
    cur = c.execute("SELECT value FROM settings WHERE key='catalog_version'").fetchone()
    if not cur or cur[0] != CATALOG_VERSION:
        seed_catalog(c)
    c.commit()
    c.close()

def S(key):
    r = q("SELECT value FROM settings WHERE key=?", (key,), one=True)
    if not r:
        return 0
    if key == "whatsapp":          # le numéro WhatsApp doit rester du texte
        return r["value"]
    try:
        return float(r["value"])
    except Exception:
        return r["value"]

def set_S(key, val):
    run("INSERT OR REPLACE INTO settings VALUES(?,?)", (key, str(val)))

# ---------------------------------------------------------------- SÉCURITÉ / VALIDATION
def hash_pw(pw, salt):
    return hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), 200_000).hex()

def norm_phone(p):
    p = re.sub(r"[\s.\-]", "", p.strip())
    return p.replace("+212", "0", 1) if p.startswith("+212") else p

def ok_phone(p):
    return re.fullmatch(r"0[5-7]\d{8}", norm_phone(p)) is not None

def ok_email(e):
    return re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", e) is not None

def admin_password():
    try:
        return st.secrets["ADMIN_PASSWORD"]
    except Exception:
        return os.environ.get("ADMIN_PASSWORD", "croc-admin-change-me")

def ss(k, v):
    if k not in st.session_state:
        st.session_state[k] = v

ss("cart", {})
ss("user", None)
ss("admin", False)

# ---------------------------------------------------------------- CALCULS CÔTÉ SERVEUR
def quote(cart, code, user_id, phone, email):
    items, subtotal, cogs = [], 0.0, 0.0
    for vid, qty in cart.items():
        v = q("SELECT v.*, p.name, p.cost_ball FROM variants v JOIN products p ON p.id=v.product_id WHERE v.id=?",
              (vid,), one=True)
        if not v:
            continue
        unit_cost = v["cost_ball"] * v["pieces"] + float(S(f"packaging_{v['pieces']}") or 0)
        items.append(dict(v=v, qty=qty, unit_cost=unit_cost))
        subtotal += v["price"] * qty
        cogs += unit_cost * qty
    msgs = []
    # Livraison gratuite 1re commande
    prior = q("""SELECT COUNT(*) c FROM orders WHERE status!='Annulée' AND
                 ((user_id IS NOT NULL AND user_id=?) OR (?!='' AND phone=?) OR (?!='' AND lower(email)=lower(?)))""",
              (user_id, phone, phone, email, email), one=True)["c"]
    free = bool(S("free_first")) and prior == 0 and subtotal > 0
    # Code promo
    discount, applied = 0.0, ""
    if code and code.strip():
        pcode = code.upper().strip()
        p = q("SELECT * FROM promos WHERE code=?", (pcode,), one=True)
        today = dt.date.today().isoformat()
        uses = q("SELECT COUNT(*) c FROM promo_usages WHERE code=?", (pcode,), one=True)["c"] if p else 0
        if not p or not p["active"]:
            msgs.append("Code promo invalide.")
        elif p["start"] and today < p["start"]:
            msgs.append("Ce code n'est pas encore valable.")
        elif p["end"] and today > p["end"]:
            msgs.append("Ce code a expiré.")
        elif subtotal < p["min_amount"]:
            msgs.append(f"Montant minimum pour ce code : {p['min_amount']:.0f} DH.")
        elif p["max_uses"] and uses >= p["max_uses"]:
            msgs.append("Ce code a atteint sa limite d'utilisation.")
        elif free and not S("allow_stack"):
            msgs.append("Le code n'est pas cumulable avec la livraison gratuite de 1re commande.")
        else:
            discount = round(subtotal * p["percent"] / 100, 2)
            applied = p["code"]
    fee = 0.0 if free else (float(S("delivery_fee")) if subtotal > 0 else 0.0)
    carrier = float(S("delivery_cost")) if subtotal > 0 else 0.0
    return dict(items=items, subtotal=subtotal, discount=discount, promo=applied, fee=fee, carrier=carrier,
                free=free, total=subtotal - discount + fee, cogs=cogs, msgs=msgs)

def place_order(info, cart, qt, user_id):
    c = conn()
    try:
        for it in qt["items"]:
            stock = c.execute("SELECT stock FROM variants WHERE id=?", (it["v"]["id"],)).fetchone()["stock"]
            if stock < it["qty"]:
                raise ValueError(f"Stock insuffisant pour {it['v']['name']} ({it['v']['pieces']} pièces).")
        now = dt.datetime.now().isoformat(timespec="seconds")
        oid = c.execute("""INSERT INTO orders(user_id,name,phone,email,city,address,notes,subtotal,discount,delivery_fee,
            delivery_cost,total,cogs,promo_code,free_first,payment,status,admin_notes,created)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (user_id, info["name"], info["phone"], info["email"], info["city"], info["address"], info["notes"],
             qt["subtotal"], qt["discount"], qt["fee"], qt["carrier"], qt["total"], qt["cogs"], qt["promo"],
             int(qt["free"]), "Paiement à la livraison", STATUTS[0], "", now)).lastrowid
        for it in qt["items"]:
            v = it["v"]
            c.execute("INSERT INTO order_items(order_id,variant_id,product_name,pieces,qty,unit_price,unit_cost) VALUES(?,?,?,?,?,?,?)",
                      (oid, v["id"], v["name"], v["pieces"], it["qty"], v["price"], it["unit_cost"]))
            c.execute("UPDATE variants SET stock=stock-? WHERE id=?", (it["qty"], v["id"]))
        if qt["promo"]:
            c.execute("INSERT INTO promo_usages(code,order_id,at) VALUES(?,?,?)", (qt["promo"], oid, now))
        c.execute("INSERT INTO status_history(order_id,status,at) VALUES(?,?,?)", (oid, STATUTS[0], now))
        c.commit()
        return oid
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()

def set_status(oid, new):
    o = q("SELECT status FROM orders WHERE id=?", (oid,), one=True)
    if o["status"] != "Annulée" and new == "Annulée":      # restitue le stock
        for it in q("SELECT * FROM order_items WHERE order_id=?", (oid,)):
            run("UPDATE variants SET stock=stock+? WHERE id=?", (it["qty"], it["variant_id"]))
    elif o["status"] == "Annulée" and new != "Annulée":    # ré-déduit le stock si on réactive
        for it in q("SELECT * FROM order_items WHERE order_id=?", (oid,)):
            run("UPDATE variants SET stock=stock-? WHERE id=?", (it["qty"], it["variant_id"]))
    run("UPDATE orders SET status=? WHERE id=?", (new, oid))
    run("INSERT INTO status_history(order_id,status,at) VALUES(?,?,?)",
        (oid, new, dt.datetime.now().isoformat(timespec="seconds")))

def ref(oid):
    return f"CROC-{oid:05d}"

def show_order(o):
    with st.container(border=True):
        st.markdown(f"### {ref(o['id'])} — {o['status']}")
        if o["status"] == "Annulée":
            st.error("Commande annulée")
        else:
            st.progress((STATUTS.index(o["status"]) + 1) / len(STATUTS), text=" → ".join(STATUTS))
        items = q("SELECT * FROM order_items WHERE order_id=?", (o["id"],))
        st.table(pd.DataFrame([{"Produit": i["product_name"], "Format": f"Boîte de {i['pieces']}", "Qté": i["qty"],
                                "Prix unitaire (DH)": i["unit_price"]} for i in items]))
        st.write(f"Date : {o['created']} · Paiement : {o['payment']}")
        promo_txt = f"({o['promo_code']})" if o["promo_code"] else ""
        free_txt = "(offerte, 1re commande)" if o["free_first"] else ""
        st.write(f"Sous-total {o['subtotal']:.2f} DH · Remise −{o['discount']:.2f} DH {promo_txt}"
                 f" · Livraison {o['delivery_fee']:.2f} DH {free_txt}")
        st.write(f"**Total : {o['total']:.2f} DH** · Livraison à : {o['address']}, {o['city']}")
        recap = f"Commande {ref(o['id'])}\nTotal {o['total']:.2f} DH\nStatut : {o['status']}"
        st.download_button("Télécharger le récapitulatif", recap, file_name=f"{ref(o['id'])}.txt", key=f"dl{o['id']}")
        wa = re.sub(r"\D", "", str(S("whatsapp")))
        if wa:
            st.link_button("Contacter CROC sur WhatsApp", f"https://wa.me/{wa}?text=Commande%20{ref(o['id'])}")

# ---------------------------------------------------------------- PAGES CLIENT
def compo_html(p):
    items = [i for i in (p["ingredients"] or "").split(", ") if i]
    if not items:
        return "<div class='allerg'>Composition bientôt disponible.</div>"
    chips = "".join(f"<span class='chip'>{esc(i)}</span>" for i in items)
    al = f"<div class='allerg'>⚠ Allergènes : {esc(p['allergens'])}</div>" if p["allergens"] else ""
    return f"<div class='compo'><b>Ingrédients</b><br>{chips}</div>{al}"

EMOJIS = ["🌰", "🌳", "🍫", "🌾", "🥜", "🍯", "🤍"]

def page_home():
    st.markdown("""<div class='hero'><div class='logo'>CR<span>●</span>C</div>
        <div class='tag'>Small Bites. Big Energy.</div>
        <p>Des Energy Balls gourmandes, naturelles et élégantes, préparées au Maroc.</p></div>""",
                unsafe_allow_html=True)
    cols = st.columns(3)
    feats = [("🌿", "Naturel", "Des ingrédients simples et gourmands."),
             ("🚚", "Livraison offerte", "Sur votre première commande."),
             ("💵", "Paiement à la livraison", "Réglez en espèces à la réception.")]
    for col, (ic, t, d) in zip(cols, feats):
        col.markdown(f"<div class='feat'><div class='ic'>{ic}</div><b>{t}</b><br><span>{d}</span></div>",
                     unsafe_allow_html=True)
    st.write("")
    _, mid, _ = st.columns([2, 1.4, 2])
    mid.button("Découvrir la boutique 🍫", use_container_width=True,
               on_click=lambda: st.session_state.update(page="Boutique"))
    st.markdown("<h2 style='margin-top:1.5rem'>Nos saveurs</h2>", unsafe_allow_html=True)
    cols = st.columns(3)
    for i, p in enumerate(q("SELECT * FROM products WHERE active=1")):
        cols[i % 3].markdown(f"<div class='flav'><span class='em'>{EMOJIS[i % len(EMOJIS)]}</span>{esc(p['name'])}"
                             f"<div class='sub'>{esc(p['ingredients'] or '')}</div></div>",
                             unsafe_allow_html=True)

def page_shop():
    st.title("Boutique")
    prods = q("SELECT * FROM products WHERE active=1")
    flt = st.selectbox("Filtrer par saveur", ["Toutes"] + [p["name"] for p in prods])
    visible = [p for p in prods if flt == "Toutes" or p["name"] == flt]
    cols = st.columns(3)
    for i, p in enumerate(visible):
        vs = q("SELECT * FROM variants WHERE product_id=? ORDER BY pieces", (p["id"],))
        if not vs:
            continue
        with cols[i % 3]:
            with st.container(border=True):
                st.markdown(f"<div style='font-size:46px;text-align:center'>{EMOJIS[i % len(EMOJIS)]}</div>",
                            unsafe_allow_html=True)
                st.subheader(p["name"])
                if p["description"]:
                    st.write(p["description"])
                st.markdown(compo_html(p), unsafe_allow_html=True)
                opts = {f"Boîte de {v['pieces']} ({v['pieces'] * 20} g) — {v['price']:.0f} DH": v for v in vs}
                lab = st.selectbox("Format", list(opts), key=f"f{p['id']}")
                v = opts[lab]
                st.markdown("<span class='pill'>✅ En stock</span>" if v["stock"] > 0
                            else "<span class='pill'>❌ Rupture de stock</span>", unsafe_allow_html=True)
                qty = st.number_input("Quantité", 1, 50, 1, key=f"q{p['id']}")
                if st.button("Ajouter au panier", key=f"a{p['id']}", disabled=v["stock"] <= 0,
                             use_container_width=True):
                    st.session_state.cart[v["id"]] = st.session_state.cart.get(v["id"], 0) + qty
                    st.success("Ajouté au panier")

def page_cart():
    st.title("Panier")
    cart = st.session_state.cart
    if not cart:
        st.info("Votre panier est vide.")
        return
    for vid, qty in list(cart.items()):
        v = q("SELECT v.*, p.name FROM variants v JOIN products p ON p.id=v.product_id WHERE v.id=?", (vid,), one=True)
        if not v:
            del cart[vid]
            st.rerun()
        c1, c2, c3 = st.columns([4, 2, 1])
        c1.write(f"**{v['name']}** — boîte de {v['pieces']} ({v['price']:.0f} DH)")
        cart[vid] = c2.number_input("Qté", 1, 50, qty, key=f"cq{vid}", label_visibility="collapsed")
        if c3.button("🗑", key=f"cd{vid}"):
            del cart[vid]
            st.rerun()
    user = st.session_state.user
    st.subheader("Vos informations")
    st.caption("Vous pouvez commander sans compte, ou vous connecter dans « Mon compte ».")
    name = st.text_input("Nom et prénom", value=f"{user['first']} {user['last']}" if user else "")
    phone = st.text_input("Téléphone (ex : 06 12 34 56 78)", value=user["phone"] if user else "")
    email = st.text_input("E-mail", value=user["email"] if user else "")
    city = st.text_input("Ville", value=(user["city"] or "") if user else "")
    address = st.text_area("Adresse de livraison", value=(user["address"] or "") if user else "")
    notes = st.text_input("Informations pour le livreur (facultatif)")
    code = st.text_input("Code promo")
    qt = quote(cart, code, user["id"] if user else None, norm_phone(phone), email.strip())
    for m in qt["msgs"]:
        st.warning(m)
    st.subheader("Récapitulatif")
    st.write(f"Sous-total : {qt['subtotal']:.2f} DH")
    if qt["discount"]:
        st.write(f"Remise ({qt['promo']}) : −{qt['discount']:.2f} DH")
    st.write("Livraison : " + ("**offerte** (1re commande)" if qt["free"] else f"{qt['fee']:.2f} DH"))
    st.markdown(f"### Total à payer : {qt['total']:.2f} DH")
    st.caption("Paiement à la livraison (espèces).")
    if st.button("Valider la commande"):
        err = []
        if len(name.strip()) < 3: err.append("Nom invalide.")
        if not ok_phone(phone): err.append("Numéro marocain invalide (ex : 0612345678).")
        if not ok_email(email.strip()): err.append("E-mail invalide.")
        if not city.strip() or len(address.strip()) < 5: err.append("Ville et adresse requises.")
        if err:
            for e in err:
                st.error(e)
        else:
            try:
                oid = place_order(dict(name=name.strip(), phone=norm_phone(phone), email=email.strip().lower(),
                                       city=city.strip(), address=address.strip(), notes=notes.strip()),
                                  cart, qt, user["id"] if user else None)
                st.session_state.cart = {}
                st.success(f"Commande confirmée ! Numéro : {ref(oid)}. Conservez-le avec votre téléphone pour le suivi.")
                st.balloons()
            except ValueError as e:
                st.error(str(e))

def page_account():
    st.title("Mon compte")
    u = st.session_state.user
    if not u:
        t1, t2 = st.tabs(["Connexion", "Inscription"])
        with t1:
            em = st.text_input("E-mail", key="le")
            pw = st.text_input("Mot de passe", type="password", key="lp")
            if st.button("Se connecter"):
                r = q("SELECT * FROM users WHERE email=?", (em.strip().lower(),), one=True)
                if r and secrets.compare_digest(hash_pw(pw, r["salt"]), r["pw"]):
                    st.session_state.user = dict(r)
                    st.rerun()
                else:
                    st.error("Identifiants incorrects.")
            st.caption("Mot de passe oublié : contactez CROC (réinitialisation par e-mail non incluse dans cette version).")
        with t2:
            f = st.text_input("Prénom", key="rf")
            l = st.text_input("Nom", key="rl")
            ph = st.text_input("Téléphone", key="rp")
            em = st.text_input("E-mail", key="re")
            p1 = st.text_input("Mot de passe (8 caractères min.)", type="password", key="r1")
            p2 = st.text_input("Confirmer le mot de passe", type="password", key="r2")
            if st.button("Créer mon compte"):
                if not (f.strip() and l.strip()):
                    st.error("Nom et prénom requis.")
                elif not ok_phone(ph):
                    st.error("Téléphone marocain invalide.")
                elif not ok_email(em.strip()):
                    st.error("E-mail invalide.")
                elif len(p1) < 8 or p1 != p2:
                    st.error("Mot de passe trop court ou différent de la confirmation.")
                elif q("SELECT 1 FROM users WHERE email=? OR phone=?", (em.strip().lower(), norm_phone(ph)), one=True):
                    st.error("Un compte existe déjà avec cet e-mail ou ce téléphone.")
                else:
                    salt = secrets.token_hex(16)
                    run("INSERT INTO users(first,last,phone,email,salt,pw) VALUES(?,?,?,?,?,?)",
                        (f.strip(), l.strip(), norm_phone(ph), em.strip().lower(), salt, hash_pw(p1, salt)))
                    st.success("Compte créé, vous pouvez vous connecter.")
        return
    st.write(f"Bonjour **{u['first']}** 👋")
    if st.button("Se déconnecter"):
        st.session_state.user = None
        st.rerun()
    orders = q("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC", (u["id"],))
    k = st.columns(4)
    k[0].metric("Commandes", len(orders))
    k[1].metric("En cours", sum(o["status"] not in ("Livrée", "Annulée") for o in orders))
    k[2].metric("Livrées", sum(o["status"] == "Livrée" for o in orders))
    k[3].metric("Total achats (DH)", f"{sum(o['total'] for o in orders if o['status'] != 'Annulée'):.0f}")
    with st.expander("Mon profil"):
        c = st.text_input("Ville", u["city"] or "", key="pc")
        a = st.text_area("Adresse principale", u["address"] or "", key="pa")
        ph = st.text_input("Téléphone", u["phone"], key="pph")
        if st.button("Enregistrer"):
            if not ok_phone(ph):
                st.error("Téléphone invalide.")
            else:
                run("UPDATE users SET city=?, address=?, phone=? WHERE id=?", (c, a, norm_phone(ph), u["id"]))
                st.session_state.user = dict(q("SELECT * FROM users WHERE id=?", (u["id"],), one=True))
                st.success("Profil mis à jour.")
    st.subheader("Mes commandes")
    for o in orders:
        show_order(o)

def page_track():
    st.title("Suivre une commande")
    n = st.text_input("Numéro de commande (ex : CROC-00001)")
    ph = st.text_input("Téléphone utilisé pour la commande")
    if st.button("Suivre"):
        m = re.fullmatch(r"CROC-(\d+)", n.strip().upper())
        o = q("SELECT * FROM orders WHERE id=? AND phone=?", (int(m.group(1)), norm_phone(ph)), one=True) if m else None
        if o:
            show_order(o)
        else:
            st.error("Aucune commande ne correspond à ces informations.")

# ---------------------------------------------------------------- ADMIN
def page_admin():
    st.title("Administration")
    if not st.session_state.admin:
        pw = st.text_input("Mot de passe administrateur", type="password")
        if st.button("Entrer"):
            if secrets.compare_digest(pw, admin_password()):
                st.session_state.admin = True
                st.rerun()
            else:
                st.error("Mot de passe incorrect.")
        return
    if admin_password() == "croc-admin-change-me":
        st.warning("Changez le mot de passe admin (variable ADMIN_PASSWORD).")
    if st.button("Quitter l'admin"):
        st.session_state.admin = False
        st.rerun()
    tabs = st.tabs(["Vue d'ensemble", "Commandes", "Produits & coûts", "Promos", "Réglages", "Clients"])
    orders = df("SELECT * FROM orders")
    valid = orders[orders["status"] != "Annulée"]

    # ---- Vue d'ensemble
    with tabs[0]:
        c = st.columns(4)
        c[0].metric("Commandes", len(orders))
        c[1].metric("Chiffre d'affaires (DH)", f"{valid['total'].sum():.0f}")
        c[2].metric("Panier moyen (DH)", f"{valid['total'].mean():.0f}" if len(valid) else "0")
        c[3].metric("Livrées", int((orders["status"] == "Livrée").sum()))
        if len(orders):
            st.write(orders["status"].value_counts().to_frame("Nombre"))
        rev = (valid["subtotal"] - valid["discount"]).sum()
        cogs = valid["cogs"].sum()
        deliv = (valid["delivery_cost"] - valid["delivery_fee"]).sum()
        other = float(S("other_charges"))
        st.subheader("Rentabilité")
        d = st.columns(4)
        d[0].metric("Coût de revient vendu (DH)", f"{cogs:.0f}")
        d[1].metric("Marge brute (DH)", f"{rev - cogs:.0f}")
        d[2].metric("Marge brute (%)", f"{(rev - cogs) / rev * 100:.1f}" if rev else "0")
        d[3].metric("Remises accordées (DH)", f"{valid['discount'].sum():.0f}")
        st.write(f"Livraison supportée par CROC : **{deliv:.0f} DH** · Autres charges saisies : **{other:.0f} DH** "
                 f"· Résultat estimé : **{rev - cogs - deliv - other:.0f} DH** "
                 f"(≠ bénéfice net : impôts, personnel, pub… à ajouter).")
        if len(valid):
            v2 = valid.assign(jour=pd.to_datetime(valid["created"]).dt.date)
            st.bar_chart(v2.groupby("jour")["total"].sum())
        top = df("SELECT product_name, SUM(qty*pieces) AS boules FROM order_items GROUP BY product_name ORDER BY boules DESC")
        st.write("Produits les plus vendus")
        st.dataframe(top, hide_index=True)

    # ---- Commandes
    with tabs[1]:
        stt = st.selectbox("Filtrer par statut", ["Tous"] + STATUTS + ["Annulée"])
        term = st.text_input("Rechercher (nom, téléphone, n°)")
        for o in q("SELECT * FROM orders ORDER BY id DESC"):
            if stt != "Tous" and o["status"] != stt:
                continue
            if term and term.lower() not in f"{o['name']} {o['phone']} {ref(o['id'])}".lower():
                continue
            with st.expander(f"{ref(o['id'])} · {o['name']} · {o['total']:.0f} DH · {o['status']}"):
                st.write(f"{o['phone']} · {o['email']} · {o['address']}, {o['city']} · {o['notes'] or ''}")
                for i in q("SELECT * FROM order_items WHERE order_id=?", (o["id"],)):
                    st.write(f"- {i['product_name']} — boîte de {i['pieces']} × {i['qty']}")
                opts = STATUTS + ["Annulée"]
                ns = st.selectbox("Statut", opts, index=opts.index(o["status"]), key=f"s{o['id']}")
                note = st.text_input("Note interne", o["admin_notes"] or "", key=f"n{o['id']}")
                if st.button("Enregistrer", key=f"b{o['id']}"):
                    if ns != o["status"]:
                        set_status(o["id"], ns)
                    run("UPDATE orders SET admin_notes=? WHERE id=?", (note, o["id"]))
                    st.success("Mis à jour")
                    st.rerun()
        st.download_button("Exporter les commandes (CSV)", orders.to_csv(index=False).encode("utf-8-sig"),
                           "commandes_croc.csv")

    # ---- Produits & coûts
    with tabs[2]:
        tgt = float(S("target_margin"))
        rows = []
        for v in q("SELECT v.*, p.name, p.cost_ball FROM variants v JOIN products p ON p.id=v.product_id"):
            cost = v["cost_ball"] * v["pieces"] + float(S(f"packaging_{v['pieces']}") or 0)
            minp = cost / (1 - tgt / 100) if tgt < 100 else 0
            rows.append({"Produit": v["name"], "Format": v["pieces"], "Coût de revient": round(cost, 2),
                         "Prix": v["price"], "Marge DH": round(v["price"] - cost, 2),
                         "Marge %": round((v["price"] - cost) / v["price"] * 100, 1) if v["price"] else 0,
                         "Prix min. (marge cible)": round(minp, 2),
                         "Alerte": "Coût à renseigner" if cost == 0 else ("⚠ Prix trop bas" if v["price"] < minp else "OK")})
        st.dataframe(pd.DataFrame(rows), hide_index=True)
        pid_map = {p["name"]: p["id"] for p in q("SELECT * FROM products")}
        sel = st.selectbox("Modifier un produit", list(pid_map))
        p = q("SELECT * FROM products WHERE id=?", (pid_map[sel],), one=True)
        n = st.text_input("Nom", p["name"], key=f"pn{p['id']}")
        de = st.text_area("Description", p["description"] or "", key=f"pd{p['id']}")
        compo = st.multiselect("Composition (ingrédients utilisés)", list(INGREDIENTS),
                               default=[i for i in (p["ingredients"] or "").split(", ") if i in INGREDIENTS],
                               key=f"pi{p['id']}")
        if compo:
            ing, al = compo_text(compo)
        else:
            ing, al = p["ingredients"] or "", p["allergens"] or ""
        st.caption("Allergènes déduits : " + (al or "aucun") + " — à vérifier avec vos étiquettes réelles.")
        cb = st.number_input("Coût de revient d'une Energy Ball de 20 g (DH) — saisi à partir de vos achats réels",
                             0.0, 1000.0, float(p["cost_ball"] or 0), 0.05, key=f"pc{p['id']}")
        act = st.checkbox("Actif (visible en boutique)", bool(p["active"]), key=f"pac{p['id']}")
        vdf = df("SELECT id, pieces, price, stock FROM variants WHERE product_id=?", (p["id"],))
        ed = st.data_editor(vdf, disabled=["id", "pieces"], hide_index=True, key=f"ed{p['id']}")
        if st.button("Enregistrer le produit"):
            run("UPDATE products SET name=?,description=?,ingredients=?,allergens=?,cost_ball=?,active=? WHERE id=?",
                (n, de, ing, al, cb, int(act), p["id"]))
            for _, r in ed.iterrows():
                run("UPDATE variants SET price=?, stock=? WHERE id=?", (float(r["price"]), int(r["stock"]), int(r["id"])))
            st.success("Produit enregistré")
            st.rerun()
        low = [f"{r['name']} ({r['pieces']}) : {r['stock']}" for r in
               q("SELECT v.*,p.name FROM variants v JOIN products p ON p.id=v.product_id WHERE v.stock<=?",
                 (S("low_stock"),))]
        if low:
            st.warning("Stock faible : " + " · ".join(low))
        with st.expander("Ajouter un produit"):
            nn = st.text_input("Nom du nouveau produit", key="newp")
            if st.button("Créer") and nn.strip():
                pid = run("INSERT INTO products(name,description,ingredients,allergens,active) VALUES(?,?,?,?,0)",
                          (nn.strip(), "", "", ""))
                for pcs in (6, 12, 24):
                    run("INSERT INTO variants(product_id,pieces,price,stock) VALUES(?,?,0,0)", (pid, pcs))
                st.rerun()

        with st.expander("Recharger le catalogue de départ"):
            st.caption("Remplace les produits par les recettes définies dans le code (RECETTES). "
                       "Les prix, stocks et coûts saisis sur les produits actuels seront perdus.")
            if st.checkbox("Je confirme", key="confirm_seed") and st.button("Recharger le catalogue"):
                cc = conn()
                seed_catalog(cc)
                cc.commit()
                cc.close()
                st.rerun()

    # ---- Promos
    with tabs[3]:
        st.dataframe(df("SELECT p.*, (SELECT COUNT(*) FROM promo_usages u WHERE u.code=p.code) AS utilisations FROM promos p"),
                     hide_index=True)
        code = st.text_input("Code (création ou modification)").upper().strip()
        pc = st.number_input("Pourcentage", 0.0, 100.0, 10.0)
        a, b = st.columns(2)
        d1 = a.text_input("Début (AAAA-MM-JJ, facultatif)")
        d2 = b.text_input("Fin (AAAA-MM-JJ, facultatif)")
        mn = st.number_input("Montant minimum (DH)", 0.0, 10000.0, 0.0)
        mu = st.number_input("Utilisations max (0 = illimité)", 0, 100000, 0)
        ac = st.checkbox("Actif", True)
        if st.button("Enregistrer le code") and code:
            run("INSERT OR REPLACE INTO promos VALUES(?,?,?,?,?,?,?)", (code, pc, d1.strip(), d2.strip(), mn, mu, int(ac)))
            st.rerun()

    # ---- Réglages
    with tabs[4]:
        for k, lab in [("delivery_fee", "Livraison facturée au client (DH)"),
                       ("delivery_cost", "Coût transporteur pour CROC (DH)"),
                       ("target_margin", "Marge brute cible (%)"),
                       ("packaging_6", "Emballage boîte de 6 (DH)"),
                       ("packaging_12", "Emballage boîte de 12 (DH)"),
                       ("packaging_24", "Emballage boîte de 24 (DH)"),
                       ("other_charges", "Autres charges à déduire (DH)"),
                       ("low_stock", "Seuil d'alerte stock")]:
            set_S(k, st.number_input(lab, 0.0, 100000.0, float(S(k)), key=f"set{k}"))
        set_S("allow_stack", int(st.checkbox("Autoriser le cumul code promo + livraison gratuite", bool(S("allow_stack")))))
        set_S("free_first", int(st.checkbox("Livraison gratuite à la 1re commande", bool(S("free_first")))))
        set_S("whatsapp", st.text_input("Numéro WhatsApp (format international, ex : 2126XXXXXXXX)",
                                        str(S("whatsapp") or "")).strip())

    # ---- Clients
    with tabs[5]:
        cl = df("""SELECT u.first, u.last, u.phone, u.email, COUNT(o.id) AS commandes,
                   COALESCE(SUM(o.total),0) AS total_dh, MAX(o.free_first) AS livraison_gratuite_utilisee
                   FROM users u LEFT JOIN orders o ON o.user_id=u.id AND o.status!='Annulée' GROUP BY u.id""")
        st.dataframe(cl, hide_index=True)
        st.download_button("Exporter les clients (CSV)", cl.to_csv(index=False).encode("utf-8-sig"), "clients_croc.csv")

# ---------------------------------------------------------------- NAVIGATION
init_db()
PAGES = ["Accueil", "Boutique", "Panier", "Mon compte", "Suivre ma commande", "Admin"]
with st.sidebar:
    st.markdown("<div class='brand'><div class='b1'>CR<span>●</span>C</div><div class='b2'>Small Bites. Big Energy.</div></div>", unsafe_allow_html=True)
    nb = sum(st.session_state.cart.values())
    page = st.radio("Menu", PAGES, key="page",
                    format_func=lambda x: f"Panier ({nb})" if x == "Panier" else x)

{"Accueil": page_home, "Boutique": page_shop, "Panier": page_cart, "Mon compte": page_account,
 "Suivre ma commande": page_track, "Admin": page_admin}[page]()

st.markdown("<div class='footer'>© CROC · Energy Balls artisanales préparées au Maroc 🇲🇦 · version 3</div>", unsafe_allow_html=True)
