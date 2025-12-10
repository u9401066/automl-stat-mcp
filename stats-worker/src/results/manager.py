"""
Job Results Manager

Manages local storage of analysis results in a user-friendly directory structure.
Results include reports, visualizations, and metadata for easy user access.

Directory Structure:
    /results/{user_id}/{job_name}_{timestamp}/
        ├── metadata.json          # Job info, data source, parameters
        ├── report.json            # Analysis results in JSON
        ├── report.html            # Human-readable HTML report (optional)
        ├── figures/
        │   ├── roc_curve.png
        │   ├── feature_importance.png
        │   └── ...
        └── data/
            └── source_info.json   # Original dataset metadata

Usage:
    from results.manager import JobResultsManager
    
    manager = JobResultsManager(
        user_id="eric",
        job_name="heart_disease_analysis",
        base_path="/data/results"
    )
    
    # Save analysis results
    manager.save_result(analysis_result)
    manager.save_figure(fig, "roc_curve.png")
    manager.save_source_info(dataset_metadata)
    
    # Finalize and get summary
    summary = manager.finalize()
"""
import os
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field, asdict
import logging

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)

# Default base path for results
DEFAULT_RESULTS_BASE = os.getenv("RESULTS_BASE_PATH", "/data/results")


@dataclass
class SourceInfo:
    """Information about the original data source."""
    dataset_id: Optional[str] = None
    dataset_name: Optional[str] = None
    original_file: Optional[str] = None
    processed_file: Optional[str] = None
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    columns_used: Optional[List[str]] = None
    target_column: Optional[str] = None
    created_at: Optional[str] = None
    preprocessing_notes: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class JobMetadata:
    """Metadata for a job execution."""
    job_id: str
    job_name: str
    user_id: str
    job_type: str  # 'auto_analyze', 'roc_analysis', 'survival_analysis', etc.
    created_at: str
    completed_at: Optional[str] = None
    status: str = "running"
    parameters: Dict[str, Any] = field(default_factory=dict)
    source_info: Optional[SourceInfo] = None
    result_path: Optional[str] = None
    figures: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if self.source_info:
            d['source_info'] = self.source_info.to_dict()
        return d


