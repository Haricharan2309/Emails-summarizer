# Email Summarizer & Notifier

This Python project retrieves all emails from your Gmail **Primary** tab that were received today, uses OpenAI's GPT-4 to generate a concise summary of each email, and then sends that summary to a designated email address via the Gmail API.

## Features

- **Fetch Today's Emails:**  
  Retrieves emails from the Primary category that arrived strictly between local midnight and midnight.
- **Summarize Emails:**  
  Uses OpenAI's GPT-4 to produce a summary for each email including:
  - The sender (From)
  - The subject
  - A short summary of the email body
  - Any mention of meetings, schedules, or deadlines
- **Send Summary Email:**  
  Sends the generated summary to a specified destination email address using the Gmail API.

## Prerequisites

- **Python 3.x**  
- Required Python libraries:
  - `google-auth-oauthlib`
  - `google-auth`
  - `google-api-python-client`
  - `pytz`
  - `openai`

You can install these dependencies using pip:

```bash
pip install google-auth-oauthlib google-auth google-api-python-client pytz openai


# Setup Instructions

##  Obtain Google API Credentials
To use the **Gmail API**, you need **OAuth 2.0** credentials:

1. **Go to the Google Cloud Console**:
   - Create a new project or select an existing one.

2. **Enable the Gmail API**:
   - Navigate to **APIs & Services > Library**.
   - Search for **Gmail API** and click **Enable**.

3. **Create OAuth 2.0 Credentials**:
   - Go to **APIs & Services > Credentials**.
   - Click **Create Credentials** and select **OAuth client ID**.
   - Configure the consent screen if prompted.
   - Choose **Desktop app** as the application type.
   - Click **Create** and then **Download** the resulting `client_secret.json` file.

4. **Place the Credentials**:
   - Save the downloaded `client_secret.json` file in the same folder as `main.py`.

## 3. Set Up the OpenAI API Key
Obtain your API key from **OpenAI**. For security, the code uses a placeholder (`"Get_API_Key_From_OpenAI"`). You should either:

- **Replace** the placeholder in the code with your actual API key, **or**
- **Modify** the code to load the key from an environment variable. For example, change the code to:

***** Get Oauth as client_secret file from GCP and save it same folder as main.py and get openai api key and modify in your code then code should probably work****
