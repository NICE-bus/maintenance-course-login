import streamlit as st
from supabase import create_client
import pandas as pd
import hashlib

# Load credentials from Streamlit secrets
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
print(f"Debug: SUPABASE_URL - {SUPABASE_URL}")  # Debugging log
print(f"Debug: SUPABASE_KEY - {SUPABASE_KEY[:5]}...")  # Masked for security

# Connect to Supabase
try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("Debug: Supabase client created successfully")  # Debugging log
except Exception as e:
    print(f"Error: Failed to create Supabase client - {e}")  # Debugging log

def view_employees():
    """
    Displays a list of employees in a table format and allows the user to add or edit employees.
    """
    st.title("Employee Management")
    print("Debug: Entered view_employees function")  # Debugging log

    # Fetch employee data
    def fetch_employees():
        try:
            response = supabase.table("Employees").select("Adm_num, EE_NameF, EE_NameL, EE_HireDate, EE_TermDate, EE_StatusCode").execute()
            employees = pd.DataFrame(response.data)
            print(f"Debug: Fetched employees data - {employees}")  # Debugging log
            # Renames columns for better readability
            employees = employees.rename(
                columns={
                    "Adm_num": "Employee ID",
                    "EE_NameF": "First Name",
                    "EE_NameL": "Last Name",
                    "EE_HireDate": "Hire Date",
                    "EE_TermDate": "Termination Date",
                    "EE_StatusCode": "Status",
                }
            )
            print(f"Debug: Renamed employees columns - {employees.columns}")  # Debugging log

            return employees

        except Exception as e:
            print(f"Error: Failed to fetch employees data - {e}")  # Debugging log
            return pd.DataFrame()

    # Fetch and display the employees table
    employees = fetch_employees()
    if employees.empty:
        st.warning("No employees found in the database.")
        return

    # Use a placeholder to allow dynamic updates to the table
    table_placeholder = st.empty()
    with table_placeholder.container():
        st.subheader("Employees Table")
        st.dataframe(employees)

    # Add new employee
    st.subheader("Add New Employee")
    with st.form("add_employee"):
        emp_id = st.text_input("Employee ID")
        emp_fname = st.text_input("First Name")
        emp_lname = st.text_input("Last Name")
        hire_date = st.date_input("Hire Date")

        if st.form_submit_button("Add Employee"):
            try:
                # Convert hire_date to string format
                hire_date_str = hire_date.strftime("%Y-%m-%d")

                # Insert new employee with default values for EE_TermDate and EE_StatusCode
                supabase.table("Employees").insert(
                    {
                        "Adm_num": emp_id,
                        "EE_NameF": emp_fname,
                        "EE_NameL": emp_lname,
                        "EE_HireDate": hire_date_str,
                        "EE_TermDate": "9999-12-31",  # Automatically set Terminal Date
                        "EE_StatusCode": "Active",    # Automatically set Status Code
                    }
                ).execute()
                st.success("Employee added!")
                print("Debug: Employee added successfully")  # Debugging log

                # Refresh the employees table
                employees = fetch_employees()
                with table_placeholder.container():
                    st.subheader("Employees Table")
                    st.dataframe(employees)
            except Exception as e:
                st.error("Failed to add employee")
                print(f"Error: Failed to add employee - {e}")  # Debugging log
                
    # Edit existing employee
    st.subheader("Edit Existing Employee")
    # Update the dropdown to include Employee ID, First Name, and Last Name
    employee_ids = [f"{row['Employee ID']} - {row['First Name']} {row['Last Name']}" for _, row in employees.iterrows()]
    selected_employee = st.selectbox("Select Employee to Edit", [""] + employee_ids)
    if selected_employee:
        # Extract the Employee ID from the selected value and convert it to an integer
        selected_employee_id = int(selected_employee.split(" - ")[0].strip())
        print(f"Debug: Selected Employee ID - {selected_employee_id}")  # Debugging log
        print(f"Debug: Type of Selected Employee ID - {type(selected_employee_id)}")  # Debugging log

        # Ensure Employee ID column is an integer
        employees["Employee ID"] = employees["Employee ID"].astype(int)

        # Filter the DataFrame for the selected employee
        filtered_employee = employees[employees["Employee ID"] == selected_employee_id]

        if filtered_employee.empty:
            st.error("No matching employee found. Please check the Employee ID.")
            print("Error: No matching employee found.")  # Debugging log
            return

        # Pre-fill the form with the selected employee's data
        selected_employee_data = filtered_employee.iloc[0]
        emp_fname = st.text_input("First Name", value=selected_employee_data["First Name"])
        emp_lname = st.text_input("Last Name", value=selected_employee_data["Last Name"])

        # Dropdown for Employee Status
        emp_status = st.selectbox(
            "Employee Status",
            options=["Active", "Terminated"],
            index=0 if selected_employee_data["Status"] == "Active" else 1,
        )

        # Conditionally display Termination Date input
        term_date = None
        if emp_status == "Terminated":
            st.warning("Please provide a termination date.")
            try:
                term_date = pd.to_datetime(selected_employee_data["Termination Date"])
            except pd.errors.OutOfBoundsDatetime:
                term_date = pd.Timestamp.today()  # Fallback to today's date
            term_date = st.date_input("Termination Date", value=term_date)

        if st.button("Update Employee"):
            try:
                # Prepare the data for update
                update_data = {
                    "EE_NameF": emp_fname,
                    "EE_NameL": emp_lname,
                    "EE_StatusCode": emp_status,
                }

                # Include Termination Date if the status is Terminated
                if emp_status == "Terminated" and term_date:
                    update_data["EE_TermDate"] = term_date.strftime("%Y-%m-%d")
                elif emp_status == "Active":
                    update_data["EE_TermDate"] = "9999-12-31"  # Reset Term Date for Active employees

                # Update the employee record in the database
                supabase.table("Employees").update(update_data).eq("Adm_num", selected_employee_id).execute()
                st.success("Employee updated successfully!")
                print("Debug: Employee updated successfully")  # Debugging log

                # Refresh the employees table
                employees = fetch_employees()
                with table_placeholder.container():
                    st.subheader("Employees Table")
                    st.dataframe(employees)
            except Exception as e:
                st.error("Failed to update employee")
                print(f"Error: Failed to update employee - {e}")  # Debugging log
                
