import streamlit as st
import pandas as pd
import os
import sqlite3
from datetime import datetime
import matplotlib.pyplot as plt
from streamlit_autorefresh import st_autorefresh
import urllib.parse
import hashlib

# ---------------- DB Setup ----------------
DB_FILE = "excavator_data.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS excavator_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            mobile TEXT,
            date TEXT,
            hours_worked REAL,
            cost_per_hour REAL,
            total_cost REAL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            mobile TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ---------------- AUTH HELPERS ----------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def signup(username, password, mobile):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password, mobile) VALUES (?, ?, ?)",
                       (username, hash_password(password), mobile))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def login(username, password):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, hash_password(password)))
    user = cursor.fetchone()
    conn.close()
    return user

def get_logged_user():
    return st.session_state.get("user")

# ---------------- DB Helpers ----------------
def load_data(user_id):
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM excavator_data WHERE user_id=?", conn, params=(user_id,))
    conn.close()
    return df

def save_data(df):
    conn = sqlite3.connect(DB_FILE)
    df.to_sql("excavator_data", conn, if_exists="replace", index=False)
    conn.close()

def add_user(username, mobile, user_id):
    df = load_data(user_id)
    if df.empty:
        new_id = 1
    else:
        new_id = int(df["user_id"].max()) + 1
    new_user = pd.DataFrame([[None, user_id, username, mobile, None, None, None, None]],
                            columns=["id", "user_id", "username", "mobile", "date", "hours_worked", "cost_per_hour", "total_cost"])
    df = pd.concat([df, new_user], ignore_index=True)
    save_data(df)

def add_work(user_id, date, hours, cost_per_hour):
    df = load_data(user_id)
    user_rows = df[df["user_id"] == user_id]
    if user_rows.empty:
        return
    username = user_rows["username"].iloc[0]
    mobile = user_rows["mobile"].iloc[0]
    cost = hours * cost_per_hour
    new_entry = pd.DataFrame([[None, user_id, username, mobile, date, hours, cost_per_hour, cost]],
                             columns=["id", "user_id", "username", "mobile", "date", "hours_worked", "cost_per_hour", "total_cost"])
    df = pd.concat([df, new_entry], ignore_index=True)
    save_data(df)

def delete_entry_by_index(df_index, user_id):
    df = load_data(user_id)
    if df_index in df.index:
        df = df.drop(df_index)
        df = df.reset_index(drop=True)
        save_data(df)

def delete_user(user_id):
    """Delete all records for a particular user_id"""
    df = load_data(user_id)
    df = df[df["user_id"] != user_id]
    df = df.reset_index(drop=True)
    save_data(df)

# ---------------- AUTO REFRESH ----------------
st_autorefresh(interval=5000, limit=None, key="refresh")

# ---------------- AUTH SYSTEM ----------------
if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    st.set_page_config(page_title="Excavator Billing Management", layout="wide")
    st.title("🚜 Excavator Billing Management System")

    auth_choice = st.radio("Login / Signup", ["Login", "Signup"])

    if auth_choice == "Signup":
        new_username = st.text_input("Choose a username")
        new_password = st.text_input("Choose a password", type="password")
        new_mobile = st.text_input("Enter mobile number")
        if st.button("Signup"):
            if new_username and new_password and new_mobile:
                if signup(new_username, new_password, new_mobile):
                    st.success("Signup successful! Please login.")
                else:
                    st.error("Username already exists. Try another.")
            else:
                st.error("Please fill all fields.")
    else:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            user = login(username, password)
            if user:
                st.session_state.user = {"id": user[0], "username": user[1], "mobile": user[3]}
                st.success(f"Welcome {user[1]}!")
                st.rerun()
            else:
                st.error("Invalid username or password.")
