import streamlit as st
from streamlit_js_eval import get_geolocation
import pandas as pd
import pydeck as pdk
import math
import time
import random

# ---------------------------------------------------------
# 1. CONFIGURATION & CLEAN STYLING
# ---------------------------------------------------------
st.set_page_config(page_title="Valentine's Mission", page_icon="📍")

st.markdown("""
    <style>
    /* 1. Global Reset */
    .stApp {
        background-color: #F2F2F7; /* iOS Light Gray Background */
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* 2. Hide Streamlit Branding */
    header {visibility: hidden;}
    footer {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    
    /* 3. Card Styling (Solid White, Good Shadow) */
    .css-card {
        background-color: #FFFFFF;
        border-radius: 18px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
    }
    
    /* 4. Typography */
    h1 {
        color: #FF2E63 !important;
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 800;
        font-size: 28px !important;
        text-align: center;
        margin-bottom: 5px;
    }
    
    h2 {
        color: #1C1C1E !important;
        font-weight: 700;
        font-size: 22px !important;
        margin-top: 0;
    }
    
    p, li {
        color: #3A3A3C !important;
        font-size: 17px;
        line-height: 1.5;
    }

    /* 5. Letter Pills (Flexbox to prevent cutoff) */
    .letter-container {
        display: flex;
        justify-content: center;
        flex-wrap: wrap;
        gap: 10px;
        margin-bottom: 20px;
    }
    
    .letter-box {
        width: 45px;
        height: 50px;
        background: #FFFFFF;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 800;
        font-size: 24px;
        color: #FF2E63;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border: 2px solid #FF2E63;
    }
    
    .letter-box.locked {
        background: #E5E5EA;
        color: #AEAEB2;
        border: 2px solid #E5E5EA;
    }

    /* 6. Big Buttons */
    .stButton > button {
        width: 100%;
        background-color: #FF2E63;
        color: white;
        border-radius: 14px;
        height: 55px;
        font-size: 18px;
        font-weight: 600;
        border: none;
    }
    
    /* 7. Success Banner */
    .success-banner {
        background-color: #34C759;
        color: white;
        padding: 15px;
        border-radius: 12px;
        text-align: center;
        font-weight: bold;
        margin-bottom: 15px;
    }
    
    /* 8. Flip Animation */
    .flip-text {
        display: inline-block;
        animation: flip 2s forwards 0.5s;
    }
    @keyframes flip {
        0% { transform: rotateX(0deg); }
        100% { transform: rotateX(180deg) translateY(-3px); }
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

# --- HEADER (Letters) ---
# Show letters only during the game
if 0 < st.session_state.stage < 8:
    html_pills = '<div class="letter-container">'
    for i in range(6):
        if i < (st.session_state.stage - 1):
            html_pills += f'<div class="letter-box">{STOPS[i]["letter"]}</div>'
        else:
            html_pills += '<div class="letter-box locked">?</div>'
    html_pills += '</div>'
    st.markdown(html_pills, unsafe_allow_html=True)

# =========================================================
# STAGE 0: BRIEFING
# =========================================================
if st.session_state.stage == 0:
    st.markdown("""
        <div class="css-card" style="text-align: center;">
            <div style="font-size: 50px; margin-bottom: 10px;">💌</div>
            <h1>MISSION PROTOCOL</h1>
            <p style="color: #8E8E93 !important;">Chicago, IL • Feb 14</p>
            <hr style="border-top: 1px solid #E5E5EA;">
            <div style="text-align: left; margin-top: 20px;">
                <p><b>🎯 OBJECTIVE</b><br>Navigate to 6 locations.</p>
                <p><b>📡 TOOLS</b><br>Use this app to verify GPS.</p>
                <p><b>📸 PROOF</b><br>Upload photos to unlock clues.</p>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("Start Mission"):
        st.session_state.stage = 1
        st.rerun()

# =========================================================
# STAGES 1-6: THE HUNT
# =========================================================
elif 1 <= st.session_state.stage <= 6:
    idx = st.session_state.stage - 1
    target = STOPS[idx]

    # 1. MAP SECTION (Clean & Simple)
    loc = get_geolocation(component_key='gps')
    user_lat, user_lon = None, None
    dist_miles = 999
    
    if loc and isinstance(loc, dict) and 'coords' in loc:
        user_lat = loc['coords']['latitude']
        user_lon = loc['coords']['longitude']
        dist_miles = get_dist_miles(user_lat, user_lon, target['lat'], target['lon'])
        
        # Simple Map
        view_state = pdk.ViewState(
            latitude=(user_lat + target['lat']) / 2,
            longitude=(user_lon + target['lon']) / 2,
            zoom=12,
            pitch=0
        )
        
        layer_line = pdk.Layer(
            "LineLayer",
            pd.DataFrame([{"s": [user_lon, user_lat], "t": [target['lon'], target['lat']]}]),
            get_source_position="s", get_target_position="t",
            get_color=[0, 122, 255], get_width=5
        )
        
        layer_scat = pdk.Layer(
            "ScatterplotLayer",
            pd.DataFrame([
                {"pos": [user_lon, user_lat], "c": [0, 122, 255], "r": 200}, # Blue User
                {"pos": [target['lon'], target['lat']], "c": [255, 46, 99], "r": 200} # Red Target
            ]),
            get_position="pos", get_color="c", get_radius="r"
        )
        
        st.pydeck_chart(pdk.Deck(
            layers=[layer_line, layer_scat], 
            initial_view_state=view_state, 
            map_style="mapbox://styles/mapbox/light-v10",
            height=300
        ))
    else:
        st.info("📡 Waiting for GPS signal...")

    # 2. INFO CARD
    st.markdown(f"""
        <div class="css-card">
            <p style="text-align: center; color: #8E8E93 !important; font-size: 14px; text-transform: uppercase; letter-spacing: 1px;">Target #{st.session_state.stage}</p>
            <h2>{target['name']}</h2>
            <hr style="border-top: 1px solid #E5E5EA;">
            <p style="text-align: center; font-weight: 500;">{target['task']}</p>
        </div>
    """, unsafe_allow_html=True)

    # 3. ACTIONS
    if st.button("📍 Verify Location"):
        if not loc:
            st.error("Please enable GPS!")
        elif not user_lat:
            st.warning("Acquiring signal...")
        else:
            if dist_miles < st.session_state.radius_miles:
                st.session_state.can_take_photo = True
                st.balloons()
            else:
                st.error(f"Too far! {dist_miles:.2f} miles away.")

    # 4. CAMERA UNLOCK
    if st.session_state.can_take_photo:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f'<div class="success-banner">✅ ARRIVED! ({dist_miles:.2f} mi)</div>', unsafe_allow_html=True)
        
        photo = st.camera_input("Take Photo", key=f"cam_{st.session_state.stage}")
        
        if photo:
            with st.spinner("Uploading proof..."):
                time.sleep(1.5)
                if random.random() > 0.3:
                    st.balloons()
                    st.session_state.stage += 1
                    st.session_state.can_take_photo = False
                    st.rerun()
                else:
                    st.error("⚠️ Too blurry! Smile harder.")