def sign_employee_into_course():
    """
    Allows the user to sign an employee into a course by selecting an employee, a course, 
    and specifying the date, hours, and comments for the activity.
    """
    st.title("Sign Employee Into Course")
    print("Debug: Entered sign_employee_into_course function")  # Debugging log

    # Fetch data
    try:
        employees = supabase.table("Employees").select("Adm_num, EE_NameF, EE_NameL").execute().data
        courses = supabase.table("EmployeeActivityType").select("ID, EAT_ActivityType").execute().data
        print(f"Debug: Fetched employees - {employees}")  # Debugging log
        print(f"Debug: Fetched courses - {courses}")  # Debugging log
    except Exception as e:
        st.error("Failed to fetch data from the database.")
        print(f"Error: Failed to fetch data - {e}")  # Debugging log
        employees, courses = [], []

    # Check if employees or courses are empty
    if not employees:
        st.warning("No employees found in the database. Please add employees first.")
        return
    if not courses:
        st.warning("No courses found in the database. Please add courses first.")
        return

    # Dropdowns for employee and course selection
    employee_selection = st.selectbox(
        "Select Employee",
        [f"{e['Adm_num']} - {e['EE_NameF']} {e['EE_NameL']}" for e in employees]
    )
    course_selection = st.selectbox(
        "Select Course",
        [f"{c['ID']} - {c['EAT_ActivityType']}" for c in courses]
    )

    # Input fields for date, hours, and comments
    activity_date = st.date_input("Date")
    hours = st.number_input("Hours", min_value=0.5, step=0.5)
    comments = st.text_area("Comments", placeholder="Enter any additional comments here...")

    # Button to sign in the employee
    if st.button("Sign In"):
        try:
            # Extract employee details
            employee_id = employee_selection.split(" - ")[0]  # Extract Adm_num
            employee_name = employee_selection.split(" - ")[1]  # Extract "FirstName LastName"
            first_name, last_name = employee_name.split(" ", 1)  # Split into first and last name

            # Extract course ID
            course_id = course_selection.split(" - ")[0]

            # Convert activity_date to string format
            activity_date_str = activity_date.strftime("%Y-%m-%d")

            # Insert data into the database
            supabase.table("EmployeeActivity").insert({
                "EA_Adm_num": employee_id,  # Employee ID
                "EA_NameF": first_name,  # First Name
                "EA_NameL": last_name,  # Last Name
                "EA_Activity": course_id,  # Course ID
                "EA_ActivityDate": activity_date_str,  # Activity Date
                "EA_ActivityHours": hours,  # Activity Hours
                "EA_Comments": comments  # Comments
            }).execute()
            st.success("Employee signed into course!")
            print("Debug: Employee signed into course successfully")  # Debugging log
        except Exception as e:
            st.error("Failed to sign employee into course")
            print(f"Error: Failed to sign employee into course - {e}")  # Debugging log

