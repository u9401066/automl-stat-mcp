"""
Worker Results Mixin

Provides integration between StatsWorker and JobResultsManager
for saving analysis results to local directory structure.
"""
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

import matplotlib.pyplot as plt

from ..config import RESULTS_BASE_PATH
from ..results.manager import JobResultsManager

logger = logging.getLogger(__name__)


class WorkerResultsMixin:
    """
    Mixin class to add local results management to StatsWorker.
    
    Provides methods to:
    - Create job result directories
    - Save figures locally alongside MinIO
    - Generate HTML reports for users
    - Track source dataset information
    """
    
    def create_results_manager(
        self,
        job: Dict[str, Any],
        job_type: str,
    ) -> JobResultsManager:
        """
        Create a JobResultsManager for the given job.
        
        Args:
            job: Job dictionary with job_id, user_id, etc.
            job_type: Type of analysis job
            
        Returns:
            JobResultsManager instance
        """
        job_id = job.get("job_id", "unknown")
        user_id = job.get("user_id") or job.get("params", {}).get("user_id", "anonymous")
        job_name = job.get("job_name") or job.get("params", {}).get("job_name") or job_id
        
        manager = JobResultsManager(
            user_id=user_id,
            job_name=job_name,
            job_type=job_type,
            base_path=RESULTS_BASE_PATH,
            job_id=job_id,
        )
        
        # Set job parameters
        params = job.get("params", {})
        manager.set_parameters(params)
        
        return manager
    
    def save_source_info_from_job(
        self,
        manager: JobResultsManager,
        job: Dict[str, Any],
        df_shape: tuple,
        columns_used: Optional[List[str]] = None,
    ) -> None:
        """
        Extract and save source information from job metadata.
        
        Args:
            manager: JobResultsManager instance
            job: Job dictionary
            df_shape: (rows, cols) tuple from loaded DataFrame
            columns_used: List of columns actually used in analysis
        """
        params = job.get("params", {})
        
        # Determine data source
        minio_path = job.get("minio_path") or params.get("minio_path")
        dataset_id = job.get("dataset_id") or params.get("dataset_id")
        csv_path = params.get("csv_path")
        
        manager.save_source_info(
            dataset_id=dataset_id,
            dataset_name=params.get("dataset_name"),
            original_file=csv_path or minio_path,
            row_count=df_shape[0],
            column_count=df_shape[1],
            columns_used=columns_used,
            target_column=params.get("target_column") or params.get("y_true_col"),
            metadata_dict={
                "minio_path": minio_path,
                "csv_path": csv_path,
            }
        )
    
    def save_visualizations_locally(
        self,
        manager: JobResultsManager,
        visualizations: List[Dict[str, Any]],
    ) -> List[str]:
        """
        Save visualizations to local results directory.
        
        This is called after visualizations are uploaded to MinIO,
        to provide local copies for user access.
        
        Args:
            manager: JobResultsManager instance
            visualizations: List of visualization dicts with 'figure' or 'url'
            
        Returns:
            List of local file paths
        """
        saved_paths = []
        
        for viz in visualizations:
            # If we have the matplotlib figure object, save it
            if 'figure' in viz and viz['figure'] is not None:
                fig = viz['figure']
                filename = viz.get('filename') or f"{viz.get('type', 'plot')}.png"
                
                try:
                    path = manager.save_figure(fig, filename, close_fig=False)
                    saved_paths.append(path)
                except Exception as e:
                    logger.warning(f"Failed to save figure locally: {e}")
            
            # Track URL-only visualizations
            elif 'url' in viz and viz['url']:
                manager._figures_saved.append(
                    viz.get('filename') or viz['url'].split('/')[-1]
                )
        
        return saved_paths
    
    def finalize_job_results(
        self,
        manager: JobResultsManager,
        result: Dict[str, Any],
        generate_html: bool = True,
    ) -> Dict[str, Any]:
        """
        Finalize job results and generate summary.
        
        Args:
            manager: JobResultsManager instance
            result: Analysis result dictionary
            generate_html: Whether to generate HTML report
            
        Returns:
            Summary with paths to all generated files
        """
        summary = manager.finalize(
            result=result,
            generate_html=generate_html,
        )
        
        logger.info(f"Job results saved to: {summary['result_path']}")
        
        return summary
    
    def process_with_local_results(
        self,
        job: Dict[str, Any],
        job_type: str,
        process_func,
        generate_visualizations: bool = True,
    ) -> Dict[str, Any]:
        """
        Wrapper to process a job with local results management.
        
        Args:
            job: Job dictionary
            job_type: Type of analysis
            process_func: Function that takes (job, manager) and returns result
            generate_visualizations: Whether to generate visualizations
            
        Returns:
            Result dictionary with local_results added
        """
        manager = self.create_results_manager(job, job_type)
        
        try:
            # Run the actual analysis
            result = process_func(job, manager)
            
            # Finalize and add local paths to result
            local_summary = self.finalize_job_results(manager, result)
            result['local_results'] = local_summary
            
            return result
            
        except Exception as e:
            manager.set_error(str(e))
            manager.finalize(result={"error": str(e)}, generate_html=False)
            raise
