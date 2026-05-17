import streamlit as st
import pandas as pd
import os
from urllib.parse import quote

# Database File
DATA_FILE = "butcher_dispatch_v2.csv"

# Available Time Slots across Karachi
TIME_SLOTS = [
    "06:30 AM - 08:30 AM (Early Morning / After Namaz)",
    "08:30 AM - 10:30 AM (Morning Peak)",
    "10:30 AM - 12:30 PM (Late Morning)",
    "12:30 PM - 02:30 PM (Mid-Day/Zohr)",
    "02:30 PM - 04:30 PM (Afternoon)",
    "04:30 PM - 06:30 PM (Evening/Asr)"
]

def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    return pd.DataFrame(columns=["ID", "Customer", "Phone", "Area", "Address", "Maps_Link", "Animal", "Day", "Time_Slot", "Team", "Phone_Team", "Status"])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

st.set_page_config(page_title="Eid Butcher Control Center", layout="wide")
st.title("🥩 Eid-ul-Adha Booking & Dispatch Board (With Time-Slots)")

orders_df = load_data()

# --- SIDEBAR: BOOKING ENGINE WITH AUTOMATIC TIME-SLOT CHECKING ---
st.sidebar.header("📝 Book New Order")

# 1. Quick selection for Day and Team first to check available slots
col_sidebar_1, col_sidebar_2 = st.sidebar.columns(2)
with col_sidebar_1:
    eid_day = st.selectbox("Eid Day", ["Day 1", "Day 2", "Day 3"])
with col_sidebar_2:
    assigned_team = st.radio("Assign To:", ["Team Alpha (Naseer)", "Team Beta (Aslam)"])

# Find which slots are ALREADY taken by this specific team on this specific day
taken_slots = []
if not orders_df.empty:
    taken_slots = orders_df[
        (orders_df['Day'] == eid_day) & 
        (orders_df['Team'] == assigned_team) & 
        (orders_df['Status'] != 'Cancelled')
    ]['Time_Slot'].tolist()

with st.sidebar.form("booking_form", clear_on_submit=True):
    cust_name = st.text_input("Customer Name")
    cust_phone = st.text_input("Customer Contact (WhatsApp)")
    cust_area = st.selectbox("Karachi Area", ["DHA / Clifton", "Gulshan / Johar", "Nazimabad / FB Area", "PECHS / Saddar", "Malir / Cantt", "Scheme 33", "Other"])
    exact_address = st.text_area("Exact House/Street Address")
    maps_link = st.text_input("Google Maps Link (Optional)")
    animal = st.selectbox("Animal", ["Goat/Sheep", "Cow (Full)", "Cow (Hissa)", "Camel"])
    
    # Dynamic Time Slot Selection: Shows text label if slot is booked
    available_slots_options = []
    slot_mapping = {}
    for slot in TIME_SLOTS:
        if slot in taken_slots:
            display_text = f"❌ {slot} [ALREADY BOOKED]"
            is_available = False
        else:
            display_text = f"🟢 {slot}"
            is_available = True
        available_slots_options.append(display_text)
        slot_mapping[display_text] = (slot, is_available)
        
    selected_display_slot = st.selectbox("Available Time Slots", available_slots_options)
    actual_slot, slot_is_free = slot_mapping[selected_display_slot]
    
    # Configure Team WhatsApp Numbers
    team_phone = "923363087084" if "Alpha" in assigned_team else "923360848024"

    submitted = st.form_submit_button("Confirm & Save Booking")
    
    if submitted:
        if not slot_is_free:
            st.sidebar.error("This time slot is already booked for this team! Please choose another time or switch teams.")
        elif cust_name and exact_address:
            new_id = len(orders_df) + 1
            new_row = pd.DataFrame([{
                "ID": new_id, "Customer": cust_name, "Phone": cust_phone,
                "Area": cust_area, "Address": exact_address, "Maps_Link": maps_link,
                "Animal": animal, "Day": eid_day, "Time_Slot": actual_slot, 
                "Team": assigned_team, "Phone_Team": team_phone, "Status": "Pending"
            }])
            orders_df = pd.concat([orders_df, new_row], ignore_index=True)
            save_data(orders_df)
            st.sidebar.success(f"Order #{new_id} successfully locked for {actual_slot}!")
            st.rerun()
        else:
            st.sidebar.error("Name and Address are required fields!")

# --- MAIN BOARD: LIVE TIME SCHEDULES ---
st.subheader("📊 Live Dispatch Dashboard")

# Filter view by Day to see the sequence clearly
selected_day_filter = st.segmented_control("Filter View by Eid Day:", ["Day 1", "Day 2", "Day 3"], default="Day 1")

# Split view into Team columns
col_team_a, col_team_b = st.columns(2)

# Function to render a team schedule sorted chronologically by time slot
def render_team_column(team_name, df_source, color_tag):
    st.header(f"{color_tag} {team_name}")
    
    # Filter and sort according to the pre-defined sequence of TIME_SLOTS
    team_df = df_source[(df_source['Team'].str.contains(team_name.split()[1])) & (df_source['Day'] == selected_day_filter)]
    
    if team_df.empty:
        st.info(f"No bookings scheduled for {team_name} on {selected_day_filter}.")
    else:
        # Sort dataframe manually based on our TIME_SLOTS order
        team_df['slot_priority'] = team_df['Time_Slot'].apply(lambda x: TIME_SLOTS.index(x) if x in TIME_SLOTS else 99)
        team_df = team_df.sort_values(by='slot_priority')
        
        for idx, row in team_df.iterrows():
            with st.container(border=True):
                # Highlight time slot
                st.markdown(f"⏱️ **{row['Time_Slot']}**")
                st.write(f"**Order #{row['ID']}** | **Status:** `{row['Status']}`")
                st.write(f"👤 **{row['Customer']}** ({row['Phone']})")
                st.write(f"📍 **{row['Area']}:** {row['Address']}")
                st.write(f"🐄 **Animal:** {row['Animal']}")
                
                # Action Buttons
                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    maps_part = f"\n📍 *Location Pin:* {row['Maps_Link']}" if pd.notna(row['Maps_Link']) and row['Maps_Link'] != "" else ""
                    msg = f"*EID JOB ASSIGNMENT*\n\n*Day:* {row['Day']}\n*Time:* {row['Time_Slot']}\n\n*Customer:* {row['Customer']}\n*Phone:* {row['Phone']}\n*Area:* {row['Area']}\n*Address:* {row['Address']}{maps_part}\n*Animal:* {row['Animal']}\n\n_Please confirm when you depart for this location._"
                    wa_url = f"https://wa.me/{row['Phone_Team']}?text={quote(msg)}"
                    st.link_button("📲 WhatsApp Dispatch", wa_url, use_container_width=True)
                with btn_col2:
                    if row['Status'] != 'Completed':
                        if st.button("Mark Complete", key=f"comp_{row['ID']}", use_container_width=True):
                            orders_df.at[idx, 'Status'] = 'Completed'
                            save_data(orders_df)
                            st.rerun()
                    else:
                        st.success("✅ Finished")

# Render columns
with col_team_a:
    render_team_column("Team Alpha (Naseer)", orders_df, "🟢")

with col_team_b:
    render_team_column("Team Beta (Aslam)", orders_df, "🔵")

# --- DATA MAINTENANCE UTILITIES ---
st.divider()
col_util1, col_util2 = st.columns([4, 1])
with col_util2:
    if st.button("🚨 Reset Whole App Data", type="primary", use_container_width=True):
        if os.path.exists(DATA_FILE):
            os.remove(DATA_FILE)
            st.success("Database wiped clean!")
            st.rerun()