# Detailed `token.json` Generation Flow

The `token.json` file is not downloaded manually from Google Cloud Console.

Instead, it is generated automatically after the application successfully authenticates with your Google account using OAuth2.

This file stores:
- Google OAuth access token
- Google OAuth refresh token
- Token expiration information

The application later uses this file to access Google Drive without asking you to login every time.

---

# How `token.json` Is Created in This Project

Your `docker-compose.yaml` mounts the token file using:

```yaml
volumes:
  - ./sidecar/token.json:/app/token.json
```

This means:

| Host Machine | Docker Container |
|---|---|
| `./sidecar/token.json` | `/app/token.json` |

The application inside the container writes the generated token into:

```text
/app/token.json
```

which becomes:

```text
./sidecar/token.json
```

on your host machine.

---

# First-Time Authentication Process
This should be done in your test phase to release the application for production. Once completed and the token.json is retrieved, you can place the token.json file in the project directory so the application works as expected.

## Step 1 — Start the Containers

Run:

```bash
docker compose up
```

or:

```bash
docker-compose up
```

You should be able to check the logs with:
```bash
docker compose logs -f sidecar
```

---

## Step 2 — Application Requests Google Authorization

On first startup, the `sidecar` service detects that:

```text
/app/token.json
```

does not exist.

The application then starts the OAuth authentication process.
You may see logs similar to:

```text
Please visit this URL to authorize this application:
https://accounts.google.com/o/oauth2/auth?...
```

---

## Step 3 — Open the Authorization URL

Copy the URL from the container logs and open it in your browser.
Login with the Google account that should access Google Drive.

---

## Step 4 — Approve Permissions

Google displays a consent screen asking permission for the application to access your Google Drive.
Approve the requested permissions.

---

## Step 5 — Application Receives Authorization

After approval:
- Google sends authorization information back to the application
- the application exchanges it for OAuth tokens
- the application generates `token.json`

The file is then automatically saved at:

```text
sidecar/token.json
```

---

# Important Notes About `token.json`

## The File Is Sensitive

`token.json` contains long-lived authentication information.

Anyone with this file may potentially access your Google Drive.

Treat it like a password.

---

## Never Commit It to GitHub

Add to `.gitignore`:

```gitignore
sidecar/token.json
sidecar/credentials.json
```

---

## If `token.json` Is Deleted

The application will usually request authorization again during the next startup.

You will need to:
1. Open the authorization URL again
2. Login again
3. Approve permissions again

A new `token.json` file will then be generated automatically.

---

# Recommended Final Repository Structure

```text
project-root/
├── docker-compose.yaml
├── .env
├── app/
├── sidecar/
│   ├── credentials.json
│   ├── token.json
│   └── Dockerfile
```

This structure matches the paths configured in `docker-compose.yaml`.
