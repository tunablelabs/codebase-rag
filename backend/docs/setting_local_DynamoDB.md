# Setting Up Local DynamoDB with Docker Compose

This guide provides step-by-step instructions for setting up a local DynamoDB instance using Docker Compose with persistent data storage.

## Prerequisites

- Docker installed ([Install Docker](https://docs.docker.com/get-docker/))
- Docker Compose installed ([Install Docker Compose](https://docs.docker.com/compose/install/))
- Basic knowledge of terminal/command line

## Step 1: Create a Project Directory

```bash
mkdir dynamodb-local
cd dynamodb-local
```

## Step 2: Create the Docker Compose Configuration

Create a file named `docker-compose.yml` in the project directory:

```bash
touch docker-compose.yml
```

Open the file in your preferred text editor and add the following configuration:

```yaml
version: '3.8'
services:
  dynamodb-local:
    image: amazon/dynamodb-local
    container_name: dynamodb-local
    ports:
      - "7000:8000"
    volumes:
      - dynamodb-data:/home/dynamodblocal
    command: "-jar DynamoDBLocal.jar -sharedDb"
    environment:
      - AWS_ACCESS_KEY_ID=local
      - AWS_SECRET_ACCESS_KEY=local
      - AWS_REGION=us-east-1

volumes:
  dynamodb-data:
```

This configuration:
- Uses the official Amazon DynamoDB Local image
- Maps port 7000 to access DynamoDB
- Creates a persistent volume for data storage
- Uses the `-sharedDb` option for a single database file
- Specifies a custom network for container communication

## Step 3: Start DynamoDB Local

From the project directory, run:

```bash
docker-compose up -d
```

This starts the container in detached mode. To view the logs:

```bash
docker-compose logs -f
```

Press `Ctrl+C` to exit the logs view.

## Step 4: Verify the Installation

### Method 1: Using Docker

Check if the container is running:

```bash
docker ps
```

You should see your `dynamodb-local` container in the list.

After creating DynamoDB, You could use NoSQL Workbench for DynamoDB to manage or view DynamoDB. Navigate to end of the document for more details.

### Method 2: Using AWS CLI

If you have AWS CLI installed, you can verify by listing tables:

```bash
aws dynamodb list-tables --endpoint-url http://localhost:7000
```

If you don't have AWS credentials configured, you can use:

```bash
aws dynamodb list-tables --endpoint-url http://localhost:7000 --region local --no-sign-request
```

## Step 5: Create a Test Table

Create a test table to verify functionality:

```bash
aws dynamodb create-table \
    --table-name TestTable \
    --attribute-definitions AttributeName=id,AttributeType=S \
    --key-schema AttributeName=id,KeyType=HASH \
    --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
    --endpoint-url http://localhost:7000 \
    --region local \
    --no-sign-request
```

Verify the table was created:

```bash
aws dynamodb list-tables --endpoint-url http://localhost:7000 --region local --no-sign-request
```

## Step 6: Test Data Persistence

1. Add an item to the table:

```bash
aws dynamodb put-item \
    --table-name TestTable \
    --item '{"id": {"S": "1"}, "name": {"S": "Test Item"}}' \
    --endpoint-url http://localhost:7000 \
    --region local \
    --no-sign-request
```

2. Stop and remove the container:

```bash
docker-compose down
```

3. Start the container again:

```bash
docker-compose up -d
```

4. Check if the data is still there:

```bash
aws dynamodb scan \
    --table-name TestTable \
    --endpoint-url http://localhost:7000 \
    --region local \
    --no-sign-request
```

You should see your test item, confirming that the data persists even when the container is removed.

## Step 7: Managing Your Local DynamoDB

Common commands for managing your DynamoDB container:

- Start containers: `docker-compose up -d`
- Stop containers: `docker-compose down`
- View container logs: `docker-compose logs -f`
- Restart containers: `docker-compose restart`
- Check container status: `docker-compose ps`

## Step 8: Connecting from Your Application

Update your `.env` file to use the local DynamoDB:

```
USE_LOCAL_DYNAMODB=true
DYNAMODB_LOCAL_ENDPOINT=http://localhost:7000
```

Your Python application should now connect to the local DynamoDB instance using the DynamoDBManager class you've implemented.

## Step 9: Inspecting the Persistent Volume

To verify where Docker is storing your data:

```bash
docker volume inspect dynamodb-data
```

This will show you the path on your host where the data is being stored.

## Troubleshooting

- **Port conflict**: If port 8000 is already in use, change the port mapping in the docker-compose.yml file (e.g., "7000:8000").
- **Connection refused**: Make sure the container is running (`docker ps`).
- **Cannot connect from application**: If your app is running in another container, make sure they're on the same network.
- **Access denied**: When using AWS CLI, try the `--no-sign-request` flag.

## Conclusion

You now have a local DynamoDB instance running with persistent data storage. This setup is ideal for development and testing without incurring AWS costs or requiring internet connectivity.

# Installing NoSQL Workbench for DynamoDB

This guide provides step-by-step instructions for downloading, installing, and configuring NoSQL Workbench for DynamoDB to work with your local DynamoDB instance.

## What is NoSQL Workbench?

NoSQL Workbench is an AWS visual development tool that provides:
- Data modeling
- Data visualization
- Query development capabilities for DynamoDB

## Step 1: Download NoSQL Workbench

1. Visit the official AWS NoSQL Workbench download page:
   [https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/workbench.settingup.html](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/workbench.settingup.html)

2. Download the appropriate version for your operating system:
   - Windows: `.msi` installer file
   - macOS: `.dmg` file
   - Linux: `.AppImage` file

## Step 2: Install NoSQL Workbench

### Windows Installation
1. Locate the downloaded `.msi` file
2. Double-click the file to start the installation wizard
3. Follow the on-screen instructions
4. Click "Finish" when installation completes

### macOS Installation
1. Locate the downloaded `.dmg` file
2. Double-click to mount the disk image
3. Drag the NoSQL Workbench icon to the Applications folder
4. (First launch) Right-click on the application in the Applications folder and select "Open" to bypass Gatekeeper security

### Linux Installation
1. Make the AppImage executable:
   ```bash
   chmod +x ~/Downloads/NoSQL-Workbench-linux-x86_64.AppImage
   ```
   (Adjust the path if necessary)

2. Run the AppImage:
   ```bash
   ~/Downloads/NoSQL-Workbench-linux-x86_64.AppImage
   ```

3. (Optional) Move to a system location for easier access:
   ```bash
   mkdir -p ~/.local/bin
   cp ~/Downloads/NoSQL-Workbench-linux-x86_64.AppImage ~/.local/bin/nosql-workbench
   chmod +x ~/.local/bin/nosql-workbench
   ```

## Step 3: Launch NoSQL Workbench

1. Open NoSQL Workbench from:
   - Windows: Start menu
   - macOS: Applications folder
   - Linux: Run the AppImage or use the command if you moved it to ~/.local/bin

2. You should see the welcome screen with three main components:
   - Data Modeler
   - Visualization
   - Operation Builder

## Step 4: Connect to Your Local DynamoDB Instance

1. Click on "Operation Builder" in the left navigation panel
2. Click "Add Connection"
3. Select "DynamoDB Local" from the connection options

4. Enter the connection details:
   - Connection name: Any name (e.g., "Local Development")
   - Port: 8000 (or the custom port you configured in Docker, like 7000)
   - Uncheck "Use secure connection (HTTPS)" for local development

5. Click "Connect"

## Step 5: Working with Your Local Tables

Once connected, you can:

1. View existing tables
2. Create new tables using the interface
3. Add sample data
4. Design and execute queries
5. Export and import data

### Creating a New Table
1. In Operation Builder, click "Create table"
2. Define table name, partition key, and sort key (if needed)
3. Configure additional settings as needed
4. Click "Create"

### Running Queries
1. Select a table
2. Click "PartiQL editor" or "Operation builder"
3. Design your query
4. Execute and view results

# Creating the DynamoDB 'codebase' Table

This document outlines different methods to create a DynamoDB table named "codebase" with the schema that matches your DynamoDBManager implementation.

## Table Schema

- **Table Name**: `codebase`
- **Partition Key**: `PK` (String)
- **Sort Key**: `SK` (String)
- **Billing Mode**: Pay-per-request (On-demand)

## Option 1: Using AWS CLI

If you have the AWS Command Line Interface (CLI) installed, you can create the table with the following commands:

### For Local DynamoDB

```bash
aws dynamodb create-table \
    --table-name codebase \
    --attribute-definitions \
        AttributeName=PK,AttributeType=S \
        AttributeName=SK,AttributeType=S \
    --key-schema \
        AttributeName=PK,KeyType=HASH \
        AttributeName=SK,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST \
    --endpoint-url http://localhost:7000
```

### For AWS DynamoDB

```bash
aws dynamodb create-table \
    --table-name codebase \
    --attribute-definitions \
        AttributeName=PK,AttributeType=S \
        AttributeName=SK,AttributeType=S \
    --key-schema \
        AttributeName=PK,KeyType=HASH \
        AttributeName=SK,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST \
    --region us-east-1
```

Replace `us-east-1` with your preferred AWS region if different.

## Option 2: Using Python Code

You can create the table programmatically using Python and aioboto3 (which your application already uses).

```python
import aioboto3
from config.config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION, USE_LOCAL_DYNAMODB, DYNAMODB_LOCAL_ENDPOINT
from config.logging_config import info, warning, debug, error

async def create_codebase_table():
    """
    Creates the 'codebase' DynamoDB table with the appropriate schema.
    Uses either local DynamoDB or AWS DynamoDB based on configuration.
    """
    info("Creating codebase DynamoDB table")
    
    # Check if we should use local or production mode
    use_local = USE_LOCAL_DYNAMODB.lower() == 'true'
    
    # Configure session and connection parameters
    if use_local:
        info("Using local DynamoDB instance")
        session = aioboto3.Session()
        dynamodb_config = {
            'endpoint_url': DYNAMODB_LOCAL_ENDPOINT,
            'region_name': 'us-east-1',
            'aws_access_key_id': 'local',
            'aws_secret_access_key': 'local'
        }
    else:
        info("Using production AWS DynamoDB")
        session = aioboto3.Session(
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_DEFAULT_REGION
        )
        dynamodb_config = {
            'region_name': AWS_DEFAULT_REGION
        }
    
    try:
        # Create DynamoDB client with the appropriate configuration
        async with session.client('dynamodb', **dynamodb_config) as dynamodb:
            # Define table schema
            table_definition = {
                'TableName': 'codebase',
                'KeySchema': [
                    {'AttributeName': 'PK', 'KeyType': 'HASH'},  # Partition key
                    {'AttributeName': 'SK', 'KeyType': 'RANGE'}  # Sort key
                ],
                'AttributeDefinitions': [
                    {'AttributeName': 'PK', 'AttributeType': 'S'},  # String
                    {'AttributeName': 'SK', 'AttributeType': 'S'}   # String
                ],
                'BillingMode': 'PAY_PER_REQUEST'  # On-demand capacity mode
            }
            
            # Create the table
            response = await dynamodb.create_table(**table_definition)
            info(f"Table creation initiated: {response['TableDescription']['TableStatus']}")
            
            # Wait for the table to be created
            info("Waiting for table to become active...")
            waiter = dynamodb.get_waiter('table_exists')
            await waiter.wait(TableName='codebase')
            
            info("Table 'codebase' created successfully!")
            return True
            
    except Exception as e:
        error(f"Error creating DynamoDB table: {e}")
        return False

# For running the function directly if this script is executed
if __name__ == "__main__":
    import asyncio
    asyncio.run(create_codebase_table())
```

Save this code to a file (e.g., `create_table.py`) and run it with `python create_table.py`.

## Option 3: Using AWS Management Console

If you prefer a visual interface, you can create the table using the AWS Management Console:

1. Go to https://console.aws.amazon.com/dynamodb/
2. Sign in to your AWS account
3. Click "Create table"
4. Enter "codebase" as the table name
5. Set "PK" as the partition key (type: String)
6. Check "Add sort key" and set "SK" as the sort key (type: String)
7. Under "Table settings", select "On-demand" for read/write capacity
8. Keep the default settings for the other options
9. Click "Create table"

## Option 4: For Local DynamoDB Development

### Using NoSQL Workbench

1. Download and install [NoSQL Workbench](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/workbench.html)
2. Open NoSQL Workbench and connect to your local DynamoDB instance
3. Use the "Data modeler" to create your table schema
4. Deploy the model to your local DynamoDB instance

## Verifying Table Creation

To verify that your table was created successfully:

### For Local DynamoDB:

```bash
aws dynamodb list-tables --endpoint-url http://localhost:8000
```

### For AWS DynamoDB:

```bash
aws dynamodb list-tables --region us-east-1
```