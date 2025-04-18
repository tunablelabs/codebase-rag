import logging
from decimal import Decimal
import json
import aioboto3
from botocore.exceptions import ClientError
from typing import Dict, Any, Optional
import uuid
from datetime import datetime
from config.config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION, USE_LOCAL_DYNAMODB, DYNAMODB_LOCAL_ENDPOINT
from config.logging_config import info, warning, debug, error


class DynamoDBManager:
    """
    Manages DynamoDB operations for a chat application using aioboto3.
    Handles users, sessions, and messages in a single table design.
    """

    _resource = None  # Shared resource across all method calls
    _table = None  # Cached table reference

    def __init__(self):
        """
        Initialize connection to AWS DynamoDB.
        Connection type (local or production) is determined by environment variables.
        """
        info("Initializing DynamoDBManager")
        # Check if we should use local or production mode
        use_local = USE_LOCAL_DYNAMODB.lower() == 'true'
        
        if use_local:
            info("Using local DynamoDB instance")
            self.session = aioboto3.Session()
            self.dynamodb_config = {
                'endpoint_url': DYNAMODB_LOCAL_ENDPOINT,
                'region_name': 'us-east-1',
                'aws_access_key_id': 'local',
                'aws_secret_access_key': 'local'
            }
        else:
            info("Using production AWS DynamoDB")
            self.session = aioboto3.Session(
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                region_name=AWS_DEFAULT_REGION
            )
            self.dynamodb_config = {} 
            
        info("DynamoDB session created")

    async def get_table(self):
        """Helper method to get table resource, creating it only once"""
        if DynamoDBManager._resource is None:
            # Create the resource only once
            info("Creating new DynamoDB resource connection")
            DynamoDBManager._resource = await self.session.resource('dynamodb', **self.dynamodb_config).__aenter__()
            DynamoDBManager._table = await DynamoDBManager._resource.Table('codebase')
        return DynamoDBManager._table

    async def create_user(self, user_id: str) -> Dict:
        """Create a new user in the database if they don't already exist."""
        info(f"Creating user with ID: {user_id}")
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
                info(f"User {user_id} already exists")
                return {'success': True, 'user_id': user_id}

            user_name = user_id.replace('@', '_').replace('.', '_')
            item = {
                'PK': f'USER#{user_id}',
                'SK': 'PROFILE',
                'user_name': user_name,
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            info(f"Creating new user {user_id} in database")
            await table.put_item(Item=item)
            info(f"User {user_id} created successfully")
            return {'success': True, 'user_id': user_id}

        except ClientError as e:
            error(f"Error creating user {user_id}: {e}")
            return {'success': False, 'error': str(e)}

    async def create_session(self, user_id: str, session_id: str) -> Dict:
        """Create a new session for a user."""
        info(f"Creating session {session_id} for user {user_id}")
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
            info(f"Session {session_id} created successfully for user {user_id}")

            return {'success': True, 'session_id': session_id}

        except ClientError as e:
            error(f"Error creating session {session_id} for user {user_id}: {e}")
            return {'success': False, 'error': str(e)}

    async def get_user(self, user_id: str) -> Dict:
        """Retrieve a user's profile."""
        info(f"Getting user profile for user {user_id}")
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
                info(f"User {user_id} profile retrieved successfully")
                return item
            info(f"User {user_id} not found")
            return {}
        except ClientError as e:
            error(f"Error getting user {user_id}: {e}")
            return {}

    async def get_user_sessions(self, user_id: str) -> list:
        """Get all sessions for a specific user."""
        info(f"Getting sessions for user {user_id}")
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
                    "session_id": [],
                    "project_name": []
                }
                session_data['session_id'] = (session['SK'].split('#')[1])
                session_data['project_name'] = (session['project_name'])
                session_result.append(session_data)
            info(f"Retrieved {len(session_result)} sessions for user {user_id}")
            return session_result

        except ClientError as e:
            error(f"Error getting sessions for user {user_id}: {e}")
            return []

    async def rename_session(self, user_id: str, session_id: str, new_name: str):
        info(f"Renaming session {session_id} to '{new_name}' for user {user_id}")
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
            info(f"Session {session_id} renamed successfully to '{new_name}'")
            return True
        except Exception as e:
            error(f"Error renaming session {session_id} for user {user_id}: {e}")
            return False

    async def delete_session(self, user_id: str, session_id: str):
        info(f"Deleting session {session_id} for user {user_id}")
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
            message_count = len(messages.get('Items', []))
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
            info(f"Session {session_id} and {message_count} messages deleted successfully")
            return True

        except Exception as e:
            error(f"Error deleting session {session_id}: {e}")
            return False

    async def get_session_messages(self, user_id: str, session_id: str) -> list:
        """Get all messages in a specific session."""
        info(f"Getting messages for session {session_id}, user {user_id}")
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

            specific_keys = ['query', 'response', 'metrics']

            # Fetch the required keys and values
            result = [{k: sm.get(k, None) for k in specific_keys} for sm in sorted_messages]
            info(f"Retrieved {len(result)} messages from session {session_id}")
            return result

        except ClientError as e:
            error(f"Error getting messages for session {session_id}: {e}")
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
        info(f"Checking daily message limit for user {user_id}")
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
            info(f"User {user_id} has used {today_message_count}/{limit} messages today. Remaining: {remaining}")

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
            error(f"Error checking message limit for user {user_id}: {e}")
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
            return "You have reached your daily limit of 20 messages. Your limit will reset tomorrow."
        else:
            return None

    async def create_message(self, user_id: str, session_id: str, query: str, response: str, metrics: Dict) -> Dict:
        """Create a new message in a session if daily limit not exceeded."""
        info(f"Creating message in session {session_id} for user {user_id}")
        # First check if user has reached their daily limit
        # reset = await self.reset_daily_message_count(user_id)
        limit_check = await self.check_daily_message_limit(user_id)

        if not limit_check['success']:
            warning(f"Failed to check message limit for user {user_id}")
            return {'success': False, 'error': limit_check.get('error', 'Error checking message limit')}

        if limit_check['limit_reached']:
            warning(f"Daily message limit reached for user {user_id}")
            return {
                'success': False,
                'error': 'Daily message limit reached',
                'limit_info': limit_check
            }

        # If limit not reached, proceed with creating the message
        # Convert all scores to Decimal
        for metric_values in metrics.values():
            score = metric_values['score']
            metric_values['score'] = Decimal(str(round(score, 2)))

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
            info(f"Message created successfully. User has {updated_limit.get('remaining')} messages remaining today")
            return {'success': True, 'limit_info': updated_limit}

        except ClientError as e:
            error(f"Error creating message in session {session_id}: {e}")
            return {'success': False, 'error': str(e)}

    async def check_for_limit(self, user_id: str, session_id: str, query: str) -> Dict:
        """Create a new message in a session if daily limit not exceeded."""
        info(f"Checking limits for user {user_id} in session {session_id}")
        # First check if user has reached their daily limit
        # reset = await self.reset_daily_message_count(user_id)
        limit_check = await self.check_daily_message_limit(user_id)

        if not limit_check['success']:
            warning(f"Failed to check message limit for user {user_id}")
            return {'success': False, 'error': limit_check.get('error', 'Error checking message limit'),
                    'notification': limit_check.get('notification_message', '')}

        if limit_check['limit_reached']:
            warning(f"Daily message limit reached for user {user_id}")
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
            info(f"Limit check passed. User has {updated_limit.get('remaining')} messages remaining today")
            return {'success': True, 'limit_info': updated_limit}

        except ClientError as e:
            error(f"Error during limit check for user {user_id}: {e}")
            return {'success': False, 'error': str(e)}

    async def get_remaining_daily_messages(self, user_id: str) -> int:
        """Get number of remaining messages for a user."""
        info(f"Getting remaining daily messages for user {user_id}")
        limit_info = await self.check_daily_message_limit(user_id)
        remaining = limit_info.get("remaining", 0)
        info(f"User {user_id} has {remaining} messages remaining today")
        return remaining

    async def reset_daily_message_count(self, user_id: str) -> Dict:
        """
        Reset a user's daily message count by updating the timestamp on all messages sent today.
        This effectively makes them appear as if they were sent yesterday.

        Args:
            user_id: The ID of the user whose message count should be reset.

        Returns:
            Dict containing success status and count of messages reset.
        """
        info(f"Resetting daily message count for user {user_id}")
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

            info(f"Successfully reset {reset_count} messages for user {user_id}")
            return {
                'success': True,
                'reset_count': reset_count,
                'message': f"Successfully reset {reset_count} messages for user {user_id}"
            }

        except ClientError as e:
            error(f"Error resetting message count for user {user_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
            
    async def get_session_stats(self, user_id: str, session_id: str) -> Dict:
        """
        Get repository statistics for a session if they exist in DB.
        
        Args:
            user_id: The ID of the user.
            session_id: The ID of the session.
            
        Returns:
            Dict with stats or None if not found.
        """
        info(f"Checking for existing stats in DB for session {session_id}, user {user_id}")
        try:
            table = await self.get_table()
            response = await table.get_item(
                Key={
                    'PK': f'USER#{user_id}',
                    'SK': f'SESSION#{session_id}'
                }
            )
            
            session_item = response.get('Item', {})
            
            if 'repo_stats' in session_item:
                info(f"Found existing stats for session {session_id}")
                return session_item['repo_stats']
            else:
                info(f"No stats found in DB for session {session_id}")
                return None
                
        except ClientError as e:
            error(f"Error checking stats for session {session_id}: {e}")
            return None
        
        
    async def update_session_stats(self, user_id: str, session_id: str, stats: Dict) -> bool:
        """
        Update a session with repository statistics.
        
        Args:
            user_id: The ID of the user.
            session_id: The ID of the session.
            stats: Dictionary containing repository statistics.
            
        Returns:
            bool: True if the update was successful, False otherwise.
        """
        info(f"Updating stats in DB for session {session_id}, user {user_id}")
        try:
            table = await self.get_table()
            await table.update_item(
                Key={
                    'PK': f'USER#{user_id}',
                    'SK': f'SESSION#{session_id}'
                },
                UpdateExpression='SET repo_stats = :stats, updated_at = :timestamp',
                ExpressionAttributeValues={
                    ':stats': stats,
                    ':timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            )
            info(f"Updated stats in DB for session {session_id} successfully")
            return True
        except Exception as e:
            error(f"Error updating stats for session {session_id}: {e}")
            return False