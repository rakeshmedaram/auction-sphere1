import streamlit as st
import sqlite3
import hashlib
from datetime import datetime, timedelta
import os
from streamlit_autorefresh import st_autorefresh

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Auction Sphere", layout="wide")
st_autorefresh(interval=4000, key="refresh")

# ---------------- IMAGE FOLDER ----------------
if not os.path.exists("images"):
    os.makedirs("images")

# ---------------- DB ----------------
conn = sqlite3.connect("auction.db", check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS users (
id INTEGER PRIMARY KEY, username TEXT, email TEXT, password TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS auctions (
id INTEGER PRIMARY KEY, title TEXT, description TEXT,
base_price REAL, end_time TEXT, created_by TEXT, image TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS bids (
id INTEGER PRIMARY KEY, auction_id INTEGER,
bidder TEXT, amount REAL)''')

conn.commit()

# ---------------- FUNCTIONS ----------------
def hash_password(p):
    return hashlib.sha256(p.strip().encode()).hexdigest()

def register(u, e, p):
    try:
        u = u.strip()
        e = e.strip()
        p = p.strip()

        c.execute("INSERT INTO users VALUES(NULL,?,?,?)",
                  (u, e, hash_password(p)))
        conn.commit()
        return True
    except:
        return False

def login(e, p):
    e = e.strip()
    p = p.strip()

    c.execute("SELECT * FROM users WHERE email=?", (e,))
    user = c.fetchone()

    if user and user[3] == hash_password(p):
        return user
    return None

def create_auction(t, d, b, dur, u, img):
    end = datetime.now() + timedelta(minutes=int(dur))
    path = ""

    if img:
        path = f"images/{img.name}"
        with open(path, "wb") as f:
            f.write(img.getbuffer())

    c.execute("INSERT INTO auctions VALUES(NULL,?,?,?,?,?,?)",
              (t.strip(), d.strip(), b,
               end.strftime("%Y-%m-%d %H:%M:%S"), u, path))
    conn.commit()

def place_bid(a, u, amt):
    c.execute("INSERT INTO bids VALUES(NULL,?,?,?)", (a, u, amt))
    conn.commit()

def highest(a):
    c.execute("SELECT MAX(amount) FROM bids WHERE auction_id=?", (a,))
    r = c.fetchone()[0]
    return r if r else 0

def bids_history(a):
    c.execute("SELECT bidder,amount FROM bids WHERE auction_id=? ORDER BY amount DESC", (a,))
    return c.fetchall()

# ---------------- SESSION ----------------
if "user" not in st.session_state:
    st.session_state.user = None

# ---------------- NAV ----------------
if st.session_state.user:
    tabs = st.tabs(["🏠 Home", "➕ Create", "📊 Dashboard", "🚪 Logout"])
else:
    tabs = st.tabs(["🔐 Login", "📝 Register"])

# ---------------- LOGIN ----------------
if not st.session_state.user:
    with tabs[0]:
        st.title("🔐 Login")

        e = st.text_input("Email", key="login_email").strip()
        p = st.text_input("Password", type="password", key="login_pass").strip()

        if st.button("Login", key="login_btn"):
            user = login(e, p)
            if user:
                st.session_state.user = user[1]
                st.success("Login successful")
                st.rerun()
            else:
                st.error("Invalid credentials")

# ---------------- REGISTER ----------------
    with tabs[1]:
        st.title("📝 Register")

        u = st.text_input("Username", key="reg_user").strip()
        e = st.text_input("Email", key="reg_email").strip()
        p = st.text_input("Password", type="password", key="reg_pass").strip()

        if st.button("Register", key="reg_btn"):
            if u and e and p:
                if register(u, e, p):
                    st.success("Account created successfully")
                else:
                    st.error("Email already exists")
            else:
                st.warning("Fill all fields")

# ---------------- HOME ----------------
if st.session_state.user:
    with tabs[0]:
        st.title("🔥 Auction Marketplace")

        col1, col2, col3 = st.columns(3)
        c.execute("SELECT COUNT(*) FROM auctions")
        col1.metric("Auctions", c.fetchone()[0])

        c.execute("SELECT COUNT(*) FROM bids")
        col2.metric("Total Bids", c.fetchone()[0])

        col3.metric("User", st.session_state.user)

        search = st.text_input("🔍 Search Auctions", key="search")

        c.execute("SELECT * FROM auctions")
        data = c.fetchall()

        cols = st.columns(3)

        for i, a in enumerate(data):
            aid, title, desc, base, end, creator, img = a

            if search.lower() not in title.lower():
                continue

            with cols[i % 3]:
                st.markdown("### " + title)

                if img and os.path.exists(img):
                    st.image(img, use_container_width=True)

                st.write(desc)

                h = highest(aid)
                st.success(f"💰 ₹{h}")

                end_dt = datetime.strptime(end, "%Y-%m-%d %H:%M:%S")
                rem = end_dt - datetime.now()

                if rem.total_seconds() > 0:
                    st.warning(f"⏳ {str(rem).split('.')[0]}")

                    bid_val = st.number_input("Your Bid", min_value=float(base),
                                              key=f"bid_{aid}")

                    if st.button("Place Bid", key=f"btn_{aid}"):
                        if bid_val > h:
                            place_bid(aid, st.session_state.user, bid_val)
                            st.success("Bid placed")
                            st.rerun()
                        else:
                            st.error("Bid too low")

                    with st.expander("📜 Bid History"):
                        for bh in bids_history(aid):
                            st.write(f"{bh[0]} → ₹{bh[1]}")

                else:
                    st.error("Auction Ended")
                    w = bids_history(aid)
                    if w:
                        st.success(f"🏆 Winner: {w[0][0]} ₹{w[0][1]}")

# ---------------- CREATE ----------------
    with tabs[1]:
        st.title("➕ Create Auction")

        t = st.text_input("Title", key="create_title")
        d = st.text_area("Description", key="create_desc")
        b = st.number_input("Base Price", min_value=1.0, key="create_price")
        dur = st.number_input("Duration (minutes)", min_value=1, key="create_duration")
        img = st.file_uploader("Upload Image", key="create_img")

        if st.button("Create Auction", key="create_btn"):
            if t and d:
                create_auction(t, d, b, dur, st.session_state.user, img)
                st.success("Auction created!")
            else:
                st.warning("Fill all fields")

# ---------------- DASHBOARD ----------------
    with tabs[2]:
        st.title("📊 My Dashboard")

        c.execute("SELECT COUNT(*) FROM auctions WHERE created_by=?",
                  (st.session_state.user,))
        st.metric("My Auctions", c.fetchone()[0])

        c.execute("SELECT COUNT(*) FROM bids WHERE bidder=?",
                  (st.session_state.user,))
        st.metric("My Bids", c.fetchone()[0])

# ---------------- LOGOUT ----------------
    with tabs[3]:
        if st.button("Logout", key="logout_btn"):
            st.session_state.user = None
            st.rerun()