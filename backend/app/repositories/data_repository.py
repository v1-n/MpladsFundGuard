import json
import logging
from pathlib import Path
from typing import Optional
import pandas as pd

from backend.app.core.config import settings
from backend.app.core.errors import ArtifactMissingException

logger = logging.getLogger(__name__)

class DataRepository:
    def __init__(self, clean_dir: Optional[Path] = None):
        self.clean_dir = clean_dir or settings.CLEAN_DATA_DIR
        self._master_df: Optional[pd.DataFrame] = None
        self._anomaly_scores_df: Optional[pd.DataFrame] = None
        self._audit_sample_df: Optional[pd.DataFrame] = None
        self._clean_sanc_df: Optional[pd.DataFrame] = None
        self._clean_exp_df: Optional[pd.DataFrame] = None
        self._clean_comp_df: Optional[pd.DataFrame] = None
        self._clean_mp_df: Optional[pd.DataFrame] = None
        self._data_quality_report: Optional[dict] = None
        self._evaluation_results: Optional[dict] = None
        self._audit_diagnostics: Optional[dict] = None
        self._audit_rubric: Optional[str] = None

    def _require_file(self, filename: str) -> Path:
        filepath = self.clean_dir / filename
        if not filepath.exists():
            logger.error(f"Required artifact {filename} missing at {filepath}")
            raise ArtifactMissingException(filename)
        return filepath

    def get_master_df(self) -> pd.DataFrame:
        if self._master_df is None:
            p = self._require_file("mplads_360_master.csv")
            df = pd.read_csv(p, low_memory=False)
            required = ["Work ID", "Lifecycle_Stage", "State", "Constituency", "Sanction_Amount", "Total_Exp_Settled"]
            missing = [c for c in required if c not in df.columns]
            if missing:
                raise ValueError(f"mplads_360_master.csv missing required columns: {missing}")
            self._master_df = df
        return self._master_df

    def get_anomaly_scores_df(self) -> pd.DataFrame:
        if self._anomaly_scores_df is None:
            p = self._require_file("anomaly_scores.csv")
            df = pd.read_csv(p, low_memory=False)
            required = ["Work ID", "Stage", "rank_in_stage", "anomaly_score"]
            missing = [c for c in required if c not in df.columns]
            if missing:
                raise ValueError(f"anomaly_scores.csv missing required columns: {missing}")
            self._anomaly_scores_df = df
        return self._anomaly_scores_df

    def get_blind_audit_sample_df(self) -> pd.DataFrame:
        if self._audit_sample_df is None:
            p = self._require_file("manual_audit_sample_blind.csv")
            df = pd.read_csv(p, low_memory=False)
            # Ensure answer key columns are NEVER in the blind sample
            forbidden = ["Cohort", "rank_in_stage", "anomaly_score"]
            leaked = [c for c in forbidden if c in df.columns]
            if leaked:
                raise RuntimeError(f"CRITICAL: Key columns leaked into blind audit sample: {leaked}")
            self._audit_sample_df = df
        return self._audit_sample_df

    def get_data_quality_report(self) -> dict:
        if self._data_quality_report is None:
            p = self._require_file("data_quality_report.json")
            with open(p, "r") as f:
                self._data_quality_report = json.load(f)
        return self._data_quality_report

    def get_evaluation_results(self) -> dict:
        if self._evaluation_results is None:
            p = self._require_file("evaluation_results.json")
            with open(p, "r") as f:
                self._evaluation_results = json.load(f)
        return self._evaluation_results

    def get_audit_diagnostics(self) -> dict:
        if self._audit_diagnostics is None:
            p = self._require_file("audit_matching_diagnostics.json")
            with open(p, "r") as f:
                self._audit_diagnostics = json.load(f)
        return self._audit_diagnostics

    def get_audit_rubric(self) -> str:
        if self._audit_rubric is None:
            p = self._require_file("manual_audit_rubric.md")
            with open(p, "r") as f:
                self._audit_rubric = f.read()
        return self._audit_rubric

    def get_clean_sanc_df(self) -> pd.DataFrame:
        if self._clean_sanc_df is None:
            p = self._require_file("clean_works_sanctioned.csv")
            self._clean_sanc_df = pd.read_csv(p, low_memory=False)
        return self._clean_sanc_df

    def get_clean_exp_df(self) -> pd.DataFrame:
        if self._clean_exp_df is None:
            p = self._require_file("clean_expenditure.csv")
            self._clean_exp_df = pd.read_csv(p, low_memory=False)
        return self._clean_exp_df

    def get_clean_comp_df(self) -> pd.DataFrame:
        if self._clean_comp_df is None:
            p = self._require_file("clean_works_completed.csv")
            self._clean_comp_df = pd.read_csv(p, low_memory=False)
        return self._clean_comp_df

    def get_clean_mp_df(self) -> pd.DataFrame:
        if self._clean_mp_df is None:
            p = self._require_file("clean_mp_summary.csv")
            self._clean_mp_df = pd.read_csv(p, low_memory=False)
        return self._clean_mp_df

# Global repository instance
data_repo = DataRepository()
