# DynamoDB Table Cloner

Clone DynamoDB tables from cloud to local DynamoDB with table discovery tools.

## Features

- Clone table schema and data from cloud to local DynamoDB
- Auto-rename tables: `dev_users` → `local_users`
- Discover tables across AWS regions
- Batch operations with progress tracking

## Setup

1. **Start Local DynamoDB**

   ```bash
   docker run -p 8000:8000 amazon/dynamodb-local
   ```

2. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Credentials** - Update `credentials.json`:

```json
{
  "roleCredentials": {
    "accessKeyId": "YOUR_ACCESS_KEY_ID",
    "secretAccessKey": "YOUR_SECRET_ACCESS_KEY",
    "sessionToken": "YOUR_SESSION_TOKEN"
  }
}
```

1. **Configure Region** - Update `config.json`:

```json
{
  "aws_region": "ap-northeast-1"
}
```

## Usage

### Activate Virtual Env

```bash
source .venv/bin/activate
```

### Clone Tables

```bash
# Clone a table
python table_cloner.py dev_Dashboard

# Use custom credentials
python table_cloner.py dev_users --credentials my_creds.json
```

### Discover Tables

```bash
# List all tables
python list_tables.py

# Filter by prefix
python list_tables.py --prefix dev_

# Search specific table
python list_tables.py --search dev_Dashboard

# Check all regions
python list_tables.py --all-regions
```

## Examples

- `dev_users` → `local_users`
- `qa_products` → `local_products`
- `stg_orders` → `local_orders`

## Troubleshooting

**Table not found?** Check your region:

```bash
python list_tables.py --search your_table_name
```
