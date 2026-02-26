from huggingface_hub import snapshot_download
from huggingface_hub.utils import tqdm, enable_progress_bars
from pathlib import Path
from typing import Optional, Callable
from ..config import Config
import os
import shutil


class HuggingFaceDownloader:
    """Downloads model files from HuggingFace Hub"""

    def __init__(self):
        self.cache_dir = Config.CACHE_DIR
        self.model_dir = Config.MODEL_DIR
    def validate_model_not_exists(self, repo_id: str, target_dir: Optional[str] = None) -> None:
        """
        Validate that a model does not already exist in target directories.
        
        Args:
            repo_id: Repository ID in format "owner/model:quant"
            target_dir: Specific target directory to check (optional)
            
        Raises:
            FileExistsError: If GGUF file already exists in cache or model_dir
        """
        # Parse owner_model from repo_id
        if ":" in repo_id:
            owner_model = repo_id.split(":")[0]
        else:
            owner_model = repo_id
        
        # Sanitize owner_model for filesystem (consistent with project conventions)
        sanitized_id = owner_model.replace("/", "-").lower()
        
        # Directories to check
        dirs_to_check = []
        if target_dir:
            dirs_to_check.append(Path(target_dir))
        else:
            # Check both cache and model_dir
            dirs_to_check.extend([self.cache_dir, Path(self.model_dir)])
        
        # Search for existing GGUF files
        for check_dir in dirs_to_check:
            if not check_dir.exists():
                continue
                
            # Check for direct subdirectory match
            model_subdir = check_dir / owner_model
            if model_subdir.exists():
                gguf_files = list(model_subdir.rglob("*.gguf"))
                if gguf_files:
                    raise FileExistsError(
                        f"Model already exists in {model_subdir} - "
                        f"found {len(gguf_files)} GGUF file(s): "
                        f"{', '.join(str(f.name) for f in gguf_files[:3])}"
                    )
            
            # Also check sanitized version
            sanitized_subdir = check_dir / sanitized_id
            if sanitized_subdir.exists() and sanitized_subdir != model_subdir:
                gguf_files = list(sanitized_subdir.rglob("*.gguf"))
                if gguf_files:
                    raise FileExistsError(
                        f"Model already exists in {sanitized_subdir} - "
                        f"found {len(gguf_files)} GGUF file(s): "
                        f"{', '.join(str(f.name) for f in gguf_files[:3])}"
                    )
            
            # Check for any GGUF files matching the model name pattern
            for item in check_dir.iterdir():
                if item.is_dir():
                    # Check if directory name matches owner or model name (case-insensitive)
                    item_name_lower = item.name.lower()
                    owner_lower = owner_model.split("/")[0].lower() if "/" in owner_model else owner_model.lower()
                    model_name_lower = owner_model.split("/")[1].lower() if "/" in owner_model else owner_model.lower()
                    
                    if item_name_lower in [owner_lower, model_name_lower, sanitized_id]:
                        gguf_files = list(item.rglob("*.gguf"))
                        if gguf_files:
                            raise FileExistsError(
                                f"Model already exists in {item} - "
                                f"found {len(gguf_files)} GGUF file(s): "
                                f"{', '.join(str(f.name) for f in gguf_files[:3])}"
                            )

    def check_disk_space(self, target_dir: str, required_gb: int = None) -> None:
        """
        Check if sufficient disk space is available.
        
        Args:
            target_dir: Directory where model will be downloaded
            required_gb: Required space in GB (default: MAX_MODEL_SIZE_GB from config)
            
        Raises:
            OSError: If insufficient disk space available
        """
        if required_gb is None:
            required_gb = Config.MAX_MODEL_SIZE_GB
        
        # Check available space
        usage = shutil.disk_usage(target_dir)
        available_gb = usage.free / (1024 ** 3)
        # Add buffer for safety (models can be larger than expected)
        required_with_buffer = required_gb * 1.2
        
        if available_gb < required_with_buffer:
            raise OSError(
                f"Insufficient disk space: {available_gb:.1f}GB available, "
                f"{required_with_buffer:.1f}GB required (including 20% buffer). "
                f"Free up space or reduce MAX_MODEL_SIZE_GB (currently {Config.MAX_MODEL_SIZE_GB}GB)"
            )

    def download_model(
        self, repo_id: str, local_dir: Optional[str] = None, revision: str = "main",
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        Download model from HuggingFace Hub with progress tracking

        Args:
            repo_id: Repository ID in format "owner/model:quant" (e.g., "microsoft/Phi-3-mini-4k-instruct:q4_0")
            local_dir: Local directory path (default: cache_dir/repo_id)
            revision: Git revision (default: "main")
            progress_callback: Optional callback function to receive progress messages

        Returns:
            str: Path to downloaded directory

        Raises:
            ValueError: If repo_id is invalid format
            FileExistsError: If model already exists
            OSError: If insufficient disk space
            Exception: If download fails
        """
        # Validate repo_id format
        if ":" in repo_id and repo_id.count(":") > 1:
            raise ValueError(
                f"Invalid repo_id format: {repo_id}. Expected format: 'owner/model:quant'"
            )

        # Parse owner, model, quantization
        if ":" in repo_id:
            owner_model = repo_id.split(":")[0]
            quantization = repo_id.split(":")[1]
        else:
            owner_model = repo_id
            quantization = "default"

        # Set local directory
        if local_dir is None:
            local_dir = str(self.cache_dir / owner_model)

        # Validate model doesn't already exist (check both cache and model_dir)
        self.validate_model_not_exists(repo_id, local_dir)

        # Check disk space before downloading
        target_path = Path(local_dir)
        target_path.mkdir(parents=True, exist_ok=True)
        self.check_disk_space(str(target_path))

        # Enable progress bars
        enable_progress_bars()

        # Download model with progress tracking
        try:
            if progress_callback:
                progress_callback(f"📥 Downloading from HuggingFace: {repo_id}")
                progress_callback(f"📂 Cache directory: {local_dir}")
            else:
                print(f"📥 Downloading from HuggingFace: {repo_id}")
                print(f"📂 Cache directory: {local_dir}")

            # Use tqdm to show overall progress
            with tqdm(
                total=None,  # Total not known beforehand for snapshot
                desc=f"Downloading {owner_model}",
                unit="files",
                leave=True,
            ) as pbar:
                downloaded_path = snapshot_download(
                    repo_id=owner_model,
                    cache_dir=str(self.cache_dir),
                    local_dir=local_dir,
                    local_dir_use_symlinks=False,
                    revision=revision,
                    resume_download=True,
                )
                pbar.update(1)  # Mark completion

            msg = f"✅ Download complete: {downloaded_path}"
            if progress_callback:
                progress_callback(msg)
            else:
                print(msg)

            return downloaded_path

        except Exception as e:
            error_msg = f"❌ Download failed: {e}"
            if progress_callback:
                progress_callback(error_msg)
            else:
                print(error_msg)
            raise
    def extract_gguf_path(self, downloaded_dir: str) -> Optional[str]:
        """
        Find the GGUF file in the downloaded directory

        Args:
            downloaded_dir: Path to downloaded directory

        Returns:
            Optional[str]: Path to GGUF file, or None if not found
        """
        downloaded_path = Path(downloaded_dir)

        # Search for GGUF file
        for file in downloaded_path.rglob("*.gguf"):
            return str(file)

        return None

    def get_download_status(self, repo_id: str) -> dict:
        """
        Get download status (if cache exists)

        Args:
            repo_id: Repository ID (without quantization)

        Returns:
            dict: Status information
        """
        owner_model = repo_id.split(":")[0] if ":" in repo_id else repo_id
        cache_path = self.cache_dir / owner_model

        if cache_path.exists():
            gguf_files = list(cache_path.rglob("*.gguf"))
            return {
                "status": "cached",
                "repo_id": repo_id,
                "cache_path": str(cache_path),
                "gguf_files": [str(f) for f in gguf_files],
                "file_count": len(gguf_files),
            }
        else:
            return {"status": "not_cached", "repo_id": repo_id, "cache_path": None}
