import streamlit as st
import os
from dotenv import load_dotenv
from api import RailClient
load_dotenv()
radar_key =os.getenv("RAILRADAR_KEY")
rapid_key= os.getenv("RAPIDAPI_KEY")

st.set_page_config(page_title="RailTracker Pro", page_icon="🚆", layout="centered")

client = RailClient(radar_key=radar_key, rapid_key=rapid_key)

st.title("🇮🇳 Indian Rail Live Tracker")
st.caption("Real-time Tracking • PNR Status • Seat Availability")

tab1, tab2, tab3, tab4 = st.tabs(["📍 Live Status", "🎫 Check PNR", "💺 Seats", "📅 Schedule"])

with tab1:
    st.header("Track Your Train")
    train_no = st.text_input("Enter Train Number", placeholder="e.g. 12222")

    if st.button("Get Live Status", key="btn_live"):
        if train_no:
            with st.spinner("Contacting Satellite..."):
                train_obj = client.get_live_status(train_no)

            if train_obj:
                st.success("Train Found!")
                st.info(str(train_obj))

                col1, col2, col3 = st.columns(3)
                col1.metric("Current Station", train_obj.current_station)
                col2.metric("Delay", f"{train_obj.delay} mins")
                col3.metric("Type", train_obj.type)
            else:
                st.error("Train not found or API Error!")
        else:
            st.warning("Please enter a train number.")

with tab2:
    st.header("Check PNR Status")
    pnr_input = st.text_input("Enter 10-digit PNR", placeholder="8234567890")

    if st.button("Check PNR", key="btn_pnr"):
        with st.spinner("Fetching PNR Records..."):
            pnr_obj = client.get_pnr_status(pnr_input)

        if pnr_obj:
            st.success("PNR Record Found")
            st.write(str(pnr_obj))

            if pnr_obj.is_confirmed():
                st.balloons()
                st.success("✅ TICKET CONFIRMED")
            else:
                st.warning("⚠️ Ticket Not Confirmed")

with tab3:
    st.header("Check Seat Availability")
    col1, col2 = st.columns(2)
    with col1:
        s_train = st.text_input("Train No", key="seat_train")
        s_class = st.selectbox("Class", ["SL", "3A", "2A", "1A"])
    with col2:
        s_src = st.text_input("From Station", "HWH")
        s_dest = st.text_input("To Station", "NDLS")
        s_date = st.date_input("Date of Journey")

    if st.button("Check Seats", key="btn_seats"):
        seat_obj = client.get_seats(s_train, s_src, s_dest, s_date, s_class)
        if seat_obj:
            st.info(f"Checking for {s_class} on {s_date}...")
            st.success(str(seat_obj))

with tab4:
    st.header("Train Schedule")
    sch_train = st.text_input("Train No for Schedule")

    if st.button("Get Route", key="btn_sch"):
        sch_obj = client.get_schedule(sch_train)
        if sch_obj:
            st.write(f"**Route Summary:** {sch_obj.route_summary()}")
            st.write("---")
            st.write("🛑 **Stops:**")
            st.code(sch_obj.full_schedule())