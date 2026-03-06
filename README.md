# DynamoDB Table Cloner

Clone DynamoDB tables from cloud to local DynamoDB with automated AWS SSO authentication.

## Features

- **Simple .env Configuration** - All settings in one place!
- **Automated AWS SSO Authentication** - No manual credential management!
- Clone table schema and data from cloud to local DynamoDB
- Auto-rename tables: `dev_users` → `local_users`
- Discover tables across AWS regions
- Batch operations with progress tracking

## Setup

1. **Start Local DynamoDB**

   - Make sure you have a local DynamoDB instance running at `http://localhost:8000`.
   - You can use NoSql Workbench, DynamoDB Local Docker image, or any.

2. **Install Dependencies**

   ```bash
   pip install -r requirements.txt

   # Or with uv
   uv pip install -r requirements.txt
   ```

3. **Configure Environment** - Create `.env` file from template:

   ```bash
   cp .env.template .env
   ```

   Then edit `.env` with your settings:

   ```env
   # AWS SSO Configuration
   AWS_SSO_PROFILE=your-sso-profile-name
   AWS_ACCOUNT_ID=YOUR_AWS_ACCOUNT_ID
   AWS_ROLE_NAME=YOUR_ROLE_NAME
   AWS_REGION=your-aws-region

   # Local DynamoDB Configuration
   LOCAL_DYNAMODB_ENDPOINT=http://localhost:8000
   LOCAL_TABLE_PREFIX=local_
   BATCH_SIZE=25
   ```

## Usage

### Activate Virtual Env

```bash
source .venv/bin/activate
```

### Clone Tables

The cloner uses automated AWS SSO authentication. Configuration is read from `.env`:

```bash
# Clone a table (automatically handles SSO login)
python3 table_cloner.py dev_Dashboard

# Clone another table
python3 table_cloner.py dev_users

# List available tables first
python3 table_cloner.py --list-tables
```

### Discover Tables

All commands use the `.env` configuration automatically:

```bash
# List all tables in configured region
python3 list_tables.py

# Filter by prefix
python3 list_tables.py --prefix dev_

# Search specific table
python3 list_tables.py --search dev_Dashboard

# Check all regions
python3 list_tables.py --all-regions

# Check specific region
python3 list_tables.py --region us-west-2
```

### Manual Credential Retrieval

If you need to manually get AWS SSO credentials:

```bash
python3 get_sso_credentials.py
```

This reads from `.env` and prints the credentials in JSON format.

## Examples

- `dev_users` → `local_users`
- `qa_products` → `local_products`
- `stg_orders` → `local_orders`

## How It Works

The project uses `.env` for configuration and AWS SSO for authentication:

1. **Configuration**: All settings stored in single `.env` file
2. **Authentication**: `get_sso_credentials.py` handles the SSO login flow
3. **Process**:
   - Reads AWS SSO settings from `.env`
   - Executes `aws sso login` and retrieves the access token
   - Calls `aws sso get-role-credentials` to get temporary credentials
   - Provides these credentials to the DynamoDB clients

**Benefits**:
- ✅ Single `.env` file for all configuration
- ✅ No manual credential management
- ✅ Credentials automatically fetched and refreshed
- ✅ Easy to set up and modify

## Configuration Reference

Your `.env` file should contain:

| Variable                  | Description               | Example                      |
| ------------------------- | ------------------------- | ---------------------------- |
| `AWS_SSO_PROFILE`         | Your AWS SSO profile name | `your-sso-profile-name`      |
| `AWS_ACCOUNT_ID`          | AWS account ID            | `YOUR_AWS_ACCOUNT_ID`        |
| `AWS_ROLE_NAME`           | IAM role name             | `YOUR_ROLE_NAME`             |
| `AWS_REGION`              | AWS region                | `your-aws-region`            |
| `LOCAL_DYNAMODB_ENDPOINT` | Local DynamoDB URL        | `http://localhost:8000` |
| `LOCAL_TABLE_PREFIX`      | Prefix for cloned tables  | `local_`                |
| `BATCH_SIZE`              | Batch size for operations | `25`                    |

## Troubleshooting

**Missing .env file?**
```bash
cp .env.template .env
# Then edit .env with your values
```

**SSO Login Issues?**
- Make sure AWS CLI is installed and configured
- Check your `.env` settings match your AWS SSO configuration
- Verify `AWS_SSO_PROFILE` exists in your `~/.aws/config`

**Table not found?** Search across regions:

```bash
python3 list_tables.py --search your_table_name
```

**Local DynamoDB not running?**
```bash
docker run -p 8000:8000 amazon/dynamodb-local
```

**Credentials expired?**
- The script will automatically prompt for re-authentication
- SSO tokens are cached and reused when valid
