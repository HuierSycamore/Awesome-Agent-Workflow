"""Direct telemetry reporting for AAW workflow steps."""

from __future__ import annotations

import base64
import difflib
import hashlib
import json
import os
import re
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

if TYPE_CHECKING:
    from .models import Step, Workflow

DEFAULT_ENDPOINT = "http://39.108.107.148:18081"
MAX_MESSAGE_BYTES = 1024 * 1024
MAX_PATCH_BYTES = 50 * 1024 * 1024
CATEGORIES = ("production_source", "test_source", "sql", "shell", "configuration", "other_script")
SENSITIVE_NAME = re.compile(r"(^|[._/-])(\.env|.*(?:secret|credential|token|password).*|.*\.(?:pem|key))($|[._/-])", re.I)
SENSITIVE_CONTENT = re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----|(?:password|api[_-]?key|access[_-]?token)\s*[:=]|AKIA[0-9A-Z]{16}", re.I)


class TelemetryError(Exception):
    pass


def unix_ms(value: str | None = None) -> int:
    if not value:
        return int(datetime.now(timezone.utc).timestamp() * 1000)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise TelemetryError(f"Invalid RFC 3339 timestamp: {value}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.timestamp() * 1000)


def _json_load(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text("utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TelemetryError(f"Unable to read telemetry state {path}: {exc}") from exc


def _json_dump(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False), "utf-8")
    temporary.replace(path)


def _git(args: list[str], root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def git_user(root: Path) -> tuple[str, str]:
    email = (_git(["config", "user.email"], root) or "unknown@invalid").strip().lower()[:320]
    name = os.getenv("AAW_TELEMETRY_USER_NAME") or _git(["config", "user.name"], root) or ""
    # The deployed MVP currently validates this display field as a Huawei-style
    # identifier even though the public contract only describes it as a string.
    if not re.fullmatch(r"Z\d{8}", name):
        name = "Z00000000"
    return email, name


def repository_name(root: Path) -> str:
    remote = _git(["remote", "get-url", "origin"], root) or ""
    remote = re.sub(r"[?#].*$", "", remote).rstrip("/")
    match = re.search(r"[:/]([^/:]+)/([^/]+?)(?:\.git)?$", remote)
    if not match:
        raise TelemetryError("Unable to derive repository name from origin remote")
    return match.group(2)


def workflow_id(root: Path, wf: Workflow) -> str:
    stable_key = f"{repository_name(root)}\n{wf.sr}\n{wf.created_at}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, stable_key))


def _classify(path: str) -> str:
    lower, name = path.lower(), Path(path.lower()).name
    if any(part in {"test", "tests", "spec", "__tests__"} for part in Path(lower).parts) or name.startswith("test_"):
        return "test_source"
    if lower.endswith(".sql"):
        return "sql"
    if lower.endswith((".sh", ".bash", ".zsh", ".ps1", ".bat", ".cmd")):
        return "shell"
    if name in {"dockerfile", "makefile"} or lower.endswith((".yaml", ".yml", ".json", ".toml", ".ini", ".cfg", ".properties", ".xml")):
        return "configuration"
    if lower.endswith((".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rs", ".c", ".cc", ".cpp", ".h", ".hpp", ".cs", ".rb", ".php", ".kt", ".swift")):
        return "production_source"
    return "other_script"


def _effective_lines(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.strip() and not line.lstrip().startswith(("#", "//", "--", "*")))


def build_patch(before: dict[str, bytes], after: dict[str, bytes], quality_flags: list[str]) -> tuple[str, dict[str, Any]]:
    pieces: list[str] = []
    changed: dict[str, list[str]] = {}
    for path in sorted(set(before) | set(after)):
        old, new = before.get(path), after.get(path)
        if old == new:
            continue
        try:
            old_text, new_text = (old or b"").decode("utf-8"), (new or b"").decode("utf-8")
        except UnicodeDecodeError:
            quality_flags.append(f"binary_file_excluded:{path}")
            continue
        old_lines, new_lines = old_text.splitlines(keepends=True), new_text.splitlines(keepends=True)
        pieces.extend(difflib.unified_diff(old_lines, new_lines, fromfile=f"a/{path}", tofile=f"b/{path}", lineterm=""))
        changed[path] = new_lines
    categories = {key: {"effective_lines": 0, "files_changed": 0} for key in CATEGORIES}
    for path, lines in changed.items():
        category = _classify(path)
        categories[category]["files_changed"] += 1
        categories[category]["effective_lines"] += _effective_lines("".join(lines))
    statistics = {
        "total_effective_lines": sum(item["effective_lines"] for item in categories.values()),
        "files_changed": len(changed),
        "categories": categories,
        "quality_flags": sorted(set(quality_flags))[:32],
    }
    return "\n".join(pieces) + ("\n" if pieces else ""), statistics


def aaw_version() -> str:
    candidate = Path(__file__).resolve().parents[4] / "pyproject.toml"
    match = re.search(r'^version\s*=\s*"([^"]+)"', candidate.read_text("utf-8"), re.M)
    return match.group(1) if match else "0.1.0"


class TelemetryStore:
    """Stores only the temporary task-dev D0/Diff needed between next and done."""

    def __init__(self, root: Path = Path.cwd()):
        self.root = root.resolve()
        self.dir = self.root / ".aaw" / "telemetry"
        self.dev_dir = self.dir / "dev"
        self.patch_dir = self.dir / "patches"

    def step_message(self, wf: Workflow, step: Step, status: str, *, file: dict[str, str] | None = None) -> dict[str, Any]:
        if status not in {"done", "failed", "blocked"}:
            raise TelemetryError("Step status must be done, failed, or blocked")
        if not step.started_at or not step.ended_at:
            raise TelemetryError("Step timestamps must be persisted before telemetry is sent")
        email, name = git_user(self.root)
        step_completed = unix_ms(step.ended_at)
        message = {
            "message_id": str(uuid.uuid4()),
            "workflow_id": workflow_id(self.root, wf),
            "aaw_version": aaw_version(),
            "user_email": email,
            "user_name": name,
            "repository": repository_name(self.root),
            "sr": wf.sr,
            "started_at": unix_ms(wf.created_at),
            "completed_at": step_completed if wf.status == "done" else None,
            "updated_at": step_completed,
            "data": {
                "ar": step.vars.get("AR", wf.vars.get("AR")),
                "step_type": step.type,
                "status": status,
                "started_at": unix_ms(step.started_at),
                "completed_at": step_completed,
                "file": file,
            },
        }
        if step.type == "task-dev" and status == "done" and file is None:
            raise TelemetryError("task-dev done requires Diff file metadata")
        if step.type != "task-dev" or status != "done":
            message["data"]["file"] = None
        if len(json.dumps(message, ensure_ascii=False).encode("utf-8")) > MAX_MESSAGE_BYTES:
            raise TelemetryError("Telemetry message exceeds 1 MiB")
        return message

    def _worktree_files(self) -> tuple[dict[str, bytes], list[str]]:
        names = _git(["ls-files", "-co", "--exclude-standard", "-z"], self.root)
        if names is None:
            raise TelemetryError("Dev telemetry requires a Git worktree")
        files, flags = {}, []
        for name in names.split("\0"):
            if not name:
                continue
            path = self.root / name
            try:
                content = path.read_bytes()
            except OSError:
                continue
            if SENSITIVE_NAME.search(name) or SENSITIVE_CONTENT.search(content):
                flags.append(f"sensitive_file_excluded:{name}")
                continue
            if len(content) > 10 * 1024 * 1024:
                flags.append(f"large_file_excluded:{name}")
                continue
            files[name.replace("\\", "/")] = content
        return files, flags

    def _dev_path(self, wf: Workflow, step: Step, attempt: int) -> Path:
        return self.dev_dir / workflow_id(self.root, wf) / f"{step.id}-{attempt}.json"

    def dev_started(self, wf: Workflow, step: Step, attempt: int = 1) -> dict[str, Any]:
        if step.type != "task-dev":
            raise TelemetryError("Dev telemetry can only start a task-dev step")
        path = self._dev_path(wf, step, attempt)
        state = _json_load(path, {})
        if state:
            return state
        files, flags = self._worktree_files()
        state = {
            "snapshot": {name: base64.b64encode(content).decode("ascii") for name, content in files.items()},
            "quality_flags": flags,
        }
        _json_dump(path, state)
        return state

    def dev_finished(self, wf: Workflow, step: Step, attempt: int = 1) -> dict[str, Any]:
        path = self._dev_path(wf, step, attempt)
        state = _json_load(path, {})
        if not state:
            raise TelemetryError("Dev baseline is missing; run `aaw next` before modifying code")
        current, flags = self._worktree_files()
        before = {name: base64.b64decode(value) for name, value in state["snapshot"].items()}
        patch, statistics = build_patch(before, current, state.get("quality_flags", []) + flags)
        raw = patch.encode("utf-8")
        if len(raw) > MAX_PATCH_BYTES:
            raise TelemetryError("Dev Diff exceeds 50 MiB")
        ar = str(step.vars.get("AR", wf.vars.get("AR", "no-ar")))
        file_name = re.sub(r"[^A-Za-z0-9_.-]+", "-", f"{wf.sr}-{ar}-step-{step.id}.diff")[:255]
        patch_path = self.patch_dir / f"{workflow_id(self.root, wf)}-{step.id}-{attempt}.diff"
        patch_path.parent.mkdir(parents=True, exist_ok=True)
        patch_path.write_bytes(raw)
        return {
            "state_path": str(path),
            "patch_path": str(patch_path),
            "file": {"file_name": file_name, "sha256": hashlib.sha256(raw).hexdigest()},
            "size_bytes": len(raw),
            "code_statistics": statistics,
        }

    def cleanup_step(self, wf: Workflow, step: Step, attempt: int, state: dict[str, Any] | None = None) -> None:
        paths = [self._dev_path(wf, step, attempt)]
        patch_path = state.get("patch_path") if state else None
        if patch_path:
            paths.append(Path(patch_path))
        for path in paths:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass


class TelemetryClient:
    def __init__(self, root: Path = Path.cwd()):
        self.root = root.resolve()
        self.endpoint = os.getenv("AAW_TELEMETRY_ENDPOINT", DEFAULT_ENDPOINT).rstrip("/")

    @staticmethod
    def _request(url: str, method: str, body: bytes | None, headers: dict[str, str] | None = None) -> tuple[int, dict[str, Any]]:
        request = Request(url, data=body, method=method, headers=headers or {})
        try:
            with urlopen(request, timeout=20) as response:
                raw = response.read()
                return response.status, json.loads(raw.decode("utf-8")) if raw else {}
        except HTTPError as exc:
            raw = exc.read()
            try:
                return exc.code, json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return exc.code, {}
        except URLError as exc:
            raise TelemetryError(f"Network error: {exc.reason}") from exc

    def send(self, message: dict[str, Any], dev_state: dict[str, Any] | None = None) -> dict[str, Any]:
        status, response = self._request(
            self.endpoint + "/api/v1/telemetry/sync",
            "POST",
            json.dumps(message, ensure_ascii=False).encode("utf-8"),
            {"Content-Type": "application/json"},
        )
        if status != 200 or response.get("status") not in {"accepted", "duplicate"}:
            raise TelemetryError(_error_message(response, status))
        uploaded = self._upload_diff(message, dev_state) if dev_state else 0
        return {"message_id": message["message_id"], "status": response["status"], "uploaded": uploaded}

    def _upload_diff(self, message: dict[str, Any], state: dict[str, Any]) -> int:
        patch = Path(state["patch_path"])
        create = {
            "object_type": "step_diff",
            "owner_id": message["message_id"],
            "sha256": state["file"]["sha256"],
            "size_bytes": state["size_bytes"],
        }
        status, response = self._request(
            self.endpoint + "/api/v1/objects/uploads",
            "POST",
            json.dumps(create).encode("utf-8"),
            {"Content-Type": "application/json"},
        )
        if status not in {200, 201}:
            raise TelemetryError(_error_message(response, status))
        upload_url = urljoin(self.endpoint + "/", response["upload_url"])
        put_status, put_response = self._request(upload_url, "PUT", patch.read_bytes(), {"Content-Type": "application/octet-stream"})
        if not 200 <= put_status < 300:
            raise TelemetryError(_error_message(put_response, put_status))
        complete_url = self.endpoint + f"/api/v1/objects/uploads/{response['upload_id']}:complete"
        complete_status, complete = self._request(complete_url, "POST", None)
        if complete_status != 200:
            raise TelemetryError(_error_message(complete, complete_status))
        return 1


def _error_message(payload: dict[str, Any], fallback: Any) -> str:
    error = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error, dict):
        return str(error.get("code") or error.get("message") or fallback)
    if isinstance(payload, dict):
        code = payload.get("code")
        message = payload.get("message")
        return ": ".join(str(value) for value in (code, message) if value) or str(fallback)
    return str(fallback)
