import sqlite3
import json
from a2a.server.tasks import TaskStore
from a2a.types import Task

class DBTaskStore(TaskStore):
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn = None

    def connect(self):
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._create_table()

    def _create_table(self):
        with self._conn:
            self._conn.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    task_data TEXT NOT NULL
                )
            ''')

    async def save(self, task: Task):
        self.connect()
        with self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO tasks (id, task_data) VALUES (?, ?)",
                (task.id, task.json())
            )

    async def get(self, task_id: str) -> Task | None:
        self.connect()
        cursor = self._conn.cursor()
        cursor.execute("SELECT task_data FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        if row:
            return Task.parse_raw(row[0])
        return None

    async def delete(self, task_id: str):
        self.connect()
        with self._conn:
            self._conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None