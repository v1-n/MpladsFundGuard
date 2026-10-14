from pathlib import Path
from backend.app.repositories.data_repository import DataRepository
from backend.app.core.errors import ArtifactMissingException
import pytest

def test_missing_artifact_raises_503_exception(tmp_path):
    # Initialize repository with empty directory
    empty_repo = DataRepository(clean_dir=tmp_path)
    
    with pytest.raises(ArtifactMissingException) as exc_info:
        empty_repo.get_master_df()
        
    exc = exc_info.value
    assert exc.status_code == 503
    assert exc.code == "ARTIFACT_MISSING"
    assert "Required data artifact 'mplads_360_master.csv' is not present" in exc.message
    assert "python -m src.rebuild" in exc.message
