import streamlit as st
from streamlit_js_eval import get_geolocation
import pandas as pd
import pydeck as pdk
import math
import time
import random

# ---------------------------------------------------------
# 1. CONFIGURATION & PREMIUM IOS STYLING
# ---------------------------------------------------------
st.set_page_config(page_title="Valentine's Mission", page_icon="📍", layout="wide")

st.markdown("""
    <style>
    /* RESET STREAMLIT DEFAULTS */
    .stApp {
        background: linear-gradient(180deg, #FFDEE9 0%, #B5FFFC 100%);
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Hide Header/Footer/Hamburger */
    header {visibility: hidden;}
    footer {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    
    /* Remove padding for edge-to-edge feel */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 5rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 100%;
    }

    /* -------------------------- */
    /* IOS-STYLE CARDS (Glassmorphism) */
    /* -------------------------- */
    .ios-card {
        background: rgba(255, 255, 255, 0.65);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border-radius: 24px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.07);
        border: 1px solid rgba(255, 255, 255, 0.4);
    }
    
    .briefing-card {
        background: rgba(255, 255, 255, 0.85);
        border-radius: 30px;
        padding: 40px 20px;
        text-align: center;
        box-shadow: 0 20px 50px rgba(0,0,0,0.1);
        margin-top: 40px;
    }

    /* TYPOGRAPHY */
    h1 {
        font-weight: 800;
        font-size: 28px !important;
        color: #1c1c1e;
        margin-bottom: 10px;
        text-align: center;
        letter-spacing: -0.5px;
    }
    
    h2 {
        font-weight: 600;
        font-size: 20px !important;
        color: #ff2e63;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 20px;
        text-align: center;
    }
    
    p {
        font-size: 17px;
        line-height: 1.5;
        color: #3a3a3c;
        margin-bottom: 15px;
    }
    
    .small-text {
        font-size: 14px;
        color: #8e8e93;
        text-align: center;
    }

    /* PROGRESS BAR (Top Inventory) */
    .letter-row {
        display: flex;
        justify-content: center;
        gap: 8px;
        margin-bottom: 25px;
    }
    
    .letter-pill {
        width: 45px;
        height: 55px;
        background: #fff;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 800;
        font-size: 24px;
        color: #ff2e63;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        border: 2px solid #fff;
    }
    
    .letter-pill.locked {
        background: rgba(255,255,255,0.3);
        color: rgba(0,0,0,0.2);
        border: none;
        box-shadow: none;
    }

    /* MAPS-STYLE BUTTONS */
    .stButton > button {
        width: 100%;
        background-color: #007AFF; /* iOS Blue */
        color: white;
        font-weight: 600;
        font-size: 17px;
        padding: 14px 20px;
        border-radius: 14px;
        border: none;
        box-shadow: 0 4px 12px rgba(0, 122, 255, 0.3);
        transition: transform 0.1s ease;
    }
    
    .stButton > button:active {
        transform: scale(0.96);
    }
    
    /* Secondary Button Style (for Check Location) */
    .check-btn > button {
        background-color: #34C759 !important; /* iOS Green */
        box-shadow: 0 4px 12px rgba(52, 199, 89, 0.3) !important;
    }

    /* ANIMATIONS */
    @keyframes flip-final {
        0% { transform: rotateX(0deg); }
        100% { transform: rotateX(180deg) translateY(-4px); }
    }
    .flip-text {
        display: inline-block;
        animation: flip-final 2s forwards 0.5s;
        color: #ff2e63;
    }

    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. STATE MANAGEMENT
# ---------------------------------------------------------

if 'stage' not in st.session_state:
    st.session_state.stage = 0
if 'radius_miles' not in st.session_state:
    st.session_state.radius_miles = 0.25
if 'can_take_photo' not in st.session_state:
    st.session_state.can_take_photo = False

# DATA: u - N - f - O - r - D
STOPS = [
    {"name": "Start: Davis St", "lat": 42.0451, "lon": -87.6877, "letter": "u", "task": "Selfie on the platform."},
    {"name": "The Conservatory", "lat": 41.9245, "lon": -87.6348, "letter": "N", "task": "Find a flower matching your outfit."},
    {"name": "Royal Palms", "lat": 41.9105, "lon": -87.6775, "letter": "f", "task": "Capture the shuffleboard vibes."},
    {"name": "Wicker Park", "lat": 41.9088, "lon": -87.6770, "letter": "O", "task": "Find something vintage."},
    {"name": "QXY Dumplings", "lat": 41.8527, "lon": -87.6322, "letter": "r", "task": "Snap the soup dumplings!"}, 
    {"name": "Navy Pier", "lat": 41.8917, "lon": -87.6043, "letter": "D", "task": "Skyline background needed."}
]

def get_dist_miles(lat1, lon1, lat2, lon2):
    return math.sqrt(((lat2 - lat1) * 69.0)**2 + ((lon2 - lon1) * 52.0)**2)

# ---------------------------------------------------------
# 3. UI RENDERER
# ---------------------------------------------------------

# --- HEADER (Only show during game) ---
if 0 < st.session_state.stage < 8:
    # Render the "Inventory" Pills
    cols = st.columns([1, 6, 1])
    with cols[1]:
        html_pills = '<div class="letter-row">'
        for i in range(6):
            if i < (st.session_state.stage - 1):
                html_pills += f'<div class="letter-pill">{STOPS[i]["letter"]}</div>'
            else:
                html_pills += '<div class="letter-pill locked">?</div>'
        html_pills += '</div>'
        st.markdown(html_pills, unsafe_allow_html=True)

# =========================================================
# STAGE 0: BRIEFING (The "Welcome" Screen)
# =========================================================
if st.session_state.stage == 0:
    st.markdown("""
        <div class="briefing-card">
            <div style="font-size: 60px; margin-bottom: 20px;">🕵️‍♀️</div>
            <h1>MISSION PROTOCOL</h1>
            <p style="color: #8e8e93; font-weight: 500;">Feb 14, 2026 • Chicago, IL</p>
            <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
            <div style="text-align: left; padding: 0 10px;">
                <p><b>🎯 OBJECTIVE:</b><br>Navigate to 6 secure locations.</p>
                <p><b>📡 TOOLS:</b><br>Use this app to verify GPS coordinates.</p>
                <p><b>📸 PROOF:</b><br>Upload visual evidence to unlock clues.</p>
            </div>
            <br>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Accept Mission"):
        st.session_state.stage = 1
        st.rerun()

# =========================================================
# STAGES 1-6: THE MAP INTERFACE
# =========================================================
elif 1 <= st.session_state.stage <= 6:
    idx = st.session_state.stage - 1
    target = STOPS[idx]

    # 1. MAP CARD (Top Half)
    # We define the map logic first so it sits at the top
    loc = get_geolocation(component_key='gps')
    user_lat, user_lon = None, None
    dist_miles = 999
    
    if loc and isinstance(loc, dict) and 'coords' in loc:
        user_lat = loc['coords']['latitude']
        user_lon = loc['coords']['longitude']
        dist_miles = get_dist_miles(user_lat, user_lon, target['lat'], target['lon'])
        
        # PyDeck Map
        view_state = pdk.ViewState(
            latitude=(user_lat + target['lat']) / 2,
            longitude=(user_lon + target['lon']) / 2,
            zoom=13,
            pitch=0
        )
        
        layer_line = pdk.Layer(
            "LineLayer",
            pd.DataFrame([{"s": [user_lon, user_lat], "t": [target['lon'], target['lat']]}]),
            get_source_position="s", get_target_position="t",
            get_color=[0, 122, 255], get_width=6
        )
        
        layer_scat = pdk.Layer(
            "ScatterplotLayer",
            pd.DataFrame([
                {"pos": [user_lon, user_lat], "c": [0, 122, 255], "r": 150}, # User Blue
                {"pos": [target['lon'], target['lat']], "c": [255, 59, 48], "r": 150} # Target Red
            ]),
            get_position="pos", get_color="c", get_radius="r"
        )
        
        st.pydeck_chart(pdk.Deck(
            layers=[layer_line, layer_scat], 
            initial_view_state=view_state, 
            map_style="mapbox://styles/mapbox/light-v10",
            height=350
        ))
    else:
        # Placeholder map if no GPS yet
        st.pydeck_chart(pdk.Deck(
            initial_view_state=pdk.ViewState(latitude=41.8781, longitude=-87.6298, zoom=10),
            map_style="mapbox://styles/mapbox/light-v10",
            height=350
        ))

    # 2. ACTION CARD (Bottom Half - Bottom Sheet Style)
    st.markdown(f"""
        <div class="ios-card">
            <h2>📍 Target #{st.session_state.stage}</h2>
            <h1>{target['name']}</h1>
            <p style="text-align: center; color: #8e8e93;">{target['task']}</p>
        </div>
    """, unsafe_allow_html=True)
    
    # 3. CONTROLS
    col1, col2 = st.columns([1, 1])
    
    # Check Location Button
    if st.button("📍 Check GPS"):
        if not loc:
            st.error("⚠️ Enable GPS!")
        elif not user_lat:
            st.warning("📡 Acquiring signal...")
        else:
            if dist_miles < st.session_state.radius_miles:
                st.session_state.can_take_photo = True
                st.balloons()
            else:
                st.toast(f"Too far! {dist_miles:.2f} mi away.")

    # 4. CAMERA DRAWER
    if st.session_state.can_take_photo:
        st.markdown("---")
        st.success(f"✅ Arrived! ({dist_miles:.2f} mi)")
        photo = st.camera_input("Take Proof Photo", key=f"cam_{st.session_state.stage}")
        
        if photo:
            with st.spinner("Verifying biometrics..."):
                time.sleep(2)
                if random.random() > 0.3:
                    st.balloons()
                    st.session_state.stage += 1
                    st.session_state.can_take_photo = False
                    st.rerun()
                else:
                    st.error("⚠️ Too blurry! Try again with a smile.")

# =========================================================
# STAGE 7: THE REVEAL
# =========================================================
elif st.session_state.stage == 7:
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("""
        <div class="ios-card" style="text-align: center; padding: 50px 20px;">
            <p style="font-weight: 600; color: #8e8e93; margin-bottom: 30px;">DECODING COMPLETE...</p>
            <div style="font-size: 60px; font-weight: 800; color: #1c1c1e; letter-spacing: 5px;">
                uNfO<span class="flip-text">r</span>D
            </div>
            <br><br>
            <p style="font-size: 20px;">Instruction Received:</p>
            <h2 style="color: #007AFF !important;">CHECK YOUR POCKET</h2>
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("🎉 I said YES!"):
        st.balloons()
        st.session_state.stage = 8
        st.rerun()

# =========================================================
# STAGE 8: SUCCESS
# =========================================================
elif st.session_state.stage == 8:
    st.balloons()
    st.markdown("""
        <div class="briefing-card">
            <div style="font-size: 80px;">💑</div>
            <h1 style="color: #34C759;">MISSION ACCOMPLISHED</h1>
            <p>Status: <b>Official Couple</b></p>
            <hr>
            <p>Next Steps:</p>
            <p>1. Kiss the Developer 😘<br>2. Watch Fireworks 🎆</p>
        </div>
    """, unsafe_allow_html=True)

# =========================================================
# ADMIN OVERRIDE (Hidden at bottom)
# =========================================================
st.markdown("<br><br>", unsafe_allow_html=True)
with st.expander("🛠️"):
    st.session_state.radius_miles = st.slider("GPS Radius (mi)", 0.1, 15.0, 0.25)
    target_stage = st.selectbox("Jump to", range(9))
    if st.button("Teleport"):
        st.session_state.stage = target_stage
        st.session_state.can_take_photo = False
        st.rerun()
    if st.button("Force Camera"):
        st.session_state.can_take_photo = True
        st.rerun()
