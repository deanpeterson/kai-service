import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any, Optional, Sequence

from kai.reactive_codeplanner.vfs.repo_context_snapshot import RepoContextSnapshot


# NOTE(@JonahSussman): Why is this necessary when we have
# `KaiRpcApplicationConfig`?
@dataclass
class RpcClientConfig:
    repo_directory: Path
    analyzer_lsp_server_binary: Path
    analyzer_rules: list[Path]
    analyzer_lsp_path: Path
    analyzer_bundle_paths: list[Path]
    included_paths: Optional[list[Path]] = None
    excluded_paths: Optional[list[Path]] = None
    dep_open_source_labels_path: Optional[Path] = None
    label_selector: Optional[str] = None
    incident_selector: Optional[str] = None


@dataclass(eq=False, kw_only=True)
class Task:
    priority: int = 10
    depth: int = 0
    parent: Optional["Task"] = None
    children: list["Task"] = field(default_factory=list, compare=False)
    retry_count: int = 0
    max_retries: int = 3
    result: Optional["TaskResult"] = None
    # Will be used by the task manager, to revert
    # if/when we ignore this task
    _snapshot_before_work: Optional[RepoContextSnapshot] = None

    _creation_counter = 0

    def oldest_ancestor(self) -> "Task":
        if self.parent:
            return self.parent.oldest_ancestor()
        return self

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Task) and self.__dict__ == other.__dict__

    def sort_key(self) -> tuple[Any, ...]:
        """
        By default, we want to:
          - sort by depth descending (so a deeper node is considered "less" first),
          - then by priority ascending (lower number means higher priority),
          - then by type-level priority (if child classes override priority).
        """
        return (-self.depth, self.priority, self.__class__.priority)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Task):
            raise ValueError(f"Cannot compare Task with {type(other)}")
        return self.sort_key() < other.sort_key()

    def __hash__(self) -> int:
        return hash(tuple(sorted(self.__dict__.items())))

    def __str__(self) -> str:
        def truncate(value: str, max_length: int = 30) -> str:
            return (value[:max_length] + "...") if len(value) > max_length else value

        class_name = self.__class__.__name__
        field_strings = []
        for _field in fields(self):
            value = getattr(self, _field.name)
            truncated_value = truncate(str(value))
            field_strings.append(f'{_field.name}="{truncated_value}"')

        return f"{class_name}<" + ", ".join(field_strings) + ">"

    def background(self) -> str:
        """Used by Agents to provide context when solving child issues"""
        raise NotImplementedError

    def get_cache_path(self, root: Path) -> Path:
        """Used by individual tasks to set the path"""
        if self.depth == 0:
            stem = root / self.__class__.__name__
        else:
            stem = Path(f"depth_{self.depth}") / self.__class__.__name__

        if self.retry_count > 0:
            stem /= Path(self._clean_filename(f"retry_{self.retry_count}"))
        return root / stem

    def _clean_filename(self, name: str) -> str:
        filename = re.sub(r"[\\/:\.]", "_", name)
        filename = re.sub(r"\_+", "_", filename)
        segments = filename.split("_")
        filename = "_".join(segments[-min(3, len(segments)) :])
        return filename[-min(50, len(filename)) :]

    def markdown(self) -> str:
        """Used to communicate task contents to user"""
        raise NotImplementedError

    __repr__ = __str__


@dataclass(eq=False, kw_only=True)
class ValidationError(Task):
    file: str
    line: int
    column: int
    message: str
    priority: int = 5

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.file == other.file
            and self.line == other.line
            and self.column == other.column
            and self.message == other.message
        )

    def __hash__(self) -> int:
        return hash((self.file, self.line, self.column, self.message))

    def fuzzy_equals(self, error2: Task, offset: int = 1) -> bool:
        """
        Determines if two ValidationError objects are likely the same error,
        with a fuzzy comparison allowing for a line number offset.

        Args:
        - error1 (ValidationError): First error to compare.
        - error2 (ValidationError): Second error to compare.
        - offset (int): The allowed difference in line numbers for errors to still be considered the same.

        Returns:
        - bool: True if the errors are likely the same, False otherwise.
        """
        if isinstance(error2, ValidationError):
            return (
                self.file == error2.file
                and abs(self.line - error2.line) <= offset
                and self.column == error2.column
                and self.message == error2.message
            )
        return False

    def sort_key(self) -> tuple[Any, ...]:
        """
        Extend the parent's sort_key with file, line, column, and message.
        So all ValidationErrors are ordered by (depth, priority, ...) first,
        then by file, line, column, message.
        """
        base_key = super().sort_key()  # from Task
        return base_key + (self.file, self.line, self.column, self.message)

    def __str__(self) -> str:
        shadowed_priority: int
        if self.parent:
            shadowed_priority = self.oldest_ancestor().priority
        else:
            shadowed_priority = self.__class__.priority

        return f"{self.__class__.__name__}<loc={self.file}:{self.line}:{self.column}, message={self.message}>(priority={self.priority}({shadowed_priority}), depth={self.depth}, retries={self.retry_count})"

    def background(self) -> str:
        """Used by Agents to provide context when solving child issues"""
        if self.parent is None:
            return ""
        return self.oldest_ancestor().background()

    def get_cache_path(self, root: Path) -> Path:
        root_path = super().get_cache_path(root)
        root_path /= self._clean_filename(self.file)
        return root_path

    def markdown(self) -> str:
        return (
            f"## ValidationError\n\n"
            f"**File**: `{self.file}`\n\n"
            f"**Line**: `{self.line}`\n\n"
            f"**Column**: `{self.column}`\n\n"
            f"**Message**: {self.message}\n"
        )

    __repr__ = __str__


# FIXME: Might not need
@dataclass
class TaskResult:
    encountered_errors: list[str]
    modified_files: list[Path]
    summary: str


@dataclass
class ValidationResult:
    passed: bool
    errors: Sequence[ValidationError]


class ValidationException(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)


class ValidationStep(ABC):
    def __init__(self, RpcClientConfig: RpcClientConfig) -> None:
        self.config = RpcClientConfig

    @abstractmethod
    async def run(self, scoped_paths: Optional[list[Path]]) -> ValidationResult:
        pass
