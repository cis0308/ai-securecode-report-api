import shutil
import zipfile
from pathlib import Path
from uuid import uuid4
from fastapi import UploadFile
from app.config import UPLOAD_DIR, TEMP_DIR, ALLOWED_EXTENSIONS, SOURCE_EXTENSIONS

def validate_file(filename: str):
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise ValueError(f"지원하지 않는 파일 형식입니다. 허용 확장자: {allowed}")

def save_upload_file(file: UploadFile) -> Path:
    validate_file(file.filename)
    ext = Path(file.filename).suffix.lower()
    saved_path = UPLOAD_DIR / f"{uuid4().hex}{ext}"
    with saved_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return saved_path

def prepare_analysis_target(saved_path: Path) -> Path:
    target_dir = TEMP_DIR / saved_path.stem
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    if saved_path.suffix.lower() in SOURCE_EXTENSIONS:
        shutil.copy(saved_path, target_dir / saved_path.name)
        return target_dir
    if saved_path.suffix.lower() == ".zip":
        with zipfile.ZipFile(saved_path, "r") as zip_ref:
            zip_ref.extractall(target_dir)
        return target_dir
    raise ValueError("분석할 수 없는 파일 형식입니다.")

def count_python_files(target_dir: Path) -> int:
    return len(list(target_dir.rglob("*.py")))

def count_java_files(target_dir: Path) -> int:
    return len(list(target_dir.rglob("*.java")))

def count_c_cpp_files(target_dir: Path) -> int:
    return sum(len(list(target_dir.rglob(p))) for p in ["*.c", "*.cpp", "*.h", "*.hpp"])

def count_source_files(target_dir: Path) -> int:
    return sum(len(list(target_dir.rglob(f"*{ext}"))) for ext in SOURCE_EXTENSIONS)

def read_source_code(target_dir: Path, limit: int = 6000) -> str:
    chunks, total = [], 0
    for ext in SOURCE_EXTENSIONS:
        for src_file in target_dir.rglob(f"*{ext}"):
            try:
                text = src_file.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            part = f"\n# FILE: {src_file}\n{text}\n"
            chunks.append(part)
            total += len(part)
            if total >= limit:
                return "".join(chunks)[:limit]
    return "".join(chunks)[:limit]

def read_python_code(target_dir: Path, limit: int = 6000) -> str:
    return read_source_code(target_dir, limit)
