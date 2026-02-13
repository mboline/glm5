import streamlit as st
import pandas as pd
import pymongo
import os

# --- DATABASE CONNECTION ---
def get_database():
    # 1. Try to get the URI from Streamlit Secrets (Web Environment)
    try:
        uri = st.secrets["MONGO_URI"]
    except:
        # 2. Fallback for local testing (checks your computer's environment variables)
        # You can also paste your string here temporarily for local testing, 
        # but don't commit it to GitHub.
        uri = os.environ.get("MONGO_URI", "") 

    if not uri:
        st.error("Database URI not found. Please set MONGO_URI in Streamlit Secrets.")
        st.stop()

    # Connect using the URI
    client = pymongo.MongoClient(uri)
    
    # Create/Switch to a NEW database specifically for this app
    # This ensures we don't mix data with your 'WordInfo' database
    return client["library_db"]

# --- HELPER FUNCTIONS ---
def load_data(collection):
    data = list(collection.find({}, {'_id': 0}))
    if not data:
        return pd.DataFrame(columns=["Title", "Author", "Purchased", "Read", "Rating", "Notes"])
    return pd.DataFrame(data)

def save_book(collection, book_data):
    collection.insert_one(book_data)

def delete_book(collection, title):
    collection.delete_one({"Title": title})

def update_book(collection, old_title, new_data):
    collection.update_one({"Title": old_title}, {"$set": new_data})

# --- APP LAYOUT ---
st.set_page_config(page_title="My Library", page_icon="📚", layout="wide")

st.title("📚 Personal Library Tracker")
st.write("Securely hosted on MongoDB Atlas.")

# Connect to DB
db = get_database()
# Create/Switch to the 'books' collection inside 'library_db'
collection = db["books"]

# Load current data
df = load_data(collection)

# --- SIDEBAR: ADD NEW BOOK ---
with st.sidebar:
    st.header("Add a New Book")
    with st.form("book_form", clear_on_submit=True):
        title = st.text_input("Title*")
        author = st.text_input("Author")
        purchased = st.text_input("Purchased At")
        read = st.checkbox("Read?")
        rating = st.select_slider("Rating", options=[1, 2, 3, 4, 5], value=3)
        notes = st.text_area("Notes")
        
        submitted = st.form_submit_button("Add Book")
        
        if submitted and title:
            new_book = {
                "Title": title,
                "Author": author,
                "Purchased": purchased,
                "Read": "Yes" if read else "No",
                "Rating": f"{'⭐' * rating}",
                "Notes": notes
            }
            save_book(collection, new_book)
            st.success(f"Added '{title}'!")
            st.rerun()
        elif submitted and not title:
            st.error("Title is required.")

# --- MAIN AREA: SEARCH AND VIEW ---
search_term = st.text_input("🔍 Search", "")

if search_term:
    mask = df.apply(lambda row: row.astype(str).str.lower().str.contains(search_term.lower()).any(), axis=1)
    display_df = df[mask]
else:
    display_df = df

st.subheader(f"Library ({len(display_df)} books)")
st.dataframe(display_df, use_container_width=True, hide_index=True)

# --- EDIT / DELETE SECTION ---
st.divider()
st.subheader("Edit or Delete")

if not df.empty:
    book_titles = df["Title"].tolist()
    selected_title = st.selectbox("Select Book", options=book_titles)

    if selected_title:
        current_data = df[df["Title"] == selected_title].iloc[0]
        
        col1, col2 = st.columns(2)
        with col1:
            edit_author = st.text_input("Author", value=current_data["Author"])
            edit_purchased = st.text_input("Purchased At", value=current_data["Purchased"])
        
        with col2:
            is_read = current_data["Read"] == "Yes"
            edit_read = st.checkbox("Read?", value=is_read)
            current_rating = current_data["Rating"].count("⭐")
            edit_rating = st.select_slider("Rating", options=[1, 2, 3, 4, 5], value=current_rating)

        edit_notes = st.text_area("Notes", value=current_data["Notes"])

        btn_col1, btn_col2 = st.columns(2)
        
        if btn_col1.button("💾 Update Book", use_container_width=True):
            updated_data = {
                "Author": edit_author,
                "Purchased": edit_purchased,
                "Read": "Yes" if edit_read else "No",
                "Rating": f"{'⭐' * edit_rating}",
                "Notes": edit_notes
            }
            update_book(collection, selected_title, updated_data)
            st.success("Updated!")
            st.rerun()

        if btn_col2.button("🗑️ Delete Book", use_container_width=True, type="primary"):
            delete_book(collection, selected_title)
            st.warning("Deleted!")
            st.rerun()