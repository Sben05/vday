import streamlit as st
from streamlit_js_eval import get_geolocation
import pandas as pd
import pydeck as pdk
import math
import time
import random

# ---------------------------------------------------------
# 1. CONFIGURATION & ROMANTIC STYLING
# ---------------------------------------------------------
st.set_page_config(page_title="Valentine's Mission", page_icon="💖")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Fredoka+One&family=Pacifico&family=Quicksand:wght@500&display=swap');

    /* Background & Hearts */
    .stApp {
        background: linear-gradient(135deg, #fff0f5 0%, #ffe6e9 100%);
    }
    
    /* Typography */
    h1 {
        font-family: 'Pacifico', cursive;
        color: #e91e63;
        font-size: 2.5rem !important;
        text-align: center;
        text-shadow: 2px 2px 0px #fff;
    }
    
    h2 {
        font-family: 'Fredoka One', sans-serif;
        color: #d81b60;
        text-align: center;
    }
    
    h3, .mission-header {
        font-family: 'Fredoka One', sans-serif;
        color: #880e4f;
        text-align: center;
    }
    
    p, .status-text {
        font-family: 'Quicksand', sans-serif;
        font-size: 18px;
        color: #555;
        text-align: center;
    }

    /* The "Collected Letters" Box */
    .mystery-box {
        background: rgba(255, 255, 255, 0.95);
        padding: 15px;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(233, 30, 99, 0.15);
        text-align: center;
        margin-bottom: 20px;
        border: 2px dashed #f8bbd0;
    }
    
    .letter-slot {
        font-family: 'Fredoka One', sans-serif;
        font-size: 32px;
        color: #c2185b;
        margin: 0 8px;
        display: inline-block;
        width: 40px;
        border-bottom: 3px solid #ff4081;
    }

    /* The "Flip" Animation for Finale */
    .flip-r {
        display: inline-block;
        animation: flip-vertical 2s forwards 1s; /* Delay start by 1s */
    }
    @keyframes flip-vertical {
        0% { transform: rotateX(0deg); color: #c2185b; }
        100% { transform: rotateX(180deg) translateY(-4px); color: #d81b60; } 
    }
    
    /* Button Styling */
    .stButton>button {
        background: linear-gradient(45deg, #ff4081, #f50057);
        color: white;
        border-radius: 25px;
        font-weight: bold;
        border: none;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        height: 50px;
        width: 100%;
        font-size: 18px;
    }

    /* Success Screen */
    .success-card {
        background: white;
        padding: 30px;
        border-radius: 20px;
        text-align: center;
        box-shadow: 0 10px 30px rgba(233, 30, 99, 0.3);
        animation: popIn 0.5s;
    }
    @keyframes popIn {
        0% { transform: scale(0.8); opacity: 0; }
        100% { transform: scale(1); opacity: 1; }
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. STATE MANAGEMENT & DATA
# ---------------------------------------------------------

if 'stage' not in st.session_state:
    st.session_state.stage = 0

if 'radius_miles' not in st.session_state:
    st.session_state.radius_miles = 0.25

if 'can_take_photo' not in st.session_state:
    st.session_state.can_take_photo = False

# MIXED CASE LETTERS: u - N - f - O - r - D
STOPS = [
    {"name": "Start: Davis St", "lat": 42.0451, "lon": -87.6877, "letter": "u", "task": "Take a selfie on the platform!"},
    {"name": "The Conservatory", "lat": 41.9245, "lon": -87.6348, "letter": "N", "task": "Find a flower matching your outfit."},
    {"name": "Royal Palms", "lat": 41.9105, "lon": -87.6775, "letter": "f", "task": "Capture the shuffleboard vibes."},
    {"name": "Wicker Park", "lat": 41.9088, "lon": -87.6770, "letter": "O", "task": "Find something vintage."},
    {"name": "QXY Dumplings", "lat": 41.8527, "lon": -87.6322, "letter": "r", "task": "Snap the dumplings!"}, # The Lowercase r
    {"name": "Navy Pier", "lat": 41.8917, "lon": -87.6043, "letter": "D", "task": "Get the skyline background."}
]

def get_dist_miles(lat1, lon1, lat2, lon2):
    dlat = (lat2 - lat1) * 69.0
    dlon = (lon2 - lon1) * 52.0
    return math.sqrt(dlat**2 + dlon**2)

# ---------------------------------------------------------
# 3. MAIN UI
# ---------------------------------------------------------

st.markdown("<h1>💖 Valentine's Protocol 💖</h1>", unsafe_allow_html=True)

# A. SHOW COLLECTED LETTERS
# Only show letters if we are in the HUNT phases (Stage 1-7)
if 0 < st.session_state.stage < 8:
    display_html = '<div class="mystery-box">'
    for i in range(6):
        # We offset by 1 because Stage 0 is instructions
        if i < (st.session_state.stage - 1):
            display_html += f'<span class="letter-slot">{STOPS[i]["letter"]}</span>'
        else:
            display_html += '<span class="letter-slot" style="color:#ccc">?</span>'
    display_html += '</div>'
    st.markdown(display_html, unsafe_allow_html=True)


# =========================================================
# STAGE 0: BRIEFING / INSTRUCTIONS
# =========================================================
if st.session_state.stage == 0:
    st.markdown("""
        <div class="success-card">
            <h2>🕵️‍♀️ MISSION BRIEFING</h2>
            <p>
                Welcome, Agent. 
                <br><br>
                Today is not a normal day. It is a <b>City-Wide Scavenger Hunt</b>.
                <br><br>
                <b>THE OBJECTIVE:</b><br>
                Travel to 6 specific locations across Chicago.
                <br><br>
                <b>THE RULES:</b><br>
                1. Navigate to the Target Location.<br>
                2. Use this app to verify your GPS coordinates.<br>
                3. Upload photographic evidence to unlock a <b>Secret Clue</b>.<br>
                <br>
                Collect all 6 clues to decode the Final Message.
            </p>
            <br>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("🚀 INITIALIZE MISSION"):
        st.session_state.stage = 1
        st.rerun()


# =========================================================
# STAGES 1-6: THE HUNT
# =========================================================
elif 1 <= st.session_state.stage <= 6:
    # Offset Index by -1 because Stage 1 maps to STOP[0]
    current_stop_idx = st.session_state.stage - 1
    target = STOPS[current_stop_idx]
    
    st.write(f"### 📍 TARGET #{st.session_state.stage}: {target['name']}")
    st.markdown(f"<p class='status-text'>Task: {target['task']}</p>", unsafe_allow_html=True)
    
    # ------------------------------------------------
    # 1. THE "CHECK LOCATION" BUTTON
    # ------------------------------------------------
    
    loc = get_geolocation(component_key='gps')
    user_lat, user_lon = None, None
    dist_miles = 999
    
    if loc:
        user_lat = loc['coords']['latitude']
        user_lon = loc['coords']['longitude']
        dist_miles = get_dist_miles(user_lat, user_lon, target['lat'], target['lon'])
        
        # MAP VISUALIZATION
        line_data = pd.DataFrame([{ "source": [user_lon, user_lat], "target": [target['lon'], target['lat']] }])
        scat_data = pd.DataFrame([
            {"lon": user_lon, "lat": user_lat, "color": [0, 0, 255, 200], "size": 100}, 
            {"lon": target['lon'], "lat": target['lat'], "color": [255, 0, 0, 200], "size": 100} 
        ])

        layer_line = pdk.Layer("LineLayer", line_data, get_source_position="source", get_target_position="target", get_color=[255, 0, 128], get_width=5)
        layer_scat = pdk.Layer("ScatterplotLayer", scat_data, get_position=["lon", "lat"], get_color="color", get_radius="size", pickable=True)
        
        mid_lat = (user_lat + target['lat']) / 2
        mid_lon = (user_lon + target['lon']) / 2
        zoom_level = 12 if dist_miles > 2 else 15

        view_state = pdk.ViewState(latitude=mid_lat, longitude=mid_lon, zoom=zoom_level, pitch=0)
        
        st.pydeck_chart(pdk.Deck(layers=[layer_line, layer_scat], initial_view_state=view_state, tooltip={"text": "Current Location"}))
    
    # THE CHECK BUTTON
    if st.button("📍 CHECK MY LOCATION"):
        if not loc:
            st.error("⚠️ GPS not found. Allow location access!")
        else:
            if dist_miles < st.session_state.radius_miles:
                st.session_state.can_take_photo = True # LOCK IT OPEN
                st.balloons()
            else:
                st.warning(f"🔭 Too far! Distance: {dist_miles:.2f} miles")
                st.caption(f"Needed: < {st.session_state.radius_miles} mi")

    # ------------------------------------------------
    # 2. CAMERA UNLOCK (Persistent State)
    # ------------------------------------------------
    
    if st.session_state.can_take_photo:
        st.success(f"✅ YOU ARE HERE! ({dist_miles:.2f} mi)")
        st.markdown("---")
        st.write("📸 **Proof Required**")
        
        photo = st.camera_input("Capture Evidence", key=f"cam_{st.session_state.stage}")
        
        if photo:
            progress_text = "Analyzing joy levels..."
            my_bar = st.progress(0, text=progress_text)
            
            for percent_complete in range(100):
                time.sleep(0.01)
                if percent_complete == 50: my_bar.progress(percent_complete + 1, text="Verifying hearts...")
                my_bar.progress(percent_complete + 1)
            
            # 30% Reject Chance
            if random.random() > 0.3:
                st.balloons()
                st.success("✨ MATCH CONFIRMED!")
                time.sleep(1)
                st.session_state.stage += 1
                st.session_state.can_take_photo = False # Reset for next stage
                st.rerun()
            else:
                st.error("⚠️ DETECTION ERROR: Not enough smiles.")
                st.caption("Try again!")


# =========================================================
# STAGE 7: THE REVEAL (Finale)
# =========================================================
elif st.session_state.stage == 7:
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("""
        <div style="text-align: center;">
            <span style="font-size: 60px; font-family: 'Fredoka One'; color: #c2185b;">
                u N f O <span class="flip-r">r</span> D
            </span>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
        <div style="text-align: center; margin-top: 30px; animation: fadeIn 3s;">
            <p style="font-family: 'Quicksand'; font-size: 20px;">
                Processing complete.<br>
                <b>Check your pocket.</b>
            </p>
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
        <div class="success-card">
            <h1 style="color: #4CAF50;">MISSION ACCOMPLISHED!</h1>
            <br>
            <p style="font-size: 24px; font-family: 'Fredoka One'; color: #333;">
                Relationship Status: <span style="color: #e91e63;">COUPLE</span> 💑
            </p>
            <hr>
            <p style="font-family: 'Quicksand'; font-size: 18px;">
                <b>Next Objectives:</b><br>
                1. Watch the Fireworks 🎆<br>
                2. Take a "First Photo" 📸<br>
                3. Live Happily Ever After ✨
            </p>
            <br>
            <p style="font-size: 14px; color: #888;">
                Developed with ❤️ by Your Boyfriend.
            </p>
        </div>
    """, unsafe_allow_html=True)


# =========================================================
# D. MANUAL ADMIN OVERRIDE
# =========================================================
st.markdown("<br><br><br>", unsafe_allow_html=True)
with st.expander("🛠️ Admin Console"): 
    st.write("Use this if GPS fails or to skip ahead.")
    
    st.session_state.radius_miles = st.slider(
        "GPS Tolerance (Miles)", 
        min_value=0.1, max_value=12.5, value=float(st.session_state.radius_miles), step=0.1
    )
    st.write(f"Requirement: < **{st.session_state.radius_miles} miles**")
    
    # Updated Selectbox for 0-8 stages
    target_stage = st.selectbox(
        "Jump to Stage:", 
        options=[0, 1, 2, 3, 4, 5, 6, 7, 8],
        format_func=lambda x: f"Stage {x}" if x < 7 else ("Finale" if x==7 else "Success")
    )
    
    if st.button("Teleport"):
        st.session_state.stage = target_stage
        st.session_state.can_take_photo = False
        st.rerun()
    
    if st.button("Force Unlock Camera"):
        st.session_state.can_take_photo = True
        st.rerun()