def view_employee_history():
    """
    Displays the course history of a specific employee within a specified date range.
    """
    st.title("Employee Course History")
    print("Debug: Entered view_employee_history function")  # Debugging log

    # Fetch employee data
    try:
        employees = supabase.table("Employees").select("Adm_num, EE_NameF, EE_NameL").execute().data
        print(f"Debug: Fetched employees - {employees}")  # Debugging log
    except Exception as e:
        st.error("Failed to fetch employees from the database.")
        print(f"Error: Failed to fetch employees - {e}")  # Debugging log
        employees = []

    # Check if employees are empty
    if not employees:
        st.warning("No employees found in the database. Please add employees first.")
        return

    # Dropdown for employee selection
    employee_selection = st.selectbox(
        "Select Employee",
        [f"{e['Adm_num']} - {e['EE_NameF']} {e['EE_NameL']}" for e in employees]
    )

    # Input fields for date range
    start_date = st.date_input("Start Date")
    end_date = st.date_input("End Date")

    if st.button("Fetch History"):
        try:
            # Extract the selected employee's ID
            employee_id = employee_selection.split(" - ")[0]  # Extract Adm_num
            print(f"Debug: Selected Employee ID - {employee_id}")  # Debugging log

            # Query to fetch employee history
            query = (
                supabase.table("EmployeeActivity")
                .select(
                    "EA_Adm_num, EA_NameF, EA_NameL, EA_ActivityDate, EA_ActivityHours, EA_Comments, "
                    "EmployeeActivityType(EAT_ActivityType)"
                )
                .eq("EA_Adm_num", employee_id)
                .gte("EA_ActivityDate", str(start_date))
                .lte("EA_ActivityDate", str(end_date))
                .execute()
            )

            # Convert the query result to a DataFrame
            data = query.data
            if data:
                df = pd.DataFrame(data)

                # Extract the "EAT_ActivityType" value from the EmployeeActivityType column
                if "EmployeeActivityType" in df.columns:
                    df["Course"] = df["EmployeeActivityType"].apply(
                        lambda x: x.get("EAT_ActivityType") if isinstance(x, dict) else None
                    )
                    df = df.drop(columns=["EmployeeActivityType"])  # Drop the original column

                # Rename columns for better readability
                df = df.rename(
                    columns={
                        "EA_Adm_num": "Employee ID",
                        "EA_NameF": "First Name",
                        "EA_NameL": "Last Name",
                        "EA_ActivityDate": "Activity Date",
                        "EA_ActivityHours": "Activity Hours",
                        "EA_Comments": "Comments",
                    }
                )

                # Reorder columns to place "Course" after "Last Name"
                column_order = [
                    "Employee ID",
                    "First Name",
                    "Last Name",
                    "Course",  # Move Course here
                    "Activity Date",
                    "Activity Hours",
                    "Comments",
                ]
                df = df[column_order]

                # Add a totals row
                totals = {
                    "Employee ID": "",
                    "First Name": "",
                    "Last Name": "",
                    "Course": f"Total Classes: {len(df)}",  # Count of rows
                    "Activity Date": "Total Hours -->",
                    "Activity Hours": df["Activity Hours"].sum(),  # Sum of Activity Hours
                    "Comments": ""
                }
                df = pd.concat([df, pd.DataFrame([totals])], ignore_index=True)

                # Display the DataFrame
                st.dataframe(df)
                print(f"Debug: Fetched employee history - {df}")  # Debugging log
            else:
                st.warning("No records found for the specified criteria.")
        except Exception as e:
            st.error("Failed to fetch employee history")
            print(f"Error: Failed to fetch employee history - {e}")  # Debugging log
            
