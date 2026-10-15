import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class Conversation:
    id: int
    title: str
    channel: str
    product_id: str | None
    marketplace: str | None
    language: str
    created_at: str
    updated_at: str


@dataclass
class Message:
    id: int
    conversation_id: int
    role: str
    content: str
    created_at: str


class ConversationStore:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    product_id TEXT,
                    marketplace TEXT,
                    language TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(conversation_id) REFERENCES conversations(id)
                )
                """
            )

    def create_conversation(
        self,
        *,
        title: str,
        channel: str,
        product_id: str | None,
        marketplace: str | None,
        language: str,
    ) -> Conversation:
        now = _now_iso()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO conversations (title, channel, product_id, marketplace, language, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (title, channel, product_id, marketplace, language, now, now),
            )
            conversation_id = cursor.lastrowid
        return self.get_conversation(conversation_id)

    def list_conversations(self) -> list[Conversation]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, title, channel, product_id, marketplace, language, created_at, updated_at
                FROM conversations
                ORDER BY updated_at DESC, id DESC
                """
            ).fetchall()
        return [_row_to_conversation(row) for row in rows]

    def get_conversation(self, conversation_id: int) -> Conversation:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, title, channel, product_id, marketplace, language, created_at, updated_at
                FROM conversations
                WHERE id = ?
                """,
                (conversation_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"Conversation {conversation_id} not found")
        return _row_to_conversation(row)

    def add_message(self, *, conversation_id: int, role: str, content: str) -> Message:
        now = _now_iso()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO messages (conversation_id, role, content, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (conversation_id, role, content, now),
            )
            conn.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (now, conversation_id),
            )
            message_id = cursor.lastrowid
        return self.get_message(message_id)

    def get_message(self, message_id: int) -> Message:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, conversation_id, role, content, created_at
                FROM messages
                WHERE id = ?
                """,
                (message_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"Message {message_id} not found")
        return _row_to_message(row)

    def list_messages(self, conversation_id: int, limit: int | None = None) -> list[Message]:
        query = (
            "SELECT id, conversation_id, role, content, created_at "
            "FROM messages WHERE conversation_id = ? ORDER BY id ASC"
        )
        params: tuple = (conversation_id,)
        if limit is not None:
            query = (
                "SELECT * FROM ("
                "SELECT id, conversation_id, role, content, created_at "
                "FROM messages WHERE conversation_id = ? ORDER BY id DESC LIMIT ?"
                ") ORDER BY id ASC"
            )
            params = (conversation_id, limit)

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [_row_to_message(row) for row in rows]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_conversation(row: sqlite3.Row) -> Conversation:
    return Conversation(
        id=row["id"],
        title=row["title"],
        channel=row["channel"],
        product_id=row["product_id"],
        marketplace=row["marketplace"],
        language=row["language"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _row_to_message(row: sqlite3.Row) -> Message:
    return Message(
        id=row["id"],
        conversation_id=row["conversation_id"],
        role=row["role"],
        content=row["content"],
        created_at=row["created_at"],
    )
