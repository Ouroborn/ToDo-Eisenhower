from __future__ import annotations

import json
import sys
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List

import customtkinter as ctk
import tkinter.messagebox as messagebox


@dataclass
class Task:
    """Model representing a single task in the Eisenhower matrix."""

    id: str
    title: str
    quadrant: str
    completed: bool = False

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, source: Dict[str, object]) -> Task:
        return cls(
            id=str(source.get("id", uuid.uuid4())),
            title=str(source.get("title", "")),
            quadrant=str(source.get("quadrant", "urgent_important")),
            completed=bool(source.get("completed", False)),
        )


class TaskStorage:
    """Handles loading and saving task data to a JSON file."""

    FILE_NAME = "tasks.json"

    def __init__(self, directory: Path | None = None) -> None:
        if directory is None:
            directory = self._resolve_base_path()
        self.file_path = directory / self.FILE_NAME
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _resolve_base_path() -> Path:
        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve().parent
        return Path(__file__).resolve().parent

    def load_tasks(self) -> List[Task]:
        if not self.file_path.exists():
            self._write_empty_file()
            return []

        try:
            with self.file_path.open("r", encoding="utf-8") as handle:
                raw_data = json.load(handle)

            if not isinstance(raw_data, list):
                raise ValueError("JSON root must be a list")

            return [Task.from_dict(item) for item in raw_data if isinstance(item, dict)]
        except (json.JSONDecodeError, ValueError, OSError) as error:
            messagebox.showwarning(
                title="Ошибка данных",
                message=(
                    "Файл tasks.json поврежден или содержит неверный формат. "
                    "Будет создан новый пустой список задач."
                ),
            )
            self._write_empty_file()
            return []

    def save_tasks(self, tasks: List[Task]) -> None:
        try:
            with self.file_path.open("w", encoding="utf-8") as handle:
                json.dump([task.to_dict() for task in tasks], handle, indent=4, ensure_ascii=False)
        except OSError as error:
            messagebox.showerror(
                title="Ошибка сохранения",
                message=f"Не удалось сохранить задачи: {error}",
            )

    def _write_empty_file(self) -> None:
        try:
            with self.file_path.open("w", encoding="utf-8") as handle:
                json.dump([], handle, indent=4, ensure_ascii=False)
        except OSError:
            pass


