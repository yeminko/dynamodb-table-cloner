# DynamoDB Table Cloner

Clone DynamoDB tables from cloud to local DynamoDB with AWS SSO authentication.

## Features

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

### Test Your Setup is Correct

Run the setup test script to verify your configuration. This will check for AWS credentials, local DynamoDB connectivity, and other prerequisites:

```bash
python test_setup.py
```

### Clone Tables

Clone tables by name. This will clone both schema and data, renaming the table with the specified prefix in `.env`:

```bash
# Clone a table
python table_cloner.py dev_users

# Clone a table with custom table name
python table_cloner.py dev_users --target-table my_users

# Clone multiple tables with a prefix
# This will clone all tables starting with 'dev_' from configured region (.env AWS_REGION)
python table_cloner.py --prefix dev_

# Clone all tables from configured region (.env AWS_REGION)
python table_cloner.py --all
```

#### Example

- If your `LOCAL_TABLE_PREFIX` is `local_`, then `dev_users` will be cloned to `local_users`.

- If the table name does not start with any of the environment prefixes (`dev_`, `qa_`, `stg_`, `test_`), it will be cloned by prepending the local prefix to the original name (e.g., `users` → `local_users`).

### Discover Tables

Discover tables in your AWS account. By default, it lists tables in the region specified in `.env`, but you can filter by prefix, search for specific tables, or check across all regions:

```bash
# List all tables in configured region (uses AWS_REGION from .env)
python list_tables.py

# Filter by prefix
python list_tables.py --prefix dev_

# Search specific table
python list_tables.py --search dev_Dashboard

# Check all regions
python list_tables.py --all-regions

# Check specific region
python list_tables.py --region us-west-2
```

### Credential Retrieval

If you need to get AWS SSO credentials:

```bash
python get_sso_credentials.py
```

This will print the credentials as JSON.

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
python list_tables.py --search your_table_name
```

**Local DynamoDB not running?**

```bash
docker run -p 8000:8000 amazon/dynamodb-local
```

**Credentials expired?**

- The script will automatically prompt for re-authentication
- SSO tokens are cached and reused when valid
