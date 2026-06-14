# Google Drive Environment Variables Setup Guide

This document explains how to retrieve and configure the required environment variables for an application that accesses Google Drive.

---

# 1. `RESTORE_AUTH_TOKEN`

```env
RESTORE_AUTH_TOKEN=change-me-to-a-secure-token
```

## What it is
This is **not provided by Google**.

It is an application-specific secret token used to authenticate restore operations or API requests in your app.

## What you should do
Generate a long random string yourself.

### Good examples
You can generate one with:

Linux/macOS:

```bash
openssl rand -hex 32
```

Example output:

```text
8f1c3e9d7a4b6c2f8d1a9e0b4c7d2f6a8b1c3d5e7f9a0b2c4d6e8f1a3b5c7d9
```

Then:

```env
RESTORE_AUTH_TOKEN=8f1c3e9d7a4b6c2f8d1a9e0b4c7d2f6a8b1c3d5e7f9a0b2c4d6e8f1a3b5c7d9
```

---

# 2. `GOOGLE_DRIVE_FOLDER_ID`

```env
GOOGLE_DRIVE_FOLDER_ID=your-google-drive-folder-id
```

## What it is
This is the ID of the Google Drive folder your application will access.

## How to retrieve it

1. Open Google Drive:
   https://drive.google.com

2. Create a folder or open an existing one.

3. Look at the URL in your browser.

Example:

```text
https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOpQrStUvWxYz123456
```

The folder ID is:

```text
1AbCdEfGhIjKlMnOpQrStUvWxYz123456
```

Then set:

```env
GOOGLE_DRIVE_FOLDER_ID=1AbCdEfGhIjKlMnOpQrStUvWxYz123456
```

---

# 3. `GOOGLE_CREDENTIALS_PATH`

```env
GOOGLE_CREDENTIALS_PATH=credentials.json
```

## What it is
This points to the OAuth client credentials file downloaded from Google Cloud.

This file contains:
- Client ID
- Client Secret
- OAuth configuration

It is usually named:

```text
credentials.json
```

---

## How to create and download it

### Step 1 — Open Google Cloud Console

Go to:

https://console.cloud.google.com

---

### Step 2 — Create a Project

1. Click the project selector at the top
2. Click:
   - “New Project”
3. Create a project name
4. Create the project

---

### Step 3 — Enable Google Drive API

1. Open:

https://console.cloud.google.com/apis/library/drive.googleapis.com

2. Click:
   - “Enable”

---

### Step 4 — Configure OAuth Consent Screen

Open:

https://console.cloud.google.com/apis/credentials/consent

Choose:
- External (usually easiest for personal use)

Fill:
- App name
- Your email

Add scopes:
- Google Drive API scopes if requested (e.g., `.../auth/drive`)

### **CRITICAL STEP: Add Test Users**
If your "Publishing status" is set to **Testing** (which is the default):
1. Find the **Test users** section on the same page. (Check Audience on the left hand-side menu)
2. Click **+ ADD USERS**.
3. Add the **email address** of the Google account you will use to authorize the app.
4. Click **SAVE**.

*If you skip this, you will receive an "Error 403: access_denied" during login.*

---

### Step 5 — Create OAuth Client Credentials

Open:

https://console.cloud.google.com/apis/credentials

1. Click:
   - “Create Credentials”
   - “OAuth client ID”

2. Application type:
   - Desktop App (usually easiest for CLI/server tools)

3. Create it.

---

### Step 6 — Download credentials.json

After creation:
1. Click the download button
2. Save the file as:

```text
credentials.json
```

Place it where your app expects it.

Example:

```text
/app/sidecar/credentials.json
```

Then:

```env
GOOGLE_CREDENTIALS_PATH=credentials.json
```

Or absolute path:

```env
GOOGLE_CREDENTIALS_PATH=/opt/myapp/credentials.json
```

---

# 4. `GOOGLE_TOKEN_PATH`

```env
GOOGLE_TOKEN_PATH=token.json
```

## What it is
This is the OAuth access/refresh token generated **after login authorization**.

Usually:
- Your application generates this automatically
- The first time you run the app, it opens a browser login
- You sign into Google
- Google asks permission
- The app saves `token.json`

---

## Typical flow

### First run

Your app may show something like:

```text
Please visit this URL to authorize this application:
https://accounts.google.com/o/oauth2/auth?...
```

You:
1. Open the URL
2. Login with Google
3. Approve access

Then the app creates:

```text
token.json
```

Automatically.

---