class EisenhowerToDoApp(ctk.CTk):
    """Основное окно приложения с визуализацией 4 квадрантов."""

    QUADRANT_DEFINITIONS = {
        "urgent_important": {
            "title": "Срочно и Важно",
            "color": "#d32f2f",
            "description": "Действовать сразу",
        },
        "not_urgent_important": {
            "title": "Не срочно, но Важно",
            "color": "#1976d2",
            "description": "Планировать",
        },
        "urgent_not_important": {
            "title": "Срочно, но Не важно",
            "color": "#f9a825",
            "description": "Делегировать",
        },
        "not_urgent_not_important": {
            "title": "Не срочно и Не важно",
            "color": "#388e3c",
            "description": "Удалить или отложить",
        },
    }

    def __init__(self) -> None:
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        super().__init__()
        self.title("Eisenhower To-Do Matrix")
        self.geometry("1024x680")
        self.minsize(880, 560)

        self.storage = TaskStorage()
        self.tasks: List[Task] = []
        self.quadrant_frames: Dict[str, ctk.CTkScrollableFrame] = {}

        self._configure_grid()
        self._build_header()
        self._build_matrix()
        self._load_tasks()

    def _configure_grid(self) -> None:
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        header.grid_columnconfigure(3, weight=1)

        title_label = ctk.CTkLabel(
            header,
            text="Eisenhower To-Do Matrix",
            font=ctk.CTkFont(size=22, weight="bold"),
        )
        title_label.grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 6))

        self.task_entry = ctk.CTkEntry(header, placeholder_text="Название задачи")
        self.task_entry.grid(row=1, column=0, columnspan=2, sticky="ew", padx=(0, 12), pady=(0, 8))

        self.quadrant_var = ctk.StringVar(value="urgent_important")
        quadrant_options = [info["title"] for info in self.QUADRANT_DEFINITIONS.values()]
        quadrant_keys = list(self.QUADRANT_DEFINITIONS.keys())

        self.quadrant_menu = ctk.CTkOptionMenu(
            header,
            values=quadrant_options,
            command=self._on_quadrant_menu_changed,
        )
        self.quadrant_menu.set(self.QUADRANT_DEFINITIONS[quadrant_keys[0]]["title"])
        self.quadrant_menu.grid(row=1, column=2, sticky="ew", padx=(0, 12), pady=(0, 8))

        add_button = ctk.CTkButton(
            header,
            text="Добавить задачу",
            command=self._add_task,
        )
        add_button.grid(row=1, column=3, sticky="ew", pady=(0, 8))

    def _on_quadrant_menu_changed(self, selected: str) -> None:
        for key, definition in self.QUADRANT_DEFINITIONS.items():
            if definition["title"] == selected:
                self.quadrant_var.set(key)
                return

    def _build_matrix(self) -> None:
        matrix_frame = ctk.CTkFrame(self, corner_radius=0)
        matrix_frame.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        matrix_frame.grid_rowconfigure((0, 1), weight=1, uniform="matrix")
        matrix_frame.grid_columnconfigure((0, 1), weight=1, uniform="matrix")

        quadrant_positions = [
            ("urgent_important", 0, 0),
            ("not_urgent_important", 0, 1),
            ("urgent_not_important", 1, 0),
            ("not_urgent_not_important", 1, 1),
        ]

        for quadrant_key, row, column in quadrant_positions:
            definition = self.QUADRANT_DEFINITIONS[quadrant_key]
            container = ctk.CTkFrame(matrix_frame, fg_color="#222222", corner_radius=15)
            container.grid(row=row, column=column, sticky="nsew", padx=8, pady=8)
            container.grid_rowconfigure(1, weight=1)
            container.grid_columnconfigure(0, weight=1)

            header_frame = ctk.CTkFrame(container, fg_color="#1d1d1d", corner_radius=12)
            header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 8))
            header_frame.grid_columnconfigure(0, weight=1)

            title_label = ctk.CTkLabel(
                header_frame,
                text=definition["title"],
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color=definition["color"],
                anchor="w",
            )
            title_label.grid(row=0, column=0, sticky="w")

            description_label = ctk.CTkLabel(
                header_frame,
                text=definition["description"],
                font=ctk.CTkFont(size=12),
                anchor="w",
            )
            description_label.grid(row=1, column=0, sticky="w", pady=(4, 0))

            scroll_area = ctk.CTkScrollableFrame(container, corner_radius=12, fg_color="#181818")
            scroll_area.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
            scroll_area.grid_columnconfigure(0, weight=1)

            self.quadrant_frames[quadrant_key] = scroll_area

    def _load_tasks(self) -> None:
        self.tasks = self.storage.load_tasks()
        self._refresh_task_display()

    def _save_tasks(self) -> None:
        self.storage.save_tasks(self.tasks)

    def _add_task(self) -> None:
        title = self.task_entry.get().strip()
        selected_quadrant = self.quadrant_var.get()

        if not title:
            messagebox.showwarning(title="Пустая задача", message="Введите текст задачи перед добавлением.")
            return

        if selected_quadrant not in self.QUADRANT_DEFINITIONS:
            selected_quadrant = "urgent_important"

        self.tasks.append(
            Task(
                id=str(uuid.uuid4()),
                title=title,
                quadrant=selected_quadrant,
                completed=False,
            )
        )
        self.task_entry.delete(0, "end")
        self._save_tasks()
        self._refresh_task_display()

    def _refresh_task_display(self) -> None:
        for quadrant_frame in self.quadrant_frames.values():
            for child in quadrant_frame.winfo_children():
                child.destroy()

        tasks_by_quadrant: Dict[str, List[Task]] = {key: [] for key in self.QUADRANT_DEFINITIONS}
        for task in self.tasks:
            tasks_by_quadrant.setdefault(task.quadrant, []).append(task)

        for quadrant_key, tasks in tasks_by_quadrant.items():
            tasks.sort(key=lambda task: (task.completed, task.title.lower()))
            for task in tasks:
                self._create_task_card(self.quadrant_frames[quadrant_key], task)

    def _create_task_card(self, parent: ctk.CTkScrollableFrame, task: Task) -> None:
        task_frame = ctk.CTkFrame(parent, fg_color="#2a2a2a", corner_radius=12, border_width=1)
        task_frame.grid(sticky="ew", padx=8, pady=6)
        task_frame.grid_columnconfigure(1, weight=1)

        completed_var = ctk.BooleanVar(value=task.completed)
        checkbox = ctk.CTkCheckBox(
            task_frame,
            text="",
            variable=completed_var,
            command=lambda t=task, var=completed_var: self._toggle_task_completion(t.id, var.get()),
        )
        checkbox.grid(row=0, column=0, padx=(8, 8), pady=10)

        label_text = task.title
        if task.completed:
            label_text = f"✓ {label_text}"

        task_label = ctk.CTkLabel(
            task_frame,
            text=label_text,
            anchor="w",
            justify="left",
            wraplength=320,
            text_color="#8f8f8f" if task.completed else "#ffffff",
        )
        task_label.grid(row=0, column=1, sticky="w", pady=10)

        remove_button = ctk.CTkButton(
            task_frame,
            text="Удалить",
            width=88,
            command=lambda task_id=task.id: self._delete_task(task_id),
        )
        remove_button.grid(row=0, column=2, padx=8, pady=10)

    def _toggle_task_completion(self, task_id: str, completed: bool) -> None:
        for task in self.tasks:
            if task.id == task_id:
                task.completed = completed
                break

        self._save_tasks()
        self._refresh_task_display()

    def _delete_task(self, task_id: str) -> None:
        self.tasks = [task for task in self.tasks if task.id != task_id]
        self._save_tasks()
        self._refresh_task_display()


def main() -> None:
    app = EisenhowerToDoApp()
    app.mainloop()


if __name__ == "__main__":
    main()
