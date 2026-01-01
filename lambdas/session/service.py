"""Session service - business logic for session CRUD operations."""

from aws_lambda_powertools import Logger

from session.models import SessionCreateRequest
from shared.campaigns import get_opening_message, get_starting_location
from shared.db import DynamoDBClient
from shared.exceptions import ConflictError, NotFoundError
from shared.utils import generate_id, utc_now

logger = Logger()

MAX_SESSIONS_PER_USER = 10
MAX_MESSAGES_PER_SESSION = 50


class SessionService:
    """Service layer for session CRUD operations."""

    def __init__(self, db_client: DynamoDBClient) -> None:
        """Initialize session service.

        Args:
            db_client: DynamoDB client instance
        """
        self.db = db_client

    def create_session(self, user_id: str, request: SessionCreateRequest) -> dict:
        """Create a new game session.

        Args:
            user_id: The user's ID
            request: Session creation request

        Returns:
            The created session data

        Raises:
            NotFoundError: If character doesn't exist
            ConflictError: If user has reached session limit
        """
        # 1. Verify character exists and belongs to user
        character = self.db.get_item(
            pk=f"USER#{user_id}",
            sk=f"CHAR#{request.character_id}",
        )
        if not character:
            raise NotFoundError("Character", request.character_id)

        # 2. Count existing sessions (enforce limit)
        existing_sessions = self.db.query_by_pk(
            pk=f"USER#{user_id}",
            sk_prefix="SESS#",
        )
        if len(existing_sessions) >= MAX_SESSIONS_PER_USER:
            raise ConflictError(
                f"Maximum {MAX_SESSIONS_PER_USER} sessions allowed per user"
            )

        # 3. Get starting location and create opening message
        campaign = request.campaign_setting.value
        location = get_starting_location(campaign)
        character_name = character.get("name", "Adventurer")
        opening_message = get_opening_message(campaign, character_name)

        # 4. Create session
        session_id = generate_id()
        now = utc_now()

        session = {
            "session_id": session_id,
            "character_id": request.character_id,
            "campaign_setting": campaign,
            "current_location": location,
            "world_state": {},
            "message_history": [
                {
                    "role": "dm",
                    "content": opening_message,
                    "timestamp": now,
                }
            ],
            "created_at": now,
            "updated_at": None,
        }

        self.db.put_item(
            pk=f"USER#{user_id}",
            sk=f"SESS#{session_id}",
            data=session,
        )

        logger.info(
            "Session created",
            extra={
                "user_id": user_id,
                "session_id": session_id,
                "character_id": request.character_id,
                "campaign_setting": campaign,
            },
        )

        return session

    def list_sessions(
        self,
        user_id: str,
        character_id: str | None = None,
        limit: int = 20,
    ) -> list[dict]:
        """List sessions with character names joined.

        Args:
            user_id: The user's ID
            character_id: Optional filter by character
            limit: Maximum number of sessions to return

        Returns:
            List of session summaries with character names
        """
        # Query all sessions for user
        sessions = self.db.query_by_pk(
            pk=f"USER#{user_id}",
            sk_prefix="SESS#",
            limit=limit if not character_id else 100,  # Get more if filtering
        )

        # Filter by character_id if provided
        if character_id:
            sessions = [s for s in sessions if s.get("character_id") == character_id]
            sessions = sessions[:limit]

        if not sessions:
            return []

        # Get unique character IDs
        char_ids = {s["character_id"] for s in sessions}

        # Batch get character names
        char_names: dict[str, str] = {}
        for char_id in char_ids:
            char = self.db.get_item(
                pk=f"USER#{user_id}",
                sk=f"CHAR#{char_id}",
            )
            if char:
                char_names[char_id] = char.get("name", "Unknown")
            else:
                char_names[char_id] = "Deleted Character"

        # Return summaries with character names
        return [
            {
                "session_id": s["session_id"],
                "character_id": s["character_id"],
                "character_name": char_names.get(s["character_id"], "Unknown"),
                "campaign_setting": s["campaign_setting"],
                "current_location": s["current_location"],
                "created_at": s["created_at"],
                "updated_at": s.get("updated_at"),
            }
            for s in sessions
        ]

    def get_session(self, user_id: str, session_id: str) -> dict:
        """Get full session details.

        Args:
            user_id: The user's ID
            session_id: The session's ID

        Returns:
            Full session data

        Raises:
            NotFoundError: If session doesn't exist
        """
        item = self.db.get_item_or_raise(
            pk=f"USER#{user_id}",
            sk=f"SESS#{session_id}",
            resource_type="Session",
            resource_id=session_id,
        )
        # Remove DynamoDB keys from response
        return {k: v for k, v in item.items() if k not in ("PK", "SK")}

    def get_message_history(
        self,
        user_id: str,
        session_id: str,
        limit: int = 20,
        before: str | None = None,
    ) -> dict:
        """Get paginated message history.

        Args:
            user_id: The user's ID
            session_id: The session's ID
            limit: Maximum messages to return
            before: Timestamp cursor for pagination

        Returns:
            Message history with pagination info

        Raises:
            NotFoundError: If session doesn't exist
        """
        session = self.get_session(user_id, session_id)
        messages = session.get("message_history", [])

        # Messages are stored oldest first, so reverse for newest first
        messages = list(reversed(messages))

        # Filter by cursor if provided
        if before:
            messages = [m for m in messages if m["timestamp"] < before]

        # Apply limit + 1 to check if there are more
        has_more = len(messages) > limit
        messages = messages[:limit]

        # Get next cursor (timestamp of last message)
        next_cursor = messages[-1]["timestamp"] if has_more and messages else None

        return {
            "messages": messages,
            "has_more": has_more,
            "next_cursor": next_cursor,
        }

    def delete_session(self, user_id: str, session_id: str) -> None:
        """Delete a session.

        Args:
            user_id: The user's ID
            session_id: The session's ID

        Raises:
            NotFoundError: If session doesn't exist
        """
        # Verify session exists first
        self.get_session(user_id, session_id)

        self.db.delete_item(
            pk=f"USER#{user_id}",
            sk=f"SESS#{session_id}",
        )

        logger.info(
            "Session deleted",
            extra={
                "user_id": user_id,
                "session_id": session_id,
            },
        )
