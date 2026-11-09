# Corporate Convenience — Smart Ticket Classification Engine

### AI-Powered Workplace Ticket Management System

## About the Project

Corporate Convenience is an AI-powered workplace ticket management system designed to simplify how employees report workplace issues and communicate with the relevant departments.

The system uses machine learning and automated response generation to classify employee requests, identify the appropriate department and generate professional responses.

## Key Features

- **Employee Authentication:** Allows employees to register and log in.
- **Ticket Submission:** Employees can submit workplace requests and concerns.
- **AI Ticket Classification:** Automatically categorises requests into HR, IT, Finance and Operations.
- **Priority Detection:** Identifies the urgency of submitted requests.
- **Automated Responses:** Generates responses using different communication tones.
- **Ticket Management:** Stores tickets and tracks their status.
- **Ticket Ownership:** Links submitted tickets to individual employees.

## Technologies Used

- Python
- Flask
- HTML
- CSS
- JavaScript
- SQLite
- Scikit-learn
- Pandas

## Project Structure

```text
Corporate-Convenience/
│
├── backend/       # Backend functionality
├── data/          # Dataset
├── models/        # Trained machine learning model
├── static/        # CSS and JavaScript files
├── templates/     # HTML templates
├── tests/         # Application tests
├── app.py         # Application entry point
├── requirements.txt
└── README.md
```

## Running the Application

1. Clone or download the project repository.
2. Open the project folder in VS Code.
3. Activate the virtual environment.
4. Install the required dependencies using:

```bash
pip install -r requirements.txt
```

5. Run the application:

```bash
python app.py
```

6. Open the local address displayed in your terminal in a web browser.

## Project Status

Corporate Convenience is currently under development. Backend functionality, including authentication, ticket management, AI classification and automated response generation, has been implemented and tested.

Frontend integration and further system improvements are ongoing.

## Project Purpose

The goal of Corporate Convenience is to improve workplace communication, reduce manual ticket handling and make it easier for employees to receive assistance from the appropriate departments.


## Sprint 2: Data Tracking & Analytics

The support workspace now includes an **Analytics & Insights** dashboard for Support Staff and Administrators.

- Ticket volume over the selected 7, 30 or 90 day period
- Ticket distribution by department and status
- Average first staff response time
- Department-level response time comparison
- Automatically generated plain-language period insights
- Department-level scoping for Support Staff; organisation-wide view for Administrators

The analytics endpoint is `GET /api/analytics?days=7` (also accepts `30` and `90`). It uses the existing SQLite `tickets` and `responses` tables. Automatic ticket acknowledgements are excluded from response-time calculations; only sent staff replies count.

Chart.js is loaded from its public CDN by the dashboard page. An internet connection is therefore required for chart rendering.
