
import streamlit as st
import pandas as pd

from classifier import predict_department
from database import (
    init_db,
    save_ticket,
    get_all_tickets,
    update_ticket_status,
)


# -----------------------------
# Page configuration
# -----------------------------
st.set_page_config(
    page_title="Corporate Convenience",
    page_icon="📋",
    layout="wide",
)

# Create the database tables if necessary.
init_db()


# -----------------------------
# Header
# -----------------------------
st.title("Corporate Convenience")
st.subheader("Workplace Request Management")

st.write(
    "Submit a workplace request and let the classifier "
    "identify the department best suited to handle it."
)

st.divider()


# -----------------------------
# Submit a new request
# -----------------------------
st.header("Submit a Request")

with st.form("request_form", clear_on_submit=True):
    message = st.text_area(
        "Describe your workplace request",
        placeholder=(
            "Example: I cannot connect to the office Wi-Fi."
        ),
        height=130,
    )

    submitted = st.form_submit_button(
        "Classify and Submit Request",
        type="primary",
    )


if submitted:
    if not message.strip():
        st.error("Please describe your request before submitting.")

    else:
        try:
            department = predict_department(message)

            # Save the request and its predicted department.
            ticket = save_ticket(message, department)

            st.session_state["last_ticket"] = ticket

            st.success("Your request has been submitted successfully!")

        except FileNotFoundError as error:
            st.error(str(error))

        except ValueError as error:
            st.error(str(error))

        except Exception as error:
            st.error(
                "The request could not be saved. "
                "Please check the database configuration."
            )
            st.exception(error)


# -----------------------------
# Display the latest ticket
# -----------------------------
last_ticket = st.session_state.get("last_ticket")

if last_ticket:
    st.subheader("Your Submitted Ticket")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Ticket ID",
        last_ticket["ticket_id"],
    )

    col2.metric(
        "Assigned Department",
        last_ticket["department"],
    )

    col3.metric(
        "Current Status",
        last_ticket["status"],
    )

    st.write("**Request:**", last_ticket["message"])
    st.write("**Created:**", last_ticket["created_at"])

st.divider()


# -----------------------------
# View all tickets
# -----------------------------
st.header("All Requests")

tickets = get_all_tickets()

if tickets:
    ticket_df = pd.DataFrame(tickets)

    st.dataframe(
        ticket_df,
        use_container_width=True,
        hide_index=True,
    )

    st.caption(f"Total tickets: {len(tickets)}")

    # -------------------------
    # Update ticket status
    # -------------------------
    st.subheader("Update Request Status")

    ticket_options = {
        ticket["ticket_id"]: (
            f"Ticket #{ticket['ticket_id']} - "
            f"{ticket['department']} - "
            f"{ticket['status']}"
        )
        for ticket in tickets
    }

    selected_ticket_id = st.selectbox(
        "Select a ticket",
        options=list(ticket_options.keys()),
        format_func=lambda ticket_id: ticket_options[ticket_id],
    )

    selected_ticket = next(
        ticket
        for ticket in tickets
        if ticket["ticket_id"] == selected_ticket_id
    )

    statuses = ["Open", "In Progress", "Resolved"]

    current_status = selected_ticket["status"]

    status_index = (
        statuses.index(current_status)
        if current_status in statuses
        else 0
    )

    new_status = st.selectbox(
        "New status",
        options=statuses,
        index=status_index,
        key=f"status_{selected_ticket_id}",
    )

    if st.button("Save Status", type="secondary"):
        try:
            update_ticket_status(
                selected_ticket_id,
                new_status,
            )

            st.success(
                f"Ticket #{selected_ticket_id} updated to "
                f"{new_status}."
            )

            st.rerun()

        except Exception as error:
            st.error("Could not update the ticket status.")
            st.exception(error)

else:
    st.info(
        "No requests have been submitted yet. "
        "Your tickets will appear here."
    )