# =========================================================
# STAGE 7: REVEAL
# =========================================================
elif st.session_state.stage == 7:
    st.markdown("""
        <div class="css-card" style="text-align: center; padding: 60px 20px;">
            <p style="color: #8E8E93 !important;">DECODING COMPLETE</p>
            <div style="font-size: 55px; font-weight: 800; color: #FF2E63; letter-spacing: 4px;">
                uNfO<span class="flip-text">r</span>D
            </div>
            <br><br>
            <h2>CHECK YOUR POCKET</h2>
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
    st.markdown("""
        <div class="css-card" style="text-align: center;">
            <div style="font-size: 80px;">💑</div>
            <h1 style="color: #34C759 !important;">MISSION SUCCESS</h1>
            <p>Status: <b>Official</b></p>
        </div>
    """, unsafe_allow_html=True)
    st.balloons()

# =========================================================
# ADMIN (Hidden)
# =========================================================
st.markdown("<br><br>", unsafe_allow_html=True)
with st.expander("🛠️"):
    st.session_state.radius_miles = st.slider("Radius (mi)", 0.1, 15.0, 0.25)
    target_stage = st.selectbox("Jump", range(9))
    if st.button("Teleport"):
        st.session_state.stage = target_stage
        st.session_state.can_take_photo = False
        st.rerun()
    if st.button("Force Camera"):
        st.session_state.can_take_photo = True
        st.rerun()