def view_course_attendance():
    """
    Displays the attendance records for a specific course on a specific date.
    """
    st.title("Course Attendance")
    print("Debug: Entered view_course_attendance function")  # Debugging log

    # Fetch course data
    try:
        courses = supabase.table("EmployeeActivityType").select("ID, EAT_ActivityType").execute().data
        print(f"Debug: Fetched courses - {courses}")  # Debugging log
    except Exception as e:
        st.error("Failed to fetch courses")
        print(f"Error: Failed to fetch courses - {e}")  # Debugging log
        courses = []

    # Create a dropdown for course selection
    course_options = {course["EAT_ActivityType"]: course["ID"] for course in courses}
    selected_course = st.selectbox("Select Course", options=list(course_options.keys()))

    # Input for date
    date = st.date_input("Date")

    if st.button("Fetch Attendance"):
        try:
            # Get the corresponding course ID for the selected course
            course_id = course_options[selected_course]

            # Query to fetch attendance records
            query = (
                supabase.table("EmployeeActivity")
                .select("EA_Adm_num, EA_NameF, EA_NameL, EA_ActivityHours, EA_Comments, EA_ActivityDate")
                .eq("EA_Activity", course_id)
                .eq("EA_ActivityDate", str(date))
                .execute()
            )

            # Convert the query result to a DataFrame
            data = query.data
            if data:
                df = pd.DataFrame(data)
                # Rename columns for better readability
                df = df.rename(
                    columns={
                        "EA_Adm_num": "Employee ID",
                        "EA_NameF": "First Name",
                        "EA_NameL": "Last Name",
                        "EA_ActivityHours": "Hours",
                        "EA_Comments": "Comments",
                        "EA_ActivityDate": "Date",
                    }
                )
                st.dataframe(df)
                print(f"Debug: Fetched course attendance - {df}")  # Debugging log
            else:
                st.warning("No attendance records found for the selected course and date.")
        except Exception as e:
            st.error("Failed to fetch course attendance")
            print(f"Error: Failed to fetch course attendance - {e}")  # Debugging log


def hash_password(password):
    """
    Hashes a password using SHA-256.
    """
    return hashlib.sha256(password.encode()).hexdigest()

def login():
    """
    Displays a login page and authenticates the user.
    """
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        try:
            # Hash the entered password
            hashed_password = hash_password(password)
            print(f"Debug: Entered username - {username}")  # Debugging log
            print(f"Debug: Hashed password - {hashed_password}")  # Debugging log

            # Query the Supabase Users table
            response = supabase.table("Users").select("*").eq("username", username).eq("password", hashed_password).execute()
            print(f"Debug: Supabase response - {response.data}")  # Debugging log

            user = response.data

            if user:
                st.session_state["authenticated"] = True
                st.session_state["current_page"] = "Sign Employee Into Course"  # Set default page after login
                st.success("Login successful!")
                st.rerun()  # Force a rerun to display authenticated content
            else:
                st.error("Invalid username or password.")
        except Exception as e:
            st.error("Failed to authenticate.")
            print(f"Error: {e}")

def main():
    """
    Main function that provides navigation between different pages of the app.
    """
    # Initialize session state for authentication and current page
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if "current_page" not in st.session_state:
        st.session_state["current_page"] = "Login"

    # Check if the user is authenticated
    if not st.session_state["authenticated"]:
        # Show the login page if the user is not authenticated
        login()
    else:
        # Render the main app content
        st.sidebar.title("Navigation")
        option = st.sidebar.selectbox(
            "Choose a page",
            [
                "View Employees",
                "Sign Employee Into Course",
                "View Employee History",
                "View Course Attendance",
            ],
            index=["View Employees", "Sign Employee Into Course", "View Employee History", "View Course Attendance"].index(
                st.session_state["current_page"]
            ),
        )

        # Update the current page in session state
        st.session_state["current_page"] = option

        # Dynamically render the selected page
        if option == "View Employees":
            view_employees()
        elif option == "Sign Employee Into Course":
            sign_employee_into_course()
        elif option == "View Employee History":
            view_employee_history()
        elif option == "View Course Attendance":
            view_course_attendance()


if __name__ == "__main__":
    main()