## Where to place it

Usually in the same folder:

```text
/app/sidecar/token.json
```

Then:

```env
GOOGLE_TOKEN_PATH=token.json
```

Or:

```env
GOOGLE_TOKEN_PATH=/opt/myapp/token.json
```

---

# Important Security Notes

## Never commit these files to Git

Do NOT upload:
- `credentials.json`
- `token.json`

to GitHub.

Add to `.gitignore`:

```gitignore
credentials.json
token.json
```

---

## `token.json` is sensitive

It can grant access to your Google Drive.

Treat it like a password.

---

---

# Why Google Cloud Project is Required for Google Drive Access

A common point of confusion is why a Google Cloud Project is required even when accessing a personal Google Drive account.

The important distinction is:

- Google Drive stores your files
- Google Cloud Project identifies the application accessing those files

Google uses the Cloud Project as the identity of your application.

---

## Why Google Cloud Project is Required

When an external application wants to access:
- Google Drive
- Gmail
- Google Calendar
- Google Photos
- Google Docs
- etc.

Google requires:
1. An application identity
2. Permission scopes
3. User consent
4. API usage tracking
5. Security controls

All of that is managed through a Google Cloud Project.

---

## What `credentials.json` Actually Represents

The `credentials.json` file is NOT your Google account password.

It contains:
- OAuth Client ID
- OAuth Client Secret
- App identification information

Example structure:

```json
{
  "installed": {
    "client_id": "...apps.googleusercontent.com",
    "project_id": "my-project",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "client_secret": "..."
  }
}
```

This tells Google:

> “This application named X is requesting Drive access.”

---

## Why Google Does This

Without this system, any random application could:
- impersonate apps
- abuse Google APIs
- steal data
- spam APIs anonymously

Google therefore requires:
- app registration
- API enablement
- consent configuration
- rate limiting
- auditability

The Cloud Project acts as the container for those controls.

---

## The Real Authentication Flow

The actual process is:

### Step 1 — App identifies itself

Using:
- `credentials.json`

The app says:

> “I am application ABC.”

---

### Step 2 — User logs into Google

You authenticate with:
- your Google account
- your password
- possibly MFA

---

### Step 3 — Google asks for consent

Example:

> “Application ABC wants access to your Google Drive.”

You approve it.

---

### Step 4 — Google issues tokens

Google generates:
- access token
- refresh token

Saved into:
- `token.json`

---

## Why Not Just Use Username/Password?

Google intentionally blocks this.

Modern Google APIs no longer allow:
- raw password authentication
- “login with email/password” access

because it is insecure.

OAuth2 is now mandatory.

---

## Relationship Between Components

Think of it like this:

| Component | Purpose |
|---|---|
| Google Account | Owns the Drive files |
| Google Cloud Project | Defines the application |
| OAuth Client | Represents the app identity |
| credentials.json | App identity configuration |
| token.json | User authorization result |

---

## Important Concept

The Google Cloud Project does NOT mean:
- you are deploying servers on Google Cloud
- you are paying for cloud hosting
- you are using Compute Engine

It is only being used as:
- an API management layer
- OAuth identity provider configuration

Many people use Google Cloud Projects ONLY for API access and nothing else.

---

## Why Google Drive API Must Be Enabled

By default, APIs are disabled.

Google requires explicit activation because:
- APIs consume resources
- quotas must be managed
- billing can apply for some APIs
- abuse prevention

So when you enable:
- Google Drive API

you are telling Google:

> “This app is allowed to request Google Drive operations.”

---

## Typical Architecture

```text
Your App
   ↓
Google OAuth Server
   ↓
Google Drive API
   ↓
Your Google Drive Files
```

The Cloud Project exists mainly in the OAuth/API layer.

---

## Analogy

Imagine:
- Your Google account = your bank account
- Google Cloud Project = a registered ATM application
- credentials.json = ATM machine ID
- token.json = your temporary session authorization

The ATM itself does not own your money.
It is simply authorized to access it securely.

---

# Typical Final Example

```env
RESTORE_AUTH_TOKEN=8f1c3e9d7a4b6c2f8d1a9e0b4c7d2f6a8b1c3d5e7f9a0b2c4d6e8f1a3b5c7d9

GOOGLE_DRIVE_FOLDER_ID=1AbCdEfGhIjKlMnOpQrStUvWxYz123456

GOOGLE_CREDENTIALS_PATH=/opt/myapp/credentials.json
GOOGLE_TOKEN_PATH=/opt/myapp/token.json
```

