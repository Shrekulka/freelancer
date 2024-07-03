# Task Description:
**Objective:** Organize the distribution of personalized emails with a link to recipients from a CSV file.

**Conditions and Requirements:**
1. Each email must contain a personalized greeting and a link.
2. The distribution should be organized in batches of 10,000 emails.
3. The specified SMTP server must be used for sending emails.

# Solution:

## Execution Sequence:

### 1. Configuration Data Setup

The `config.py` file defines the SMTP server settings, including the server address, port, and user credentials (email and password).

**Description of the `Settings` Class Attributes:**

- **SMTP_SERVER (str):** Address of the SMTP server for sending emails.
- **SMTP_PORT (int):** Port of the SMTP server.
- **SMTP_USER (EmailStr):** Email address of the SMTP user for authentication.
- **SMTP_PASSWORD (SecretStr):** Secret password of the SMTP user.
- **CSV_FILENAME (str):** Name of the file with recipients (CSV). Default is "recipients.csv".
- **EMAIL_SUBJECT (str):** Subject of the email.
- **EMAIL_BODY_TEMPLATE (str):** Template of the email body with a personalized message and link.
- **PROGRESS_BAR_DESC (str):** Description for the progress bar during email sending.
- **MAX_CONCURRENT_EMAILS (int):** Maximum number of concurrent email sends.
- **SLEEP_DURATION (int):** Waiting time between email sends in seconds.

**Configuration of the `Settings` Class:**

- **env_file:** Name of the environment variables file (".env").
- **env_file_encoding:** Encoding of the environment variables file ("utf-8").

### 2. Reading Recipient Data from CSV File

The `csv_reader.py` module contains the `CSVReader` class, which asynchronously reads data from the CSV file (`recipients.csv`) and returns a list of dictionaries with recipient data (email, name, link).

### 3. Email Template Formation

The `EmailTemplate` class in the `email_template.py` module creates an email template with a personalized greeting and link for each recipient.

### 4. Sending Emails

The `EmailService` class in the `email_service.py` module is responsible for asynchronously sending emails. To organize parallel sending and control the number of simultaneous operations, a `Semaphore` is used. Each email is checked for the presence of all required fields before sending. After successfully sending each email, logging and progress bar updates are performed.

### 5. Running the Main Function

In the `main.py` file, the `main()` function initiates the email sending process:
- First, it reads the data from the CSV file.
- Then, the data is passed to `EmailService` for sending.
- In case of errors, exceptions are logged for subsequent analysis.

### 6. Exception Handling

If exceptions occur during both the reading of the CSV file and the sending of emails, detailed errors are logged for further analysis and resolution.

### 7. Program Termination

The program ensures proper application termination by handling exceptions, including the possibility of termination by the user.

## Project Structure

```bash
📁 email_blast/              # Project root directory
│
├── .env                     # File containing confidential data, such as API keys
│
├── .gitignore               # File that specifies files and folders that will not be tracked by git
│
├── README.md                # Project description file
│
├── config.py                # Project configuration variables file
│                            # Contains settings and configuration data for the project.
│
├── csv_reader.py            # File for reading data from CSV
│                            # Contains functions for asynchronously reading recipient data from CSV files.
│
├── email_service.py         # Email sending service file
│                            # Contains functions for asynchronously sending emails via SMTP server.
│
├── email_template.py        # Email templates file
│                            # Contains a class for creating personalized email templates.
│
├── logger_config.py         # Logger settings file for recording logs
│                            # Contains logger configuration for recording events and debug information.
│
├── main.py                  # Main script file that performs all the main functions
│                            # Main script for initiating email sending and managing the process.
│
├── recipients.csv           # CSV file with recipient data
│                            # File containing the list of recipients for sending personalized emails.
│
└── 📁 venv/                 # Python virtual environment
                             # Directory with the Python virtual environment for managing project dependencies.
```