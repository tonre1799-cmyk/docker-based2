"""
Grid Based Heatmap Generator
============================
Generates human-specific heatmap using grid accumulation.
Efficient for large-scale occupancy analytics.
"""

import cv2
import numpy as np
from typing import List, Dict, Any, Tuple


class GridBasedHeatmapGenerator:
    """
    Grid-based heatmap generator.
    Accumulates human positions into grid-based heatmap.
    """
    
    def __init__(self, grid_size: Tuple[int, int] = (10, 10)):
        """
        Initialize heatmap generator.
        
        Args:
            grid_size: (rows, cols) for heatmap grid
        """
        self.grid_size = grid_size
    
    def generate_from_detections(
        self,
        detections_per_frame: List[Dict],
        frame_width: int,
        frame_height: int,
        background_image: np.ndarray = None
    ) -> Dict[str, Any]:
        """
        Generate heatmap from person detections.
        
        Args:
            detections_per_frame: List of {frame: int, humans: [{x, y, ...}]}
            frame_width: Video frame width
            frame_height: Video frame height
            background_image: Optional background image for overlay
            
        Returns:
            Dict with heatmap_image, grid_data, statistics
        """
        # Initialize heatmap grid
        grid_rows, grid_cols = self.grid_size
        heatmap_grid = np.zeros((grid_rows, grid_cols), dtype=np.int32)
        
        # Calculate cell dimensions
        cell_width = frame_width / grid_cols
        cell_height = frame_height / grid_rows
        
        # Accumulate positions into grid
        total_positions = 0
        for frame_data in detections_per_frame:
            for human in frame_data.get('humans', []):
                x, y = human['x'], human['y']
                
                # Determine grid cell
                col = int(min(x / cell_width, grid_cols - 1))
                row = int(min(y / cell_height, grid_rows - 1))
                
                heatmap_grid[row, col] += 1
                total_positions += 1
        
        # Generate visualization
        heatmap_image = self._create_heatmap_image(
            heatmap_grid,
            frame_width,
            frame_height,
            background_image
        )
        
        # Convert grid to dict for JSON storage
        grid_data = {}
        for row in range(grid_rows):
            for col in range(grid_cols):
                if heatmap_grid[row, col] > 0:
                    grid_data[f"cell_{row}_{col}"] = int(heatmap_grid[row, col])
        
        # Calculate statistics
        hotspot_threshold = np.percentile(heatmap_grid[heatmap_grid > 0], 70) if np.any(heatmap_grid > 0) else 0
        hotspot_count = int(np.sum(heatmap_grid > hotspot_threshold))
        
        return {
            'heatmap_image': heatmap_image,
            'grid_data': grid_data,
            'total_positions': total_positions,
            'hotspot_count': hotspot_count,
            'max_density': int(heatmap_grid.max()),
            'avg_density': float(heatmap_grid.mean())
        }
    
    def _create_heatmap_image(
        self,
        heatmap_grid: np.ndarray,
        target_width: int,
        target_height: int,
        background: np.ndarray = None
    ) -> np.ndarray:
        """
        Create heatmap visualization image.
        
        Args:
            heatmap_grid: Grid with accumulated counts
            target_width: Output image width
            target_height: Output image height
            background: Optional background image
            
        Returns:
            Heatmap image (BGR format)
        """
        # Normalize grid to 0-255
        if heatmap_grid.max() > 0:
            normalized = (heatmap_grid / heatmap_grid.max() * 255).astype(np.uint8)
        else:
            normalized = heatmap_grid.astype(np.uint8)
        
        # Resize to target dimensions
        heatmap_resized = cv2.resize(normalized, (target_width, target_height), interpolation=cv2.INTER_LINEAR)
        
        # Apply colormap (JET = red for hot spots)
        heatmap_colored = cv2.applyColorMap(heatmap_resized, cv2.COLORMAP_JET)
        
        # Blend with background if provided
        if background is not None:
            # Ensure background is correct size
            if background.shape[:2] != (target_height, target_width):
                background = cv2.resize(background, (target_width, target_height))
            
            # Create alpha channel based on heatmap intensity
            alpha = (heatmap_resized / 255.0 * 0.6).astype(np.float32)  # 60% max opacity
            alpha = np.expand_dims(alpha, axis=2)
            
            # Blend
            heatmap_colored = (background * (1 - alpha) + heatmap_colored * alpha).astype(np.uint8)
        
        return heatmap_colored
    
    def create_zone_heatmap(
        self,
        detections_per_frame: List[Dict],
        zones: List[Dict],
        frame_width: int,
        frame_height: int
    ) -> Dict[str, Any]:
        """
        Generate zone-specific heatmaps.
        
        Args:
            detections_per_frame: Person detections
            zones: List of {id, polygon: [[x,y], ...]}
            frame_width: Video width
            frame_height: Video height
            
        Returns:
            Dict with per-zone statistics
        """
        zone_stats = {}
        
        for zone in zones:
            zone_id = zone['id']
            polygon = np.array(zone['polygon'], dtype=np.int32)
            
            # Count detections in zone
            count = 0
            for frame_data in detections_per_frame:
                for human in frame_data.get('humans', []):
                    point = (human['x'], human['y'])
                    if cv2.pointPolygonTest(polygon, point, False) >= 0:
                        count += 1
            
            zone_stats[zone_id] = count
        
        return zone_stats
