# CyberBridge Guardian — Aurora UI (Streamlit)
# High-contrast neon/glass design, sticky glass nav, Duo QR gating, no stray "\n"
# Works in Colab + ngrok; uses .streamlit/config.toml and assets/custom.css

import streamlit as st
import pandas as pd
import numpy as np
import math, re, io, base64, random, time, difflib, hashlib
from datetime import datetime
from urllib.parse import urlparse

# Optional dependencies (graceful if missing)
try:
    import qrcode
    import pyotp
except Exception:
    qrcode = None
    pyotp = None

try:
    import tldextract
except Exception:
    tldextract = None

from streamlit_option_menu import option_menu

# ------------------------- Page setup -------------------------
st.set_page_config(page_title="CyberBridge Guardian", page_icon="🛡️", layout="wide")
st.markdown("<meta name='theme-color' content='#0A0B0F'>", unsafe_allow_html=True)

# Load external CSS (keeps styles sticky under Colab/ngrok)
def load_css(path: str):
    try:
        with open(path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except Exception:
        st.warning(f"Custom CSS not found at {path}")

load_css("assets/custom.css")

# ------------------------- Hero -------------------------
st.markdown(
    """
    <div class="hero fade-in">
      <div class="title">CyberBridge Guardian</div>
      <div class="kicker">Duo MFA · Umbrella DNS · Meraki Planner · Mini-SOC · ROI & Equity</div>
    </div>
    """,
    unsafe_allow_html=True,
)

tb1, tb2, tb3 = st.columns([1,2,1])
with tb1:
    demo_mode = st.checkbox("Use sample data", value=True)
with tb3:
    st.markdown('<div class="small" style="text-align:right;">© Shreeniket Bendre; projected data.</div>', unsafe_allow_html=True)

# ------------------------- Top Nav -------------------------
with st.container():
    st.markdown('<div class="cb-navwrap">', unsafe_allow_html=True)
    selected = option_menu(
        None,
        ["Home", "Duo MFA", "Umbrella DNS", "Meraki Planner", "Mini-SOC", "ROI & Equity", "Appendix"],
        icons=["house", "shield-lock", "shield-shaded", "wifi", "activity", "cash-coin", "book"],
        menu_icon="cast", default_index=0, orientation="horizontal",
        styles={
            "container": {"background-color": "transparent", "padding": "0"},
            "icon": {"color": "#22D3EE", "font-size": "18px"},
            "nav-link": {
                "font-size": "15px", "font-weight": "800",
                "text-transform": "none", "color": "#EAF2FF",
                "margin": "0 6px", "padding":"10px 14px",
                "border-radius":"12px"
            },
            "nav-link-selected": {
                "background-color": "transparent", "color": "#FFFFFF",
                "border":"1px solid rgba(255,255,255,.14)"
            },
        }
    )
    st.markdown("</div>", unsafe_allow_html=True)

# ------------------------- Utilities -------------------------
KNOWN_BRANDS = [
    "google","microsoft","office","outlook","teams","azure","onedrive",
    "cisco","meraki","umbrella","duo","blackboard","canvas","zoom",
    "box","dropbox","github","slack","paypal","stripe","bankofamerica",
    "wellsfargo","chase","university","student","finaid","bursar"
]
SUSP_TLDS = {"zip","kim","xyz","top","gq","ml","cf","tk","work","fit","rest","country","asia","science"}

def download_bytes(filename: str, raw: bytes, label: str):
    b64 = base64.b64encode(raw).decode()
    st.markdown(f'<a download="{filename}" href="data:application/octet-stream;base64,{b64}">{label}</a>',
                unsafe_allow_html=True)

def domain_parts(url: str):
    parsed = urlparse(url if re.match(r"^\w+://", url) else "http://" + url)
    host = parsed.netloc or parsed.path
    if tldextract:
        ext = tldextract.extract(host)
        domain = ext.registered_domain or (f"{ext.domain}.{ext.suffix}" if ext.domain and ext.suffix else ext.domain)
        sld = ext.domain or ""
        tld = ext.suffix or ""
        sub = ext.subdomain or ""
    else:
        parts = host.split(".")
        if len(parts) >= 2:
            domain = ".".join(parts[-2:])
            sld, tld = parts[-2], parts[-1]
            sub = ".".join(parts[:-2])
        else:
            domain, sld, tld, sub = host, host, "", ""
    return host, domain, sld, tld, sub, parsed

def shannon_entropy(s: str):
    if not s: return 0.0
    from math import log2
    probs = [float(s.count(c)) / len(s) for c in set(s)]
    return -sum(p * log2(p) for p in probs)

def looks_like_ip(host: str): return bool(re.match(r"^\d{1,3}(\.\d{1,3}){3}$", host))
def punycode_present(host: str): return "xn--" in host.lower()

def brand_lookalike_score(sld: str):
    if not sld: return 0.0
    close = max(difflib.SequenceMatcher(a=sld.lower(), b=b).ratio() for b in KNOWN_BRANDS)
    exact = sld.lower() in KNOWN_BRANDS
    return 0.0 if exact else close

def url_feature_vector(url: str):
    host, domain, sld, tld, sub, parsed = domain_parts(url)
    path = parsed.path or ""
    length = len(url)
    sub_count = sub.count(".") + (1 if sub else 0)
    dash_count = url.count("-")
    at_count = url.count("@")
    digit_ratio = sum(c.isdigit() for c in host) / max(1, len(host))
    entropy = shannon_entropy(host + path)
    ip = looks_like_ip(host)
    puny = punycode_present(host)
    tld_flag = tld.split(".")[-1] if tld else ""
    tld_susp = 1 if tld_flag in SUSP_TLDS else 0
    brand_score = brand_lookalike_score(sld)
    path_deep = path.count("/")
    has_port = bool(re.search(r":\d+$", host))
    return {
        "length": length, "subdomains": sub_count, "dashes": dash_count, "ats": at_count,
        "digit_ratio": digit_ratio, "entropy": entropy,
        "ip": int(ip), "punycode": int(puny), "tld_suspicious": tld_susp,
        "brand_lookalike": brand_score, "path_depth": path_deep, "has_port": int(has_port),
        "sld": sld, "tld": tld_flag, "host": host, "domain": domain
    }

def risk_score_from_features(f):
    score = 0.0
    score += min(30, f["length"]/8)
    score += 7 * f["subdomains"]
    score += 3 * f["dashes"]
    score += 12 * f["ats"]
    score += 30 * f["digit_ratio"]
    score += min(20, 4 * f["entropy"])
    score += 20 * f["ip"]
    score += 20 * f["punycode"]
    score += 12 * f["tld_suspicious"]
    score += 35 * max(0, f["brand_lookalike"] - 0.65)
    score += 2 * f["path_depth"]
    score += 8 * f["has_port"]
    return max(0.0, min(100.0, score))

def metric_tile(label, value, sub=""):
    st.markdown(
        f"""
        <div class="metric">
          <div class="big">{value}</div>
          <div class="sub">{label}{(" — " + sub) if sub else ""}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ------------------------- Pages -------------------------
if selected == "Home":
    with st.container():
        st.markdown('<div class="card fade-in">', unsafe_allow_html=True)
        st.markdown("### Overview")
        st.markdown(
            "CyberBridge Guardian turns Cisco security building blocks into an operational, explainable demo for MSIs/HBCUs. "
            "Duo drives phishing resistance; Umbrella reduces exposure; Meraki improves reliability; the Mini-SOC trains students; "
            "and ROI is framed in equity outcomes."
        )
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br/>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1: metric_tile("Reliability uplift (zones)", "65% → 99%", "Meraki plan")
    with c2: metric_tile("Phishing reduction", "≈ 40%+", "Duo MFA")
    with c3: metric_tile("Pre-block rate", "15–30%", "Umbrella DNS")
    with c4: metric_tile("Net annual savings", "≈ $1.4M", "~5% breach reduction")

    st.markdown("<hr/>", unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="card fade-in">', unsafe_allow_html=True)
        st.markdown("**Design principles**")
        st.markdown(
            "- Tie controls to institutional outcomes.\n"
            "- Keep signals explainable and transparent.\n"
            "- Reduce operator effort; keep paths to API integration.\n"
            "- Use visuals that teach, not just decorate."
        )
        st.markdown("</div>", unsafe_allow_html=True)

# ------------------------- Duo MFA (QR-only, inline verify) -------------------------
elif selected == "Duo MFA":
    st.markdown('<div class="card fade-in">', unsafe_allow_html=True)
    st.markdown("## Duo MFA, Enroll & Verify via a 6-digit TOTP")
    st.markdown(
        "- Enrollment is via QR **scanned in Duo Mobile**.\n"
        "- After scanning, enter the **6-digit code** from the app and click **Verify**.\n"
        "- This demo only stores a simple device-binding hash in session."
    )
    st.markdown("</div>", unsafe_allow_html=True)

    if qrcode is None or pyotp is None:
        st.warning("For the live demo, install: `pip install pyotp qrcode[pil]`")
    else:
        # Initialize session state
        if "totp_secret" not in st.session_state:
            st.session_state.totp_secret = pyotp.random_base32()
            st.session_state.bound_hash = None
            st.session_state.duo_ack = False

        secret = st.session_state.totp_secret

        # Two-column flow with a big arrow in the middle
        col_left, col_arrow, col_right = st.columns([1.15, 0.2, 1], gap="large")

        # ---------- LEFT: STEP 1 — Scan QR via Duo Mobile ----------
        with col_left:
            st.markdown('<div class="card fade-in">', unsafe_allow_html=True)
            st.subheader("Step 1. Scan the QR in Duo Mobile (please open the Duo app then press the show QR button below)")

            user_email = st.text_input("Campus email", "student@example.edu")
            issuer = st.text_input("Issuer", "CyberBridge Guardian (Duo-style)")

            # Reset / re-enroll
            if st.button("Reset QR (re-enroll)"):
                st.session_state.totp_secret = pyotp.random_base32()
                st.session_state.bound_hash = None
                st.session_state.duo_ack = False
                secret = st.session_state.totp_secret
                st.success("New secret generated. Re-scan the fresh QR.")

            st.markdown(
                "Open **Duo Mobile** → **Add** → **Use QR scanner**. "
                "Then scan the QR below to bind this device."
            )

            # Acknowledge instructions to reveal QR (prevents accidental screenshots)
            show_qr = st.button("I have Duo Mobile open... Show QR", disabled=st.session_state.duo_ack)
            if show_qr:
                st.session_state.duo_ack = True
                st.toast("Duo instructions acknowledged.", icon="✅")

            st.markdown("<hr/>", unsafe_allow_html=True)

            if st.session_state.duo_ack:
                uri = pyotp.TOTP(secret).provisioning_uri(
                    name=user_email or "user@campus.edu",
                    issuer_name=issuer or "CyberBridge"
                )
                img = qrcode.make(uri)
                buf = io.BytesIO(); img.save(buf, format="PNG")
                st.image(buf.getvalue(), caption="Scan this QR with Duo Mobile (or Google Authenticator / 1Password)")
                st.caption("Demo transparency: secret shown below; in production this is never visible.")
                st.code(secret, language="text")
            else:
                st.info("Click the acknowledge button above to reveal the QR code.")

            st.markdown("</div>", unsafe_allow_html=True)

        # ---------- MIDDLE: ARROW ----------
        with col_arrow:
            st.markdown(
                '<div class="fade-in" style="font-size:48px; line-height:1; text-align:center; padding-top:120px;">➡️</div>',
                unsafe_allow_html=True
            )

        # ---------- RIGHT: STEP 2 — Enter code & Verify ----------
        with col_right:
            st.markdown('<div class="card fade-in">', unsafe_allow_html=True)
            st.subheader("Step 2. Enter the 6-digit code from Duo")

            code_raw = st.text_input("6-digit code", max_chars=6, help="Type the 6 digits shown in Duo Mobile")
            code = re.sub(r"[^0-9]", "", code_raw or "")
            if code_raw and code_raw != code:
                st.caption("Non-digits removed; codes are numeric only.")

            # Timer hint
            totp = pyotp.TOTP(secret)
            now = int(time.time()); period = getattr(totp, "interval", 30)
            remaining = period - (now % period)
            st.caption(f"Code refreshes in about {remaining}s")

            if st.button("Verify"):
                if len(code) != 6:
                    st.error("Please enter the 6-digit code from Duo Mobile.")
                else:
                    ok = totp.verify(code.strip(), valid_window=1)
                    if ok:
                        # Bind on first success (demo only)
                        if st.session_state.get("bound_hash") is None:
                            bind_raw = f"{(user_email or 'user@campus.edu')}|{secret}"
                            st.session_state.bound_hash = hashlib.sha256(bind_raw.encode()).hexdigest()
                        st.success("Approved — Duo code verified and device bound.")
                        try: st.balloons()
                        except Exception: pass
                    else:
                        st.error("Invalid or expired code. Open Duo Mobile and try the current 6-digit code.")

            st.markdown("</div>", unsafe_allow_html=True)

# ------------------------- Umbrella DNS -------------------------
elif selected == "Umbrella DNS":
    st.markdown('<div class="card fade-in">', unsafe_allow_html=True)
    st.markdown("## Umbrella DNS Guard")
    st.markdown(
        "- Maintain allow / block / watch lists.\n"
        "- Explainable URL risk (lookalike, punycode, TLD, entropy, port, etc.).\n"
        "- Export results for audit and education."
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # Lists
    if "blocklist" not in st.session_state:
        st.session_state.blocklist = set(["examp1e-helpdesk.com","login-verify-secure.net"]) if demo_mode else set()
    if "allowlist" not in st.session_state:
        st.session_state.allowlist = set(["duo.com","cisco.com","meraki.cisco.com","canvas.instructure.com"]) if demo_mode else set()
    if "watchlist" not in st.session_state:
        st.session_state.watchlist = set(["out1ook-login-secure.com","micr0soft-support-secure-login.com"]) if demo_mode else set()

    three = st.columns(3)
    with three[0]:
        st.markdown('<div class="card fade-in">', unsafe_allow_html=True)
        st.markdown("### Blocklist")
        blk_add = st.text_input("Add domain to block")
        if st.button("Add → Blocklist"):
            if blk_add.strip(): st.session_state.blocklist.add(blk_add.strip().lower())
        st.code("\n".join(sorted(st.session_state.blocklist)) or "(empty)")
        st.markdown("</div>", unsafe_allow_html=True)

    with three[1]:
        st.markdown('<div class="card fade-in">', unsafe_allow_html=True)
        st.markdown("### Allowlist")
        allow_add = st.text_input("Add domain to allow")
        if st.button("Add → Allowlist"):
            if allow_add.strip(): st.session_state.allowlist.add(allow_add.strip().lower())
        st.code("\n".join(sorted(st.session_state.allowlist)) or "(empty)")
        st.markdown("</div>", unsafe_allow_html=True)

    with three[2]:
        st.markdown('<div class="card fade-in">', unsafe_allow_html=True)
        st.markdown("### Watchlist")
        watch_add = st.text_input("Add domain to watch")
        if st.button("Add → Watchlist"):
            if watch_add.strip(): st.session_state.watchlist.add(watch_add.strip().lower())
        st.code("\n".join(sorted(st.session_state.watchlist)) or "(empty)")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br/>", unsafe_allow_html=True)

    st.markdown('<div class="card fade-in">', unsafe_allow_html=True)
    st.subheader("Bulk evaluate (one URL per line)")
    sample_bulk = (
        "out1ook-login-secure.com\n"
        "http://xn--pple-43d.com\n"
        "https://duo.com\n"
        "http://192.168.1.23/login\n"
        "finaid-portal.support-verify.net"
    )
    urls_bulk = st.text_area("URLs", height=120, value=(sample_bulk if demo_mode else ""))

    def policy_decision(u: str):
        host, domain, sld, tld, sub, parsed = domain_parts(u)
        d = (domain or host).lower()
        if any(d.endswith(a) for a in st.session_state.allowlist):
            return "ALLOW", 0
        if any(d.endswith(b) for b in st.session_state.blocklist):
            return "BLOCK", 100
        for w in st.session_state.watchlist:
            sim = difflib.SequenceMatcher(a=(sld or d).split(":")[0], b=w.split(".")[0]).ratio()
            if sim > 0.8 or d.endswith(w):
                return "WATCH", 60
        f = url_feature_vector(u)
        sc = risk_score_from_features(f)
        if sc >= 60: return "BLOCK", sc
        if sc >= 25: return "WATCH", sc
        return "ALLOW", sc

    if st.button("Evaluate Policy"):
        rows = []
        for line in urls_bulk.splitlines():
            u = line.strip()
            if not u: continue
            decision, sc = policy_decision(u)
            rows.append({"url": u, "decision": decision, "score": round(sc,1)})
        if rows:
            df = pd.DataFrame(rows).sort_values(["decision","score"], ascending=[True, False])
            st.dataframe(df, use_container_width=True)
            download_bytes("dns_policy_results.csv", df.to_csv(index=False).encode(), "Download CSV")
            try: st.balloons()
            except Exception: pass
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br/>", unsafe_allow_html=True)

    st.markdown('<div class="card fade-in">', unsafe_allow_html=True)
    st.subheader("Explain a single URL")
    bad = st.text_input("URL to explain", "https://micr0soft-support-secure-login.com/renew?session=9876")
    if st.button("Explain URL"):
        f = url_feature_vector(bad.strip()); sc = risk_score_from_features(f)
        label = "Low" if sc < 25 else ("Medium" if sc < 60 else "High")
        st.markdown(f"**Risk:** {label} — **Score:** {sc:.1f}/100")
        st.write(pd.DataFrame([f]).T.rename(columns={0:"value"}))
        st.caption("Signals: brand lookalike similarity, punycode, suspicious TLDs, IP host, deep paths, non-standard port, high entropy.")
    st.markdown("</div>", unsafe_allow_html=True)

# ------------------------- Meraki Planner -------------------------
elif selected == "Meraki Planner":
    st.markdown('<div class="card fade-in">', unsafe_allow_html=True)
    st.markdown("## Meraki Reliability Planner")
    st.markdown(
        "- Estimate AP counts for high-usage zones.\n"
        "- Visualize stability around your target after redundancy."
    )
    st.markdown("</div>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        peak_concurrency = st.slider("Peak concurrent users in zone", 50, 2000, 600)
        sqft = st.number_input("Zone area (sq ft)", 35000, step=1000)
    with col2:
        capacity_per_ap = st.slider("Users per AP (Meraki 6/6E)", 30, 120, 60)
        overlap = st.slider("AP overlap (redundancy %)", 0, 50, 20)
    with col3:
        target_uptime = st.slider("Target uptime (%)", 95, 100, 99)

    raw_aps = math.ceil(peak_concurrency / capacity_per_ap)
    aps = math.ceil(raw_aps * (1 + overlap/100))
    density = round(aps / max(1, sqft/1000), 2)

    cA, cB, cC = st.columns(3)
    with cA: metric_tile("APs required (zone)", f"{aps} APs", f"base {raw_aps}")
    with cB: metric_tile("AP density", f"{density} per 1k sq ft")
    with cC: metric_tile("Reliability target", f"{target_uptime}%")

    st.markdown("<br/>", unsafe_allow_html=True)
    np.random.seed(7)
    before_uptime = np.clip(np.random.normal(0.65, 0.07, 30), 0.3, 0.95)
    after_uptime  = np.clip(np.random.normal(target_uptime/100.0, 0.02, 30), 0.8, 1.0)
    df_health = pd.DataFrame({
        "day": pd.date_range(end=datetime.today(), periods=30).date,
        "before": (before_uptime*100).round(1),
        "after":  (after_uptime*100).round(1),
    })
    st.line_chart(df_health.set_index("day"))
    st.caption("For production, ingest Meraki telemetry; this demo shows stabilization near your target with redundancy.")

# ------------------------- Mini-SOC -------------------------
elif selected == "Mini-SOC":
    st.markdown('<div class="card fade-in">', unsafe_allow_html=True)
    st.markdown("## Mini-SOC (Simulated)")
    st.markdown("Generates realistic DNS blocks, login anomalies, and policy hits.")
    st.markdown("</div>", unsafe_allow_html=True)

    if "soc_events" not in st.session_state or st.button("Regenerate Events"):
        seeds = [
            ("DNS_BLOCK", "Umbrella", "Blocked malicious domain", "micr0soft-secure-login.com"),
            ("DNS_BLOCK", "Umbrella", "Blocked lookalike", "out1ook-helpdesk.net"),
            ("LOGIN_ANOMALY", "Duo", "Impossible travel sign-in", "user01@campus.edu"),
            ("LOGIN_ANOMALY", "Duo", "Possible MFA fatigue attempt", "student23@campus.edu"),
            ("POLICY_HIT", "Guardian", "Watchlist matched", "finaid-portal.support-verify.net"),
            ("POLICY_HIT", "Guardian", "Suspicious TLD", "student-aid.xyz"),
            ("TRAINING", "NetAcad", "Student flagged phishing email", "s019"),
        ]
        rows = []
        now = int(time.time())
        for _ in range(50):
            t = now - random.randint(0, 7*24*3600)
            ev = random.choice(seeds)
            severity = random.choice(["low","medium","high"])
            rows.append({
                "time": datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M"),
                "type": ev[0], "source": ev[1], "description": ev[2], "detail": ev[3],
                "severity": severity,
            })
        st.session_state.soc_events = pd.DataFrame(rows).sort_values("time", ascending=False).reset_index(drop=True)

    df = st.session_state.soc_events.copy()
    f1, f2, f3 = st.columns(3)
    with f1: types = st.multiselect("Type", options=sorted(df["type"].unique()), default=list(sorted(df["type"].unique())))
    with f2: sevs  = st.multiselect("Severity", options=sorted(df["severity"].unique()), default=list(sorted(df["severity"].unique())))
    with f3: query = st.text_input("Search")

    mask = df["type"].isin(types) & df["severity"].isin(sevs)
    if query.strip():
        pat = re.compile(re.escape(query.strip()), re.IGNORECASE)
        mask &= df.apply(lambda r: bool(pat.search(" ".join(map(str, r.values)))), axis=1)

    view = df[mask]
    st.dataframe(view, use_container_width=True, height=440)
    download_bytes("mini_soc_events.csv", view.to_csv(index=False).encode(), "Download CSV")

# ------------------------- ROI & Equity -------------------------
elif selected == "ROI & Equity":
    st.markdown('<div class="card fade-in">', unsafe_allow_html=True)
    st.markdown("## ROI & Equity Impact")
    st.markdown(
        "- Estimate incidents avoided via MFA, DNS filtering, and training.\n"
        "- Translate savings into budget and tuition equivalents."
    )
    st.markdown("</div>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        pop_students = st.number_input("Students", 3500, step=50)
        pop_staff = st.number_input("Faculty/Staff", 500, step=10)
        baseline_incid = st.number_input("Baseline incidents per year", 4, step=1)
    with col2:
        mfa_adopt = st.slider("MFA adoption (%)", 0, 100, 85)
        dns_on = st.checkbox("Umbrella DNS filtering enabled", True)
        training_pct = st.slider("Security training completion (%)", 0, 100, 70)
    with col3:
        cost_per_incident = st.number_input("Avg. cost per incident ($)", 2_700_000, step=50_000)
        program_cost = st.number_input("Annual program cost ($)", 300_000, step=10_000)

    mfa_effect = 0.40 * (mfa_adopt/100.0)
    dns_effect = 0.15 if dns_on else 0.0
    training_effect = 0.10 * (training_pct/100.0)
    total_reduction = min(0.75, mfa_effect + dns_effect + training_effect)

    avoided = baseline_incid * total_reduction
    gross = avoided * cost_per_incident
    net = gross - program_cost
    tuition_equiv = max(0, net) / 28000.0

    cA, cB, cC, cD = st.columns(4)
    with cA: metric_tile("Incidents avoided / yr", f"{avoided:.2f}")
    with cB: metric_tile("Gross savings / yr", f"${gross:,.0f}")
    with cC: metric_tile("Program cost / yr", f"${program_cost:,.0f}")
    with cD: metric_tile("Tuition equivalents", f"{int(tuition_equiv):,} students")

    st.markdown("<hr/>", unsafe_allow_html=True)
    st.markdown(
        f"With Duo MFA at **{mfa_adopt}%**, Umbrella DNS "
        f"{'**enabled**' if dns_on else '**disabled**'}, and **{training_pct}%** training completion, "
        f"the modeled reduction in successful phishing/ransomware is **~{int(total_reduction*100)}%**. "
        f"Against **{baseline_incid}** incidents/year at **${cost_per_incident:,.0f}** each, "
        f"this avoids **{avoided:.2f}** incidents and yields **${gross:,.0f}** in gross savings. "
        f"After program costs (**${program_cost:,.0f}**), net impact is **${net:,.0f}** "
        f"(~**{int(tuition_equiv):,}** tuition equivalents)."
    )

# ------------------------- Appendix -------------------------
elif selected == "Appendix":
    st.markdown('<div class="card fade-in">', unsafe_allow_html=True)
    st.markdown("## Appendix: Context & Stakeholders")
    st.markdown(
        "- Higher-ed threats and constraints at MSIs/HBCUs.\n"
        "- How Meraki (reliability), Umbrella (pre-block), Duo (MFA), and NetAcad (people) combine into CyberBridge."
    )
    st.markdown("### Stakeholders")
    st.markdown(
        "- **Internal (Cisco):** Social Impact & Inclusion, NetAcad staff, regional AEs\n"
        "- **External:** Partner MSIs/HBCUs (AL/MS/TX), faculty & IT, nonprofits (e.g., MS-CC), partners\n"
        "- **Community:** Students & families, employers"
    )
    st.markdown("### Why this web application")
    st.markdown(
        "- **Operational:** day-to-day impact beyond slideware.\n"
        "- **Explainable:** transparent risk factors and policy rationales.\n"
        "- **Educational:** student SOC rotations with realistic exercises.\n"
        "- **Measurable:** ROI in budgeting/equity terms."
    )
    st.markdown("</div>", unsafe_allow_html=True)

# ------------------------- Footer -------------------------
st.markdown("<hr/>", unsafe_allow_html=True)
st.markdown('<div class="small" style="text-align:center;">© CyberBridge — Built for MSIs/HBCUs. Synthetic data only; no institutional credentials.</div>',
            unsafe_allow_html=True)
