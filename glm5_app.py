import streamlit as st
import pandas as pd
import pymongo
import os

# --- DATABASE CONNECTION ---
# We use st.secrets for security on the web. 
# For local testing, it falls back to a dummy string if secrets aren't found.

def get_database():
    # Try to get the URI from Streamlit Secrets (for Web)
    try:
        uri = st.secrets["MONGO_URI"]
    except:
        # Fallback for local testing (Replace with your actual URI for local runs)
        # Ideally, put this in a .streamlit/secrets.toml file locally
        uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017") 

    client = pymongo.MongoClient(uri)
    return client["library_db"]

# --- HELPER FUNCTIONS ---
def load_data(collection):
    """Load data from MongoDB to a DataFrame."""
    data = list(collection.find({}, {'_id': 0})) # Exclude the internal _id field
    if not data:
        return pd.DataFrame(columns=["Title", "Author", "Purchased", "Read", "Rating", "Notes"])
    return pd.DataFrame(data)

def save_book(collection, book_data):
    """Insert a single book."""
    collection.insert_one(book_data)

def delete_book(collection, title):
    """Delete a book by title."""
    collection.delete_one({"Title": title})

def update_book(collection, old_title, new_data):
    """Update a book by title."""
    collection.update_one({"Title": old_title}, {"$set": new_data})

# --- APP LAYOUT ---
st.set_page_config(page_title="My Library", page_icon="📚", layout="wide")

st.title("📚 Personal Library Tracker (MongoDB Edition)")
st.write("Data is securely stored in the cloud.")

# Connect to DB
db = get_database()
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
            st.success(f"Added '{title}' to library!")
            st.rerun()
        elif submitted and not title:
            st.error("Title is required.")

# --- MAIN AREA: SEARCH AND VIEW ---
search_term = st.text_input("🔍 Search by Title, Author, or Notes", "")

# Filter Data (Client-side filtering)
if search_term:
    mask = df.apply(lambda row: row.astype(str).str.lower().str.contains(search_term.lower()).any(), axis=1)
    display_df = df[mask]
else:
    display_df = df

st.subheader(f"Library ({len(display_df)} books)")
st.dataframe(
    display_df, 
    use_container_width=True, 
    hide_index=True,
    column_config={
        "Notes": st.column_config.TextColumn("Notes", width="large"),
        "Rating": st.column_config.TextColumn("Rating", width="small")
    }
)

# --- EDIT / DELETE SECTION ---
st.divider()
st.subheader("Edit or Delete a Book")

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
            st.success("Book updated!")
            st.rerun()

        if btn_col2.button("🗑️ Delete Book", use_container_width=True, type="primary"):
            delete_book(collection, selected_title)
            st.warning("Book deleted!")
            st.rerun()