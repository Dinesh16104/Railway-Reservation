import streamlit as st
import sqlite3
import pandas as pd

conn = sqlite3.connect('railway.db')
c = conn.cursor()

# ------------------- Create DB Tables -------------------
def create_db():
    c.execute("CREATE TABLE IF NOT EXISTS users (username TEXT, password TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS employees (employee_id TEXT, password TEXT, designation TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS trains (train_number TEXT, train_name TEXT, departure_date TEXT, start_destination TEXT, end_destination TEXT)")
    conn.commit()

create_db()

# ------------------- Add Train -------------------
def add_train(train_number, train_name, departure_date, start_destination, end_destination):
    c.execute("SELECT * FROM trains WHERE train_number=? AND departure_date=?", (train_number, departure_date))
    if c.fetchone():
        st.warning("Train already exists for this date.")
        return
    c.execute("INSERT INTO trains VALUES (?, ?, ?, ?, ?)", (train_number, train_name, departure_date, start_destination, end_destination))
    conn.commit()
    create_seat_table(train_number)

# ------------------- Create Seat Table -------------------
def create_seat_table(train_number):
    c.execute(f"""
        CREATE TABLE IF NOT EXISTS seats_{train_number} (
            seat_number INTEGER PRIMARY KEY,
            seat_type TEXT,
            booked INTEGER,
            passenger_name TEXT,
            passenger_age INTEGER,
            passenger_gender TEXT
        )
    """)
    c.execute(f"SELECT COUNT(*) FROM seats_{train_number}")
    if c.fetchone()[0] == 0:
        for i in range(1, 51):
            seat_type = categorize_seat(i)
            c.execute(f"""
                INSERT INTO seats_{train_number} 
                (seat_number, seat_type, booked, passenger_name, passenger_age, passenger_gender)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (i, seat_type, 0, '', None, ''))
        conn.commit()

def categorize_seat(seat_number):
    if (seat_number % 10) in [0, 4, 5, 9]:
        return "Window"
    elif (seat_number % 10) in [2, 3, 6, 7]:
        return "Aisle"
    else:
        return "Middle"

# ------------------- Book Tickets -------------------
def allocate_next_available_seat(train_number, seat_type):
    seat_query = c.execute(f"SELECT seat_number FROM seats_{train_number} WHERE booked=0 AND seat_type=? ORDER BY seat_number ASC", (seat_type,))
    result = seat_query.fetchone()
    return result

def book_tickets(train_number, passenger_name, passenger_gender, passenger_age, seat_type):
    train_query = c.execute("SELECT * FROM trains WHERE train_number=?", (train_number,))
    train_data = train_query.fetchone()
    if train_data:
        seat_number = allocate_next_available_seat(train_number, seat_type)
        if seat_number:
            c.execute(f"""
                UPDATE seats_{train_number} 
                SET booked=1, seat_type=?, passenger_name=?, passenger_age=?, passenger_gender=?
                WHERE seat_number=?
            """, (seat_type, passenger_name, passenger_age, passenger_gender, seat_number[0]))
            conn.commit()
            st.success("Ticket Booked Successfully")
        else:
            st.warning("No seat available of selected type.")

# ------------------- Cancel Ticket -------------------
def cancel_tickets(train_number, seat_number):
    c.execute(f"""
        UPDATE seats_{train_number} 
        SET booked=0, passenger_name='', passenger_age=NULL, passenger_gender=''
        WHERE seat_number=?
    """, (seat_number,))
    conn.commit()
    st.success("Ticket Cancelled")

# ------------------- View Seats -------------------
def view_seats(train_number):
    seat_query = c.execute(f"""
        SELECT 
            seat_number, 
            seat_type, 
            booked, 
            passenger_name, 
            passenger_age, 
            passenger_gender 
        FROM seats_{train_number} 
        ORDER BY seat_number ASC
    """)
    df = pd.DataFrame(seat_query.fetchall(), columns=["Seat No", "Type", "Booked", "Name", "Age", "Gender"])
    st.dataframe(df)

# ------------------- Delete Train -------------------
def delete_train(train_number, departure_date):
    c.execute("DELETE FROM trains WHERE train_number=? AND departure_date=?", (train_number, departure_date))
    c.execute(f"DROP TABLE IF EXISTS seats_{train_number}")
    conn.commit()
    st.success("Train Deleted")

# ------------------- UI and Main Logic -------------------
def train_functions():
    st.title("Train Administration")
    functions = st.sidebar.selectbox("Select Function", [
        "Add Train", "View Trains", "Search Train", "Delete Train",
        "Book Tickets", "Cancel Ticket", "View Seats"
    ])

    if functions == "Add Train":
        with st.form("add_train_form"):
            train_number = st.text_input("Train Number")
            train_name = st.text_input("Train Name")
            departure_date = st.text_input("Departure Date")
            start_destination = st.text_input("Start Destination")
            end_destination = st.text_input("End Destination")
            submitted = st.form_submit_button("Add Train")
            if submitted and all([train_number, train_name, departure_date, start_destination, end_destination]):
                add_train(train_number, train_name, departure_date, start_destination, end_destination)

    elif functions == "View Trains":
        trains = c.execute("SELECT * FROM trains").fetchall()
        df = pd.DataFrame(trains, columns=["Train No", "Name", "Date", "Start", "End"])
        st.dataframe(df)

    elif functions == "Search Train":
        st.header("Search Train")
        search_by = st.radio("Search By", ["Train Number", "Start Destination", "End Destination"])
        query = st.text_input("Enter Search Text")
        if st.button("Search"):
            if search_by == "Train Number":
                trains = c.execute("SELECT * FROM trains WHERE train_number LIKE ?", ('%' + query + '%',)).fetchall()
            elif search_by == "Start Destination":
                trains = c.execute("SELECT * FROM trains WHERE start_destination LIKE ?", ('%' + query + '%',)).fetchall()
            elif search_by == "End Destination":
                trains = c.execute("SELECT * FROM trains WHERE end_destination LIKE ?", ('%' + query + '%',)).fetchall()
            else:
                trains = []

            if trains:
                df = pd.DataFrame(trains, columns=["Train No", "Name", "Date", "Start", "End"])
                st.dataframe(df)
            else:
                st.info("No matching trains found.")

    elif functions == "Book Tickets":
        st.header("Book Train Ticket")
        train_number = st.text_input("Train Number")
        seat_type = st.selectbox("Seat Type", ["Window", "Aisle", "Middle"])
        passenger_name = st.text_input("Passenger Name")
        passenger_age = st.number_input("Passenger Age", min_value=1)
        passenger_gender = st.selectbox("Passenger Gender", ["Male", "Female"])
        if st.button("Book Ticket"):
            if train_number and passenger_name and passenger_gender:
                book_tickets(train_number, passenger_name, passenger_gender, passenger_age, seat_type)

    elif functions == "Cancel Ticket":
        st.header("Cancel Ticket")
        train_number = st.text_input("Train Number")
        seat_number = st.number_input("Seat Number", min_value=1)
        if st.button("Cancel Ticket"):
            cancel_tickets(train_number, seat_number)

    elif functions == "View Seats":
        st.header("View Seats")
        train_number = st.text_input("Train Number")
        if st.button("View"):
            view_seats(train_number)

    elif functions == "Delete Train":
        st.header("Delete Train")
        train_number = st.text_input("Train Number")
        departure_date = st.text_input("Departure Date")
        if st.button("Delete"):
            delete_train(train_number, departure_date)

train_functions()
conn.close()
