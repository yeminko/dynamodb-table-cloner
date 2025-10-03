Implement a python program that clones a table from cloud dynamodb to local dynamodb.

- Make sure not to accidentally delete and modify the cloud dynamodb tables.
- Local dynamodb is running on localhost:8000
- The program should take the source table name for example "dev_users" and auto create the target table name for example "local_users"
- All local tables should be prefixed with `local\_`
- The program should have a json file to load the aws credentials and region
- In the json file, user will provide the following data:

```json
{
  "roleCredentials": {
    "accessKeyId": "YOUR_ACCESS_KEY_ID",
    "secretAccessKey": "YOUR_SECRET_ACCESS_KEY",
    "sessionToken": "YOUR_SESSION_TOKEN"
  }
}
```

- Load the credentials from the json file and use them to connect to the cloud dynamodb
- And then clone the table to local dynamodb