else:
    # ---------------- MAIN APP ----------------
    st.set_page_config(page_title="Excavator Billing Management", layout="wide")
    st.title("🚜 Excavator Billing Management System")

    st.sidebar.write(f"👤 Logged in as {st.session_state.user['username']}")
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.rerun()

    tab1, tab2 = st.tabs(["📋 Users & Billing", "📊 Analysis"])

    # ---------------- TAB 1 ----------------
    with tab1:
        st.header("User Management & Billing")

        df = load_data(st.session_state.user["id"])

        if not df.empty:
            df = df.reset_index(drop=False)
            users = df["username"].dropna().unique()

            for i, user in enumerate(users):
                user_df = df[df["username"] == user]
                mobile_display = user_df["mobile"].dropna().iloc[0] if not user_df["mobile"].dropna().empty else ""

                with st.expander(f"👤 {user} ({mobile_display})"):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.subheader("Details")

                        if not user_df.empty:
                            for _, row in user_df.iterrows():
                                df_index = int(row["index"])
                                if pd.isna(row["date"]):
                                    continue
                                st.write(
                                    f"📅 {row['date']} | ⏱ {row['hours_worked']} hrs | 💰 ₹{row['total_cost']} (₹{row['cost_per_hour']}/hr)"
                                )
                                btn_key = f"del_{df_index}"
                                if st.button("❌ Delete", key=btn_key):
                                    delete_entry_by_index(df_index, st.session_state.user["id"])
                                    st.success("Entry deleted successfully!")
                                    st.rerun()

                        send_key = f"send_{i}"
                        if st.button("📤 Send Bill", key=send_key):
                            total_cost = user_df["total_cost"].dropna().sum()
                            message = f"Hello {user}, your total bill is ₹{total_cost}. Thank you!"
                            encoded_message = urllib.parse.quote(message)
                            mobile = str(mobile_display)
                            whatsapp_url = f"https://wa.me/{mobile}?text={encoded_message}"
                            st.markdown(f"[Click here to send via WhatsApp]({whatsapp_url})", unsafe_allow_html=True)

                        # ✅ Delete User button
                        del_user_key = f"delete_user_{i}"
                        if st.button(f"🗑️ Delete User {user}", key=del_user_key):
                            user_id = int(user_df["user_id"].iloc[0])
                            delete_user(user_id)
                            st.success(f"User '{user}' and all their records deleted!")
                            st.rerun()

                    with col2:
                        st.subheader("Add Work Entry")
                        hours = st.number_input(f"Hours worked for {user}", min_value=1, step=1, key=f"hours_{i}")
                        cost_per_hour = st.number_input(f"Cost per Hour for {user}", min_value=1, step=1, key=f"cost_{i}")
                        date = st.date_input(f"Date for {user}", datetime.today(), key=f"date_{i}")
                        add_key = f"add_{i}"
                        if st.button(f"Add Entry for {user}", key=add_key):
                            user_id = int(user_df["user_id"].iloc[0])
                            add_work(user_id, str(date), hours, cost_per_hour)
                            st.success(f"Added {hours} hours for {user} on {date} at ₹{cost_per_hour}/hr")
                            st.rerun()

        st.markdown("---")
        st.subheader("➕ Add New User")
        new_username = st.text_input("Enter new user's name")
        new_mobile = st.text_input("Enter mobile number (with country code, e.g., 91XXXXXXXXXX)")
        if st.button("Add User"):
            if new_username.strip() and new_mobile.strip():
                add_user(new_username.strip(), new_mobile.strip(), st.session_state.user["id"])
                st.success(f"User '{new_username}' added successfully!")
                st.rerun()
            else:
                st.error("Please enter a valid username and mobile number")

    # ---------------- TAB 2 ----------------
    with tab2:
        st.header("📊 Analysis")

        df = load_data(st.session_state.user["id"])
        if df.empty or df["hours_worked"].dropna().sum() == 0:
            st.warning("No data available for analysis.")
        else:
            users = df["username"].dropna().unique()
            selected_user = st.selectbox("Select User", users)

            user_entries = df[(df["username"] == selected_user) & df["hours_worked"].notna()]

            if not user_entries.empty:
                user_entries_sorted = user_entries.copy()
                user_entries_sorted["date"] = pd.to_datetime(user_entries_sorted["date"], errors="coerce")
                user_entries_sorted = user_entries_sorted.dropna(subset=["date"])

                if not user_entries_sorted.empty:
                    st.subheader(f"📈 Work Analysis for {selected_user}")

                    fig, ax = plt.subplots()
                    ax.plot(user_entries_sorted["date"], user_entries_sorted["hours_worked"], marker="o")
                    ax.set_xlabel("Date")
                    ax.set_ylabel("Hours Worked")
                    ax.set_title(f"Hours Worked Over Time - {selected_user}")
                    st.pyplot(fig)

                    total_cost = user_entries_sorted["total_cost"].sum()
                    st.metric("💰 Total Billing", f"₹{total_cost}")
                else:
                    st.info("No valid date entries found for this user.")