class JobResultsManager:
    """
    Manages local storage of job results.
    
    Creates a structured directory for each job containing:
    - metadata.json: Job info and parameters
    - report.json: Analysis results
    - figures/: Visualization images
    - data/: Source data information
    """
    
    def __init__(
        self,
        user_id: str,
        job_name: str,
        job_type: str = "analysis",
        base_path: Optional[str] = None,
        job_id: Optional[str] = None,
    ):
        """
        Initialize results manager for a job.
        
        Args:
            user_id: User identifier
            job_name: Human-readable job name (e.g., "heart_disease_analysis")
            job_type: Type of analysis job
            base_path: Base path for results (default: /data/results)
            job_id: Optional specific job ID (auto-generated if not provided)
        """
        self.user_id = user_id
        self.job_name = self._sanitize_name(job_name)
        self.job_type = job_type
        self.base_path = Path(base_path or DEFAULT_RESULTS_BASE)
        
        # Generate timestamp-based job ID
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.job_id = job_id or f"{self.job_name}_{self.timestamp}"
        
        # Setup directory structure
        self.job_dir = self.base_path / user_id / self.job_id
        self.figures_dir = self.job_dir / "figures"
        self.data_dir = self.job_dir / "data"
        
        # Initialize metadata
        self.metadata = JobMetadata(
            job_id=self.job_id,
            job_name=job_name,
            user_id=user_id,
            job_type=job_type,
            created_at=datetime.now().isoformat(),
            result_path=str(self.job_dir),
        )
        
        # Track saved items
        self._figures_saved: List[str] = []
        self._initialized = False
    
    def _sanitize_name(self, name: str) -> str:
        """Sanitize name for filesystem use."""
        # Replace spaces and special chars
        sanitized = name.replace(" ", "_").replace("/", "_").replace("\\", "_")
        # Remove non-alphanumeric except underscore and hyphen
        return "".join(c for c in sanitized if c.isalnum() or c in "_-")
    
    def _ensure_dirs(self) -> None:
        """Create directory structure if not exists."""
        if self._initialized:
            return
            
        self.job_dir.mkdir(parents=True, exist_ok=True)
        self.figures_dir.mkdir(exist_ok=True)
        self.data_dir.mkdir(exist_ok=True)
        self._initialized = True
        logger.info(f"Created job directory: {self.job_dir}")
    
    def save_source_info(
        self,
        dataset_id: Optional[str] = None,
        dataset_name: Optional[str] = None,
        original_file: Optional[str] = None,
        processed_file: Optional[str] = None,
        row_count: Optional[int] = None,
        column_count: Optional[int] = None,
        columns_used: Optional[List[str]] = None,
        target_column: Optional[str] = None,
        metadata_dict: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Save information about the source dataset.
        
        Args:
            dataset_id: Dataset identifier
            dataset_name: Human-readable dataset name
            original_file: Path to original file
            processed_file: Path to processed file
            row_count: Number of rows
            column_count: Number of columns
            columns_used: List of columns used in analysis
            target_column: Target column for ML
            metadata_dict: Additional metadata dict to merge
            
        Returns:
            Path to saved source_info.json
        """
        self._ensure_dirs()
        
        source_info = SourceInfo(
            dataset_id=dataset_id,
            dataset_name=dataset_name,
            original_file=original_file,
            processed_file=processed_file,
            row_count=row_count,
            column_count=column_count,
            columns_used=columns_used,
            target_column=target_column,
            created_at=datetime.now().isoformat(),
        )
        
        # Merge additional metadata
        info_dict = source_info.to_dict()
        if metadata_dict:
            info_dict.update(metadata_dict)
        
        # Save to file
        source_path = self.data_dir / "source_info.json"
        with open(source_path, "w", encoding="utf-8") as f:
            json.dump(info_dict, f, indent=2, ensure_ascii=False)
        
        # Update job metadata
        self.metadata.source_info = source_info
        
        logger.info(f"Saved source info: {source_path}")
        return str(source_path)
    
    def save_figure(
        self,
        fig: plt.Figure,
        filename: str,
        title: Optional[str] = None,
        dpi: int = 300,
        close_fig: bool = True,
    ) -> str:
        """
        Save a matplotlib figure to the figures directory.
        
        Args:
            fig: Matplotlib figure
            filename: Filename (e.g., "roc_curve.png")
            title: Optional title for the figure
            dpi: Resolution
            close_fig: Whether to close the figure after saving
            
        Returns:
            Path to saved figure
        """
        self._ensure_dirs()
        
        # Ensure proper extension
        if not filename.lower().endswith(('.png', '.jpg', '.svg', '.pdf')):
            filename += '.png'
        
        fig_path = self.figures_dir / filename
        
        try:
            fig.savefig(
                fig_path,
                dpi=dpi,
                bbox_inches='tight',
                facecolor='white',
                edgecolor='none',
            )
            self._figures_saved.append(filename)
            logger.info(f"Saved figure: {fig_path}")
        finally:
            if close_fig:
                plt.close(fig)
        
        return str(fig_path)
    
    def save_figures_from_minio(
        self,
        visualizations: List[Dict[str, Any]],
        minio_client=None,
    ) -> List[str]:
        """
        Download and save figures from MinIO to local directory.
        
        Args:
            visualizations: List of visualization dicts with 'url' keys
            minio_client: Optional MinIO client (creates new if not provided)
            
        Returns:
            List of local file paths
        """
        self._ensure_dirs()
        saved_paths = []
        
        # TODO: Implement MinIO download
        # For now, just track the URLs
        for viz in visualizations:
            if 'url' in viz and viz['url']:
                filename = viz.get('filename') or viz['url'].split('/')[-1]
                self._figures_saved.append(filename)
                saved_paths.append(viz['url'])
        
        return saved_paths
    
    def save_result(
        self,
        result: Dict[str, Any],
        filename: str = "report.json",
    ) -> str:
        """
        Save analysis result as JSON.
        
        Args:
            result: Analysis result dictionary
            filename: Output filename
            
        Returns:
            Path to saved file
        """
        self._ensure_dirs()
        
        result_path = self.job_dir / filename
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Saved result: {result_path}")
        return str(result_path)
    
    def save_html_report(
        self,
        result: Dict[str, Any],
        template: Optional[str] = None,
    ) -> str:
        """
        Generate and save an HTML report.
        
        Args:
            result: Analysis result dictionary
            template: Optional HTML template string
            
        Returns:
            Path to saved HTML file
        """
        self._ensure_dirs()
        
        html_content = self._generate_html_report(result, template)
        report_path = self.job_dir / "report.html"
        
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        logger.info(f"Saved HTML report: {report_path}")
        return str(report_path)
    
    def _generate_html_report(
        self,
        result: Dict[str, Any],
        template: Optional[str] = None,
    ) -> str:
        """Generate HTML report from result."""
        if template:
            return template.format(**result)
        
        # Default simple HTML template
        figures_html = ""
        for fig_name in self._figures_saved:
            figures_html += f'<div class="figure"><img src="figures/{fig_name}" alt="{fig_name}"><p>{fig_name}</p></div>\n'
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.metadata.job_name} - Analysis Report</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 40px; line-height: 1.6; }}
        h1 {{ color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .metadata {{ background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 20px 0; }}
        .metadata dt {{ font-weight: bold; color: #333; }}
        .metadata dd {{ margin-left: 20px; margin-bottom: 10px; }}
        .figures {{ display: flex; flex-wrap: wrap; gap: 20px; }}
        .figure {{ text-align: center; }}
        .figure img {{ max-width: 100%; border: 1px solid #ddd; border-radius: 4px; }}
        pre {{ background: #f8f8f8; padding: 15px; border-radius: 4px; overflow-x: auto; }}
        .success {{ color: #4CAF50; }}
        .error {{ color: #f44336; }}
    </style>
</head>
<body>
    <h1>📊 {self.metadata.job_name}</h1>
    
    <div class="metadata">
        <dl>
            <dt>Job ID</dt><dd>{self.metadata.job_id}</dd>
            <dt>Job Type</dt><dd>{self.metadata.job_type}</dd>
            <dt>User</dt><dd>{self.metadata.user_id}</dd>
            <dt>Created</dt><dd>{self.metadata.created_at}</dd>
            <dt>Status</dt><dd class="{'success' if self.metadata.status == 'completed' else ''}">{self.metadata.status}</dd>
        </dl>
    </div>
    
    <h2>📈 Visualizations</h2>
    <div class="figures">
        {figures_html if figures_html else '<p>No figures generated.</p>'}
    </div>
    
    <h2>📋 Results</h2>
    <pre>{json.dumps(result, indent=2, ensure_ascii=False, default=str)[:5000]}{'...' if len(json.dumps(result)) > 5000 else ''}</pre>
    
    <footer style="margin-top: 40px; color: #888; font-size: 0.9em;">
        Generated by AutoML Stats Service • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    </footer>
</body>
</html>"""
    
    def set_parameters(self, params: Dict[str, Any]) -> None:
        """Set job parameters in metadata."""
        self.metadata.parameters = params
    
    def set_error(self, error_message: str) -> None:
        """Set error status and message."""
        self.metadata.status = "failed"
        self.metadata.error_message = error_message
    
    def finalize(
        self,
        result: Optional[Dict[str, Any]] = None,
        generate_html: bool = True,
    ) -> Dict[str, Any]:
        """
        Finalize the job and save all metadata.
        
        Args:
            result: Final result to save
            generate_html: Whether to generate HTML report
            
        Returns:
            Summary dictionary with paths
        """
        self._ensure_dirs()
        
        # Update metadata
        self.metadata.completed_at = datetime.now().isoformat()
        # Only set to completed if not already failed
        if self.metadata.status != "failed":
            self.metadata.status = "completed"
        self.metadata.figures = self._figures_saved
        
        # Save result if provided
        if result:
            self.save_result(result)
            if generate_html:
                self.save_html_report(result)
        
        # Save metadata
        metadata_path = self.job_dir / "metadata.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(self.metadata.to_dict(), f, indent=2, ensure_ascii=False)
        
        logger.info(f"Finalized job: {self.job_dir}")
        
        return {
            "job_id": self.metadata.job_id,
            "job_name": self.metadata.job_name,
            "status": self.metadata.status,
            "result_path": str(self.job_dir),
            "figures_path": str(self.figures_dir),
            "figures": self._figures_saved,
            "metadata_path": str(metadata_path),
            "report_path": str(self.job_dir / "report.json") if result else None,
            "html_report_path": str(self.job_dir / "report.html") if result and generate_html else None,
        }
    
    @classmethod
    def list_user_jobs(
        cls,
        user_id: str,
        base_path: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List all jobs for a user.
        
        Args:
            user_id: User identifier
            base_path: Base path for results
            
        Returns:
            List of job summaries
        """
        base = Path(base_path or DEFAULT_RESULTS_BASE)
        user_dir = base / user_id
        
        if not user_dir.exists():
            return []
        
        jobs = []
        for job_dir in sorted(user_dir.iterdir(), reverse=True):
            if not job_dir.is_dir():
                continue
            
            metadata_path = job_dir / "metadata.json"
            if metadata_path.exists():
                with open(metadata_path, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
                    jobs.append({
                        "job_id": metadata.get("job_id"),
                        "job_name": metadata.get("job_name"),
                        "job_type": metadata.get("job_type"),
                        "status": metadata.get("status"),
                        "created_at": metadata.get("created_at"),
                        "path": str(job_dir),
                    })
            else:
                # Minimal info if no metadata
                jobs.append({
                    "job_id": job_dir.name,
                    "path": str(job_dir),
                })
        
        return jobs
    
    @classmethod
    def get_job(
        cls,
        user_id: str,
        job_id: str,
        base_path: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get details for a specific job.
        
        Args:
            user_id: User identifier
            job_id: Job identifier
            base_path: Base path for results
            
        Returns:
            Job details or None if not found
        """
        base = Path(base_path or DEFAULT_RESULTS_BASE)
        job_dir = base / user_id / job_id
        
        if not job_dir.exists():
            return None
        
        result = {
            "job_id": job_id,
            "path": str(job_dir),
            "figures": [],
        }
        
        # Load metadata
        metadata_path = job_dir / "metadata.json"
        if metadata_path.exists():
            with open(metadata_path, "r", encoding="utf-8") as f:
                result["metadata"] = json.load(f)
        
        # Load result
        report_path = job_dir / "report.json"
        if report_path.exists():
            with open(report_path, "r", encoding="utf-8") as f:
                result["result"] = json.load(f)
        
        # List figures
        figures_dir = job_dir / "figures"
        if figures_dir.exists():
            result["figures"] = [f.name for f in figures_dir.iterdir() if f.is_file()]
        
        # Load source info
        source_path = job_dir / "data" / "source_info.json"
        if source_path.exists():
            with open(source_path, "r", encoding="utf-8") as f:
                result["source_info"] = json.load(f)
        
        return result
