"""
Project size and structure calculator
"""

import os
import json
from pathlib import Path
from typing import Dict, Tuple

class ProjectSizeCalculator:
    """Calculate total project size and generate detailed breakdown."""
    
    def __init__(self, root_path: str = "."):
        self.root_path = Path(root_path)
        self.sizes = {}
        self.file_counts = {}
    
    def get_size_in_mb(self, size_bytes: int) -> float:
        """Convert bytes to MB."""
        return round(size_bytes / (1024 * 1024), 2)
    
    def get_size_in_gb(self, size_bytes: int) -> float:
        """Convert bytes to GB."""
        return round(size_bytes / (1024 * 1024 * 1024), 2)
    
    def calculate_directory_size(self, path: Path) -> Tuple[int, int]:
        """Calculate total size and file count for a directory."""
        total_size = 0
        file_count = 0
        
        try:
            for item in path.rglob('*'):
                if item.is_file():
                    try:
                        total_size += item.stat().st_size
                        file_count += 1
                    except OSError:
                        pass
        except PermissionError:
            pass
        
        return total_size, file_count
    
    def analyze_project(self):
        """Analyze the entire project structure."""
        print("=" * 70)
        print("PROJECT SIZE AND STRUCTURE ANALYSIS")
        print("=" * 70)
        print()
        
        main_directories = [
            "backend-services",
            "web-dashboard",
            "smart-contracts",
            "device-firmware",
            "mobile-app",
            "infrastructure",
            "monitoring",
            ".github",
            "tests",
        ]
        
        total_project_size = 0
        total_files = 0
        
        print(f"{'Component':<40} {'Size':<20} {'Files':<10}")
        print("-" * 70)
        
        for dir_name in main_directories:
            dir_path = self.root_path / dir_name
            if dir_path.exists():
                size, count = self.calculate_directory_size(dir_path)
                self.sizes[dir_name] = size
                self.file_counts[dir_name] = count
                total_project_size += size
                total_files += count
                
                size_mb = self.get_size_in_mb(size)
                print(f"{dir_name:<40} {size_mb:>10} MB {count:>15}")
        
        print("-" * 70)
        print()
        print(f"Total Project Size: {self.get_size_in_mb(total_project_size)} MB ({self.get_size_in_gb(total_project_size)} GB)")
        print(f"Total Files: {total_files}")
        print()
        
        return total_project_size, total_files
    
    def estimate_with_dependencies(self) -> Dict[str, float]:
        """Estimate project size with typical dependencies."""
        print("=" * 70)
        print("PROJECT SIZE ESTIMATION WITH DEPENDENCIES")
        print("=" * 70)
        print()
        
        estimates = {
            "Source Code": 0,
            "Python Dependencies (backend)": 500,  # MB
            "Node Dependencies (web-dashboard)": 300,  # MB
            "Node Dependencies (smart-contracts)": 200,  # MB
            "Docker Images": 2000,  # MB
            "Database Volume": 1000,  # MB
            "Cache Volume": 500,  # MB
            "Log Volume": 1000,  # MB
            "Monitoring Data": 1000,  # MB
        }
        
        total_source, _ = self.calculate_directory_size(self.root_path)
        source_mb = self.get_size_in_mb(total_source)
        estimates["Source Code"] = source_mb
        
        total_with_deps = sum(estimates.values())
        
        print(f"{'Component':<40} {'Size (MB)':<20}")
        print("-" * 60)
        for component, size in estimates.items():
            print(f"{component:<40} {size:>15.2f}")
        
        print("-" * 60)
        print(f"{'Total':<40} {total_with_deps:>15.2f}")
        print(f"Total in GB: {total_with_deps / 1024:.2f} GB")
        print()
        
        return estimates
    
    def generate_report(self) -> str:
        """Generate a comprehensive size report."""
        source_size, total_files = self.analyze_project()
        deps_breakdown = self.estimate_with_dependencies()
        
        total_with_deps = sum(deps_breakdown.values())
        
        report = f"""
PROJECT SIZE REPORT
==================

Current Source Code Size: {self.get_size_in_mb(source_size)} MB
Total Files: {total_files}

With Dependencies (Estimated):
- Full Project Size: {total_with_deps:.2f} MB ({total_with_deps / 1024:.2f} GB)
- Breakdown:
{chr(10).join([f"  - {k}: {v:.2f} MB" for k, v in deps_breakdown.items()])}

Storage Requirements:
- Development Environment: {total_with_deps:.2f} MB
- Production (with logs): {total_with_deps * 1.5:.2f} MB
- Backup (3 copies): {total_with_deps * 3:.2f} MB

Memory Requirements:
- Minimum: 4 GB (development)
- Recommended: 8 GB (development)
- Production: 16 GB (Kubernetes cluster)

Deployment Notes:
- Docker Container Size: ~2-3 GB (all services)
- Kubernetes Cluster Size: ~20-30 GB (with data volumes)
- Database Size: ~1 GB initial, grows based on usage
"""
        
        return report


if __name__ == "__main__":
    calculator = ProjectSizeCalculator()
    report = calculator.generate_report()
    print(report)
    
    # Save report to file
    with open("PROJECT_SIZE_REPORT.txt", "w") as f:
        f.write(report)
    
    print("Report saved to PROJECT_SIZE_REPORT.txt")
