import logging
from decimal import Decimal
import json
import aioboto3
from botocore.exceptions import ClientError
from typing import Dict, Any, Optional
import uuid
from datetime import datetime
from config.config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION

class DynamoDBManager:
    
    """
    Manages DynamoDB operations for a chat application using aioboto3.
    Handles users, sessions, and messages in a single table design.
    """
    
    _resource = None  # Shared resource across all method calls
    _table = None     # Cached table reference

    def __init__(self):
        """
        Initialize connection to AWS DynamoDB.
        Uses AWS credentials from environment variables.
        """      
        # Create session with credentials
        self.session = aioboto3.Session(
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_DEFAULT_REGION
        )
       
        # Local Setup
        """
        Initialize connection to local DynamoDB instance.
        Uses local endpoint and dummy credentials for development.
        """
        # self.session = aioboto3.Session()
        # self.dynamodb_config = {
        #     'endpoint_url': 'http://localhost:8000',  # Local DynamoDB endpoint
        #     'region_name': 'local',                   # Local region for development
        #     'aws_access_key_id': 'local',            # Dummy credentials
        #     'aws_secret_access_key': 'local'         # Dummy credentials
        # }


    async def get_table(self):
        """Helper method to get table resource, creating it only once"""
        if DynamoDBManager._resource is None:
            # Create the resource only once
            DynamoDBManager._resource = await self.session.resource('dynamodb').__aenter__()
            DynamoDBManager._table = await DynamoDBManager._resource.Table('codebase')
        return DynamoDBManager._table

    async def create_user(self, user_id: str) -> Dict:
        """Create a new user in the database if they don't already exist."""
        try:
            table = await self.get_table()
            # First check if user exists
            response = await table.get_item(
                Key={
                    'PK': f'USER#{user_id}',
                    'SK': 'PROFILE'
                }
            )
            # If user exists, return without creating
            if 'Item' in response:
                return {'success': True, 'user_id': user_id}

            user_name = user_id.replace('@', '_').replace('.', '_')
            item = {
                'PK': f'USER#{user_id}',
                'SK': 'PROFILE',
                'user_name': user_name,
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            await table.put_item(Item=item)
            return {'success': True, 'user_id': user_id}
        
        except ClientError as e:
            print(f"Error creating user: {e}")
            return {'success': False, 'error': str(e)}

    async def create_session(self, user_id: str, session_id: str) -> Dict:
        """Create a new session for a user."""
        # project_name = session_id.split('_', 1)[1]
        parts = session_id.split('_', 1)
        project_name = parts[1] if len(parts) > 1 else "Unknown"
        item = {
            'PK': f'USER#{user_id}',
            'SK': f'SESSION#{session_id}',
            'project_name': project_name,
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        try:
            table = await self.get_table()
            await table.put_item(Item=item)
            
            return {'success': True, 'session_id': session_id}
        
        except ClientError as e:
            print(f"Error creating session: {e}")
            return {'success': False, 'error': str(e)}

    async def get_user(self, user_id: str) -> Dict:
        """Retrieve a user's profile."""
        try:
            table = await self.get_table()
            response = await table.get_item(
                Key={
                    'PK': f'USER#{user_id}',
                    'SK': 'PROFILE'
                }
            )
            if 'Item' in response:
                item = response['Item']
                item['user_id'] = item['PK'].split('#')[1]
                return item
            return {}
        except ClientError as e:
            print(f"Error getting user: {e}")
            return {}

    async def get_user_sessions(self, user_id: str) -> list:
        """Get all sessions for a specific user."""
        session_result = []
        try:
            table = await self.get_table()
            response = await table.query(
                KeyConditionExpression='PK = :pk AND begins_with(SK, :sk)',
                ExpressionAttributeValues={
                    ':pk': f'USER#{user_id}',
                    ':sk': 'SESSION#'
                }
            )
            sessions = response.get('Items', [])
            
            # First sort the sessions based on created_at timestamp in descending order (newest first)
            sorted_sessions = sorted(sessions, key=lambda x: x.get('updated_at', ''), reverse=True)
            for session in sorted_sessions:
                session_data = {
                    "session_id":[],
                    "project_name":[]
                }
                session_data['session_id'] = (session['SK'].split('#')[1])
                session_data['project_name'] = (session['project_name'])
                session_result.append(session_data)
            return session_result
        
        except ClientError as e:
            print(f"Error getting sessions: {e}")
            return []
        
    async def rename_session(self, user_id: str, session_id: str, new_name: str):
        try:
            table = await self.get_table()
            await table.update_item(
                Key={
                    'PK': f'USER#{user_id}',
                    'SK': f'SESSION#{session_id}'
                },
                UpdateExpression='SET project_name = :new_name, updated_at = :timestamp',
                ExpressionAttributeValues={
                    ':new_name': new_name,
                    ':timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            )
            return True
        except:
            return False
        
    async def delete_session(self, user_id: str, session_id: str):
        try:
            table = await self.get_table()
            
            # First, get all messages in this session
            messages = await table.query(
                KeyConditionExpression='PK = :pk',
                ExpressionAttributeValues={
                    ':pk': f'USER#{user_id}#SESSION#{session_id}'
                }
            )

            # Delete all messages
            for message in messages.get('Items', []):
                await table.delete_item(
                    Key={
                        'PK': message['PK'],
                        'SK': message['SK']
                    }
                )

            # Delete the session
            await table.delete_item(
                Key={
                    'PK': f'USER#{user_id}',
                    'SK': f'SESSION#{session_id}'
                }
            )
            return True

        except:
            return False

    async def get_session_messages(self, user_id: str, session_id: str) -> list:
        """Get all messages in a specific session."""
        try:
            table = await self.get_table()
            response = await table.query(
                KeyConditionExpression='PK = :pk AND begins_with(SK, :sk)',
                ExpressionAttributeValues={
                    ':pk': f'USER#{user_id}#SESSION#{session_id}',
                    ':sk': 'MESSAGE#'
                }
            )
            messages = response.get('Items', [])
            # First sort the messages based on created_at timestamp in Ascending order (newest being the latest)
            sorted_messages = sorted(messages, key=lambda x: x.get('updated_at', ''), reverse=False)
            # Required keys 
            specific_keys = ['query', 'response', 'metrics']
            # Fetch the required keys and values
            result = [dict((k, sm[k]) for k in specific_keys) for sm in sorted_messages]
            
            return result
        
        except ClientError as e:
            print(f"Error getting messages: {e}")
            return []

    async def check_daily_message_limit(self, user_id: str, limit: int = 20) -> Dict:
        """
        Check if a user has reached their daily message limit.

        Args:
            user_id: The ID of the user to check.
            limit: Maximum number of messages allowed per day (default: 20).

        Returns:
            Dict containing limit status, message count, and notification flags.
        """
        try:
            table = await self.get_table()

            # Calculate the start of today as a formatted string to match how we store timestamps
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).strftime(
                '%Y-%m-%d %H:%M:%S')

            # Query all user sessions
            sessions_response = await table.query(
                KeyConditionExpression='PK = :pk AND begins_with(SK, :sk)',
                ExpressionAttributeValues={
                    ':pk': f'USER#{user_id}',
                    ':sk': 'SESSION#'
                }
            )

            sessions = sessions_response.get('Items', [])

            today_message_count = 0

            # Check messages in each session
            for session in sessions:
                session_id = session['SK'].split('#')[1]

                # Query messages created today
                messages_response = await table.query(
                    KeyConditionExpression='PK = :pk AND begins_with(SK, :sk)',
                    FilterExpression='updated_at >= :today',
                    ExpressionAttributeValues={
                        ':pk': f'USER#{user_id}#SESSION#{session_id}',
                        ':sk': 'MESSAGE#',
                        ':today': today_start  # Using formatted string timestamp for filtering
                    }
                )

                # today_message_count += len(messages_response.get('Items', []))
                if messages_response.get('Items'):
                    for item in messages_response.get('Items'):
                        if 'response' in item:  # Check if the item has a 'response' field
                            today_message_count += 1

            remaining = max(0, limit - today_message_count)
            logging.info("Remaining messages: %s", remaining)

            return {
                'success': True,
                'user_id': user_id,
                'limit_reached': today_message_count >= limit,
                'count': today_message_count,
                'limit': limit,
                'remaining': remaining,
                'notification_message': self._get_notification_message(remaining)
            }

        except ClientError as e:
            print(f"Error checking message limit: {e}")
            return {
                'success': False,
                'error': str(e),
                'limit_reached': True  # Fail safe: assume limit reached on error
            }

    def _get_notification_message(self, remaining: int) -> Optional[str]:
        """
        Get the appropriate notification message based on remaining messages.

        Args:
            remaining: Number of messages remaining for the day

        Returns:
            Notification message or None if no notification needed
        """
        if remaining == 5:
            return "You have 5 message remaining for today. Your daily limit is 5 messages."
        elif remaining == 0:
            return "You have reached your daily limit of 5 messages. Your limit will reset tomorrow."
        else:
            return None

    async def create_message(self, user_id: str, session_id: str, query: str, response: str, metrics: Dict) -> Dict:
        """Create a new message in a session if daily limit not exceeded."""
        # First check if user has reached their daily limit
        # reset = await self.reset_daily_message_count(user_id)
        limit_check = await self.check_daily_message_limit(user_id)

        if not limit_check['success']:
            return {'success': False, 'error': limit_check.get('error', 'Error checking message limit')}

        if limit_check['limit_reached']:
            return {
                'success': False,
                'error': 'Daily message limit reached',
                'limit_info': limit_check
            }

        # If limit not reached, proceed with creating the message
        # Convert all scores to Decimal
        for metric_values in metrics.values():
            score = metric_values['score']
            metric_values['score'] = Decimal(str(round(score,2)))

        message_id = str(uuid.uuid4())
        item = {
            'PK': f'USER#{user_id}#SESSION#{session_id}',
            'SK': f'MESSAGE#{message_id}',
            'query': query,
            'response': response,
            'metrics': metrics,
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        }

        try:
            table = await self.get_table()
            await table.put_item(Item=item)

            # Update session timestamp
            await table.update_item(
                Key={
                    'PK': f'USER#{user_id}',
                    'SK': f'SESSION#{session_id}'
                },
                UpdateExpression='SET updated_at = :timestamp',
                ExpressionAttributeValues={
                    ':timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            )

            # Check limits after creating the message to get updated counts
            updated_limit = await self.check_daily_message_limit(user_id)
            return {'success': True, 'limit_info': updated_limit}

        except ClientError as e:
            print(f"Error creating message: {e}")
            return {'success': False, 'error': str(e)}

    async def check_for_limit(self, user_id: str, session_id: str, query: str) -> Dict:
        """Create a new message in a session if daily limit not exceeded."""
        # First check if user has reached their daily limit
        # reset = await self.reset_daily_message_count(user_id)
        limit_check = await self.check_daily_message_limit(user_id)

        if not limit_check['success']:
            return {'success': False, 'error': limit_check.get('error', 'Error checking message limit'),
                    'notification': limit_check.get('notification_message', '')}

        if limit_check['limit_reached']:
            return {
                'success': False,
                'error': 'Daily message limit reached',
                'limit_info': limit_check
            }

        # If limit not reached, proceed with creating the message

        message_id = str(uuid.uuid4())
        item = {
            'PK': f'USER#{user_id}#SESSION#{session_id}',
            'SK': f'MESSAGE#{message_id}',
            'query': query,
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        }

        try:
            table = await self.get_table()
            await table.put_item(Item=item)

            # Update session timestamp
            await table.update_item(
                Key={
                    'PK': f'USER#{user_id}',
                    'SK': f'SESSION#{session_id}'
                },
                UpdateExpression='SET updated_at = :timestamp',
                ExpressionAttributeValues={
                    ':timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            )

            # Check limits after creating the message to get updated counts
            updated_limit = await self.check_daily_message_limit(user_id)
            return {'success': True, 'limit_info': updated_limit}

        except ClientError as e:
            print(f"Error creating message: {e}")
            return {'success': False, 'error': str(e)}

    async def get_remaining_daily_messages(self, user_id: str) -> int:
        limit_info = await self.check_daily_message_limit(user_id)
        return limit_info.get("remaining", 0)

    async def reset_daily_message_count(self, user_id: str) -> Dict:
        """
        Reset a user's daily message count by updating the timestamp on all messages sent today.
        This effectively makes them appear as if they were sent yesterday.

        Args:
            user_id: The ID of the user whose message count should be reset.

        Returns:
            Dict containing success status and count of messages reset.
        """
        try:
            table = await self.get_table()

            # Calculate today's start as a formatted string
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).strftime(
                '%Y-%m-%d %H:%M:%S')

            # Calculate yesterday's timestamp (for resetting messages)
            # Correct import of timedelta
            from datetime import timedelta
            yesterday = (datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) -
                         timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')

            # Query all user sessions
            sessions_response = await table.query(
                KeyConditionExpression='PK = :pk AND begins_with(SK, :sk)',
                ExpressionAttributeValues={
                    ':pk': f'USER#{user_id}',
                    ':sk': 'SESSION#'
                }
            )

            sessions = sessions_response.get('Items', [])
            reset_count = 0

            # Process each session
            for session in sessions:
                session_id = session['SK'].split('#')[1]

                # Query messages created today
                messages_response = await table.query(
                    KeyConditionExpression='PK = :pk AND begins_with(SK, :sk)',
                    FilterExpression='updated_at >= :today',
                    ExpressionAttributeValues={
                        ':pk': f'USER#{user_id}#SESSION#{session_id}',
                        ':sk': 'MESSAGE#',
                        ':today': today_start
                    }
                )

                today_messages = messages_response.get('Items', [])

                # Update each message's timestamp to yesterday
                for message in today_messages:
                    await table.update_item(
                        Key={
                            'PK': message['PK'],
                            'SK': message['SK']
                        },
                        UpdateExpression='SET updated_at = :yesterday',
                        ExpressionAttributeValues={
                            ':yesterday': yesterday
                        }
                    )
                    reset_count += 1

            return {
                'success': True,
                'reset_count': reset_count,
                'message': f"Successfully reset {reset_count} messages for user {user_id}"
            }

        except ClientError as e:
            print(f"Error resetting message count: {e}")
            return {
                'success': False,
                'error': str(e)
            }
