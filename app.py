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
        st.dataframe(employees, hide_index=True)

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
    Allows the user to sign multiple employees into a course by selecting a training code, a course, 
    and specifying employees, hours, and comments for the activity.
    """
    st.title("Sign Employees Into Course")
    print("Debug: Entered sign_employee_into_course function")  # Debugging log

    # Fetch data
    try:
        employees = supabase.table("Employees").select("Adm_num, EE_NameF, EE_NameL, EE_StatusCode").execute().data
        courses = supabase.table("EmployeeActivityType").select("ID, EAT_ActivityCode, EAT_ActivityType").execute().data
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

    # Filter out terminated employees
    active_employees = [e for e in employees if e["EE_StatusCode"] != "Terminated"]
    print(f"Debug: Filtered active employees - {active_employees}")  # Debugging log

    # Step 1: Select Training Code
    training_code_selection = st.selectbox(
        "Select Training Code",
        [""] + ["OSHA", "Technical"],
        format_func=lambda x: "Please select a training code" if x == "" else x,
    )
    print(f"Debug: Selected training code - {training_code_selection}")  # Debugging log

    # Map training code to EAT_ActivityCode values
    training_code_map = {"OSHA": 1, "Technical": 2}
    selected_training_code = training_code_map.get(training_code_selection)

    # Filter courses based on the selected training code
    filtered_courses = [
        c for c in courses if c.get("EAT_ActivityCode") == selected_training_code
    ] if selected_training_code else []
    print(f"Debug: Filtered courses - {filtered_courses}")  # Debugging log

    # Step 2: Select Course
    if selected_training_code:
        course_selection = st.selectbox(
            "Select Course",
            [""] + [f"{c['ID']} - {c['EAT_ActivityType']}" for c in filtered_courses],
            format_func=lambda x: "Please select a course" if x == "" else x,
        )
        print(f"Debug: Selected course from dropdown - {course_selection}")  # Debugging log

        # Extract course ID
        if course_selection != "":
            course_id = course_selection.split(" - ")[0]  # Extract the course ID
            print(f"Debug: Selected Course ID - {course_id}")  # Debugging log

            # Step 3: Sign Employees Into Course
            employee_selection = st.multiselect(
                "Select Employees",
                options=[f"{e['Adm_num']} - {e['EE_NameF']} {e['EE_NameL']}" for e in active_employees],
                default=[],
            )

            # Input field for date
            activity_date = st.date_input("Date")

            # Input field for hours
            hours = st.number_input("Hours", min_value=0.0, step=0.5)

            # Input field for comments
            comments = st.text_area("Comments", placeholder="Enter any additional comments here...")

            # Button to sign in the employees
            if st.button("Sign In"):
                try:
                    # Convert activity_date to string format
                    activity_date_str = activity_date.strftime("%Y-%m-%d")

                    # Loop through selected employees and insert data into the database
                    for emp in employee_selection:
                        employee_id = emp.split(" - ")[0]  # Extract Adm_num
                        employee_name = emp.split(" - ")[1]  # Extract "FirstName LastName"
                        first_name, last_name = employee_name.split(" ", 1)  # Split into first and last name

                        # Insert data into the database
                        supabase.table("EmployeeActivity").insert({
                            "EA_Adm_num": employee_id,  # Employee ID
                            "EA_NameF": first_name,  # First Name
                            "EA_NameL": last_name,  # Last Name
                            "EA_Activity": course_id,  # Course ID
                            "EA_ActivityDate": activity_date_str,  # Activity Date
                            "EA_ActivityHours": hours,  # Activity Hours
                            "EA_Comments": comments,  # Comments
                        }).execute()

                    st.success("Employees signed into course!")
                    print("Debug: Employees signed into course successfully")  # Debugging log
                except Exception as e:
                    st.error("Failed to sign employees into course")
                    print(f"Error: Failed to sign employees into course - {e}")  # Debugging log
def activity_history():
    """
    Displays the Activity History page with options to view Employee Course History and Course Attendance.
    """
    st.title("Activity History")
    print("Debug: Entered activity_history function")  # Debugging log

    # Tabs for Employee Course History and Course Attendance
    tab1, tab2 = st.tabs(["Employee Course History", "Course Attendance"])

    # Tab 1: Employee Course History
    with tab1:
        st.subheader("Employee Course History")
        print("Debug: Viewing Employee Course History")  # Debugging log

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
        else:
            # Dropdown for employee selection
            employee_selection = st.selectbox(
                "Select Employee",
                [""] + [f"{e['Adm_num']} - {e['EE_NameF']} {e['EE_NameL']}" for e in employees],
                format_func=lambda x: "Please select an employee" if x == "" else x,
            )

            # Check if a valid employee is selected
            if employee_selection != "":
                # Extract the selected employee's ID
                employee_id = employee_selection.split(" - ")[0]  # Extract Adm_num
                print(f"Debug: Selected Employee ID - {employee_id}")  # Debugging log

                # Query to fetch employee history
                try:
                    query = (
                        supabase.table("EmployeeActivity")
                        .select(
                            "EA_Adm_num, EA_NameF, EA_NameL, EA_ActivityDate, EA_ActivityHours, EA_Comments, "
                            "EmployeeActivityType(EAT_ActivityType)"
                        )
                        .eq("EA_Adm_num", employee_id)
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
                            "Course",
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
                            "Course": f"Total Classes: {len(df)}",
                            "Activity Date": "Total Hours -->",
                            "Activity Hours": df["Activity Hours"].sum(),
                            "Comments": "",
                        }
                        df = pd.concat([df, pd.DataFrame([totals])], ignore_index=True)

                        # Display the DataFrame
                        st.dataframe(df, hide_index=True)
                        print(f"Debug: Fetched employee history - {df}")  # Debugging log
                    else:
                        st.warning("No records found for the selected employee.")
                except Exception as e:
                    st.error("Failed to fetch employee history")
                    print(f"Error: Failed to fetch employee history - {e}")  # Debugging log

    # Tab 2: Course Attendance
    with tab2:
        st.subheader("Course Attendance")
        print("Debug: Viewing Course Attendance")  # Debugging log

        # Fetch course data
        try:
            courses = supabase.table("EmployeeActivityType").select("ID, EAT_ActivityCode, EAT_ActivityType").execute().data
            print(f"Debug: Fetched courses - {courses}")  # Debugging log
        except Exception as e:
            st.error("Failed to fetch courses from the database.")
            print(f"Error: Failed to fetch courses - {e}")  # Debugging log
            courses = []

        # Check if courses are empty
        if not courses:
            st.warning("No courses found in the database. Please add courses first.")
        else:
            # Dropdown for training code selection
            training_code_selection = st.selectbox(
                "Select Training Code",
                [""] + ["OSHA", "Technical"],
                format_func=lambda x: "Please select a training code" if x == "" else x,
            )
            print(f"Debug: Selected training code - {training_code_selection}")  # Debugging log

            # Map training code to EAT_ActivityCode values
            training_code_map = {"OSHA": 1, "Technical": 2}
            selected_training_code = training_code_map.get(training_code_selection)

            # Filter courses based on the selected training code
            filtered_courses = [
                c for c in courses if c.get("EAT_ActivityCode") == selected_training_code
            ] if selected_training_code else []
            print(f"Debug: Filtered courses - {filtered_courses}")  # Debugging log

            # Show course selection dropdown if a valid training code is selected
            if selected_training_code:
                course_selection = st.selectbox(
                    "Select Course",
                    [""] + ["All"] + [f"{c['ID']} - {c['EAT_ActivityType']}" for c in filtered_courses],
                    format_func=lambda x: "Please select a course" if x == "" else x,
                )
                print(f"Debug: Selected course from dropdown - {course_selection}")  # Debugging log

                # Check if a valid course is selected
                if course_selection != "":
                    all_data = []  # List to store all rows
                    start = 0  # Start index for pagination
                    batch_size = 1000  # Number of rows to fetch per batch

                    if course_selection == "All":
                        # Fetch all data for the selected training code
                        print(f"Debug: Fetching all data for Training Code - {selected_training_code}")  # Debugging log

                        while True:
                            # Fetch a batch of rows
                            query = (
                                supabase.table("EmployeeActivity")
                                .select("EA_Adm_num, EA_NameF, EA_NameL, EA_ActivityHours, EA_Comments, EA_ActivityDate")
                                .in_("EA_Activity", [c["ID"] for c in filtered_courses])
                                .order("EA_ActivityDate", desc=True)
                                .range(start, start + batch_size - 1)
                                .execute()
                            )

                            # Append the fetched data to the list
                            data = query.data
                            if not data:
                                break  # Exit the loop if no more data is returned
                            all_data.extend(data)

                            # Move to the next batch
                            start += batch_size

                    else:
                        # Extract course ID
                        course_id = course_selection.split(" - ")[0]
                        print(f"Debug: Extracted Course ID - {course_id}")  # Debugging log

                        while True:
                            # Fetch a batch of rows for the selected course
                            query = (
                                supabase.table("EmployeeActivity")
                                .select("EA_Adm_num, EA_NameF, EA_NameL, EA_ActivityHours, EA_Comments, EA_ActivityDate")
                                .eq("EA_Activity", course_id)
                                .order("EA_ActivityDate", desc=True)
                                .range(start, start + batch_size - 1)
                                .execute()
                            )

                            # Append the fetched data to the list
                            data = query.data
                            print(f"Debug: Fetched data batch - {data}")  # Debugging log
                            if not data:
                                print("Debug: No more data returned, exiting loop.")  # Debugging log
                                break  # Exit the loop if no more data is returned
                            all_data.extend(data)

                            # Move to the next batch
                            start += batch_size

                    print(f"Debug: Total rows fetched - {len(all_data)}")  # Debugging log

                    # Convert the combined data to a DataFrame
                    if all_data:
                        df = pd.DataFrame(all_data)

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

                        # Combine First Name and Last Name into Full Name
                        df["Employee Name"] = df["First Name"].str.strip().str.title() + " " + df["Last Name"].str.strip().str.title()

                        # Drop the original First Name and Last Name columns
                        df = df.drop(columns=["First Name", "Last Name"])

                        # Reorder columns
                        column_order = ["Employee ID", "Employee Name", "Hours", "Comments", "Date"]
                        df = df[column_order]

                        # Calculate totals
                        total_hours = df["Hours"].sum()
                        total_attendees = len(df)

                        # Add a totals row with dynamic first column
                        if course_selection == "All":
                            first_col_value = f"Total {training_code_selection} courses"
                        else:
                            if " - " in course_selection:
                                first_col_value = f'{training_code_selection} - {course_selection.split(" - ")[1]}'
                            else:
                                first_col_value = f'{training_code_selection} - {course_selection}'

                        totals_row = {
                            "Employee ID": first_col_value,
                            "Employee Name": "Total Hours -->",
                            "Hours": total_hours,
                            "Comments": f"Total Attendees: {total_attendees}",
                            "Date": "",
                        }
                        df = pd.concat([df, pd.DataFrame([totals_row])], ignore_index=True)

                        # Display the DataFrame
                        st.dataframe(df, hide_index=True)
                        print(f"Debug: Displaying course attendance DataFrame - {df}")  # Debugging log
                    else:
                        st.warning("No records found for the selected course.")
def course_management():
    """
    Displays the Course Management page with options to view, add, and edit courses.
    """
    st.title("Course Management")
    print("Debug: Entered course_management function")  # Debugging log

    # Fetch course data
    def fetch_courses():
        try:
            response = supabase.table("EmployeeActivityType").select("ID, EAT_ActivityCode, EAT_ActivityType").execute()
            courses = pd.DataFrame(response.data)
            print(f"Debug: Fetched courses data - {courses}")  # Debugging log

            # Rename columns for better readability
            courses = courses.rename(
                columns={
                    "ID": "Course ID",
                    "EAT_ActivityCode": "Training Code",
                    "EAT_ActivityType": "Course Name",
                }
            )

            # Map Training Code values to their corresponding labels
            training_code_map = {1: "OSHA", 2: "Technical"}
            courses["Training Code"] = courses["Training Code"].map(training_code_map)

            print(f"Debug: Renamed courses columns - {courses.columns}")  # Debugging log
            print(f"Debug: Updated Training Code values - {courses['Training Code']}")  # Debugging log

            return courses

        except Exception as e:
            print(f"Error: Failed to fetch courses data - {e}")  # Debugging log
            return pd.DataFrame()

    # Fetch and display the courses table
    courses = fetch_courses()
    if courses.empty:
        st.warning("No courses found in the database.")
        return

    # Use a placeholder to allow dynamic updates to the table
    table_placeholder = st.empty()
    with table_placeholder.container():
        st.subheader("Courses Table")
        st.dataframe(courses, hide_index=True)

    # Add New Course
    st.subheader("Add New Course")
    with st.form("add_course"):
        course_name = st.text_input("Course Name")
        training_code = st.selectbox("Training Code", ["Select Training Code","OSHA", "Technical"])

        if st.form_submit_button("Add Course"):
            try:
                # Map training code to its corresponding value
                training_code_map = {"OSHA": 1, "Technical": 2}
                training_code_value = training_code_map.get(training_code)

                # Fetch the current maximum Course ID
                response = supabase.table("EmployeeActivityType").select("ID").order("ID", desc=True).limit(1).execute()
                max_id = response.data[0]["ID"] if response.data else 0
                next_id = max_id + 1
                print(f"Debug: Calculated next Course ID - {next_id}")  # Debugging log

                # Insert new course into the database
                supabase.table("EmployeeActivityType").insert(
                    {
                        "ID": next_id,  # Set the next Course ID
                        "EAT_ActivityCode": training_code_value,
                        "EAT_ActivityType": course_name,
                    }
                ).execute()
                st.success("Course added successfully!")
                print("Debug: Course added successfully")  # Debugging log

                # Refresh the courses table
                courses = fetch_courses()
                with table_placeholder.container():
                    st.subheader("Courses Table")
                    st.dataframe(courses)
            except Exception as e:
                st.error("Failed to add course")
                print(f"Error: Failed to add course - {e}")  # Debugging log

    # Edit Existing Course
    st.subheader("Edit Existing Course")
    # Update the dropdown to include Course ID and Course Name
    course_ids = [f"{row['Course ID']} - {row['Course Name']}" for _, row in courses.iterrows()]
    selected_course = st.selectbox("Select Course to Edit", [""] + course_ids)
    if selected_course:
        # Extract the Course ID from the selected value
        selected_course_id = int(selected_course.split(" - ")[0].strip())
        print(f"Debug: Selected Course ID - {selected_course_id}")  # Debugging log

        # Filter the DataFrame for the selected course
        filtered_course = courses[courses["Course ID"] == selected_course_id]

        if filtered_course.empty:
            st.error("No matching course found. Please check the Course ID.")
            print("Error: No matching course found.")  # Debugging log
            return

        # Pre-fill the form with the selected course's data
        selected_course_data = filtered_course.iloc[0]
        course_name = st.text_input("Course Name", value=selected_course_data["Course Name"])
        training_code = st.selectbox(
            "Training Code",
            options=["OSHA", "Technical"],
            index=0 if selected_course_data["Training Code"] == 1 else 1,
        )

        if st.button("Update Course"):
            try:
                # Map training code to its corresponding value
                training_code_map = {"OSHA": 1, "Technical": 2}
                training_code_value = training_code_map.get(training_code)

                # Prepare the data for update
                update_data = {
                    "EAT_ActivityType": course_name,
                    "EAT_ActivityCode": training_code_value,
                }

                # Update the course record in the database
                supabase.table("EmployeeActivityType").update(update_data).eq("ID", selected_course_id).execute()
                st.success("Course updated successfully!")
                print("Debug: Course updated successfully")  # Debugging log

                # Refresh the courses table
                courses = fetch_courses()
                with table_placeholder.container():
                    st.subheader("Courses Table")
                    st.dataframe(courses)
            except Exception as e:
                st.error("Failed to update course")
                print(f"Error: Failed to update course - {e}")  # Debugging log
                
def hash_password(password):
    """
    Hashes a password using SHA-256.
    """
    return hashlib.sha256(password.encode()).hexdigest()

def login():
    """
    Displays a login page and authenticates the user.
    """
    # The above code is using the Streamlit library in Python to create a title "Login" for a web
    # application or dashboard.
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
        st.session_state["current_page"] = "Course Sign In"  # Updated default page name

    # Fix for old session state values
    if st.session_state["current_page"] == "Sign Employee Into Course":
        st.session_state["current_page"] = "Course Sign In"

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
                "Course Sign In",
                "View Activity History",
                "Employee Management",
                "Course Management",
            ],
            index=[
                "Course Sign In",
                "View Activity History",
                "Employee Management",
                "Course Management",
            ].index(st.session_state["current_page"]),
        )

        # Check if the selected page has changed
        if option != st.session_state["current_page"]:
            st.session_state["current_page"] = option
            st.rerun()  # Force a rerun to load the selected page

        # Dynamically render the selected page
        if option == "Course Sign In":
            sign_employee_into_course()
        elif option == "View Activity History":
            activity_history()
        elif option == "Employee Management":
            view_employees()
        elif option == "Course Management":
            course_management()
            
if __name__ == "__main__":
    main()