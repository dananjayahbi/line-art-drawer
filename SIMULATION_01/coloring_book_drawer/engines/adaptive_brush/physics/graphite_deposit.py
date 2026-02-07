"""
Graphite Deposit Calculation
==============================
Computes graphite deposit intensity at each stroke point,
combining tip pattern, paper receptivity, and pressure.
"""

import numpy as np
from .pencil_tip import PencilTip
from .paper_texture import PaperTexture


class GraphiteDeposit:
    """Calculates graphite deposit for individual stroke points."""
    
    def __init__(self, pencil_tip: PencilTip, paper: PaperTexture):
        self.tip = pencil_tip
        self.paper = paper
        
    def compute_deposit(self, y: int, x: int, pressure: float,
                        angle: float = 0.0,
                        canvas: np.ndarray = None) -> tuple:
        """
        Compute graphite deposit at position (y, x).
        
        Args:
            y, x: Canvas position (center of deposit)
            pressure: Normalized pressure [0, 1]
            angle: Stroke direction in radians
            canvas: Current canvas state for saturation awareness
            
        Returns:
            (deposit_patch, y_slice, x_slice): Deposit values and target region
        """
        # Get tip deposit pattern
        tip_pattern = self.tip.get_deposit_pattern(pressure, angle)
        ks = tip_pattern.shape[0]
        half = ks // 2
        
        if canvas is None:
            h, w = self.paper._height, self.paper._width
        else:
            h, w = canvas.shape[:2]
            
        # Compute bounds
        y0 = max(0, y - half)
        y1 = min(h, y + half + 1)
        x0 = max(0, x - half)
        x1 = min(w, x + half + 1)
        
        # Corresponding region in kernel
        ky0 = y0 - (y - half)
        ky1 = ks - ((y + half + 1) - y1)
        kx0 = x0 - (x - half)
        kx1 = ks - ((x + half + 1) - x1)
        
        if ky0 >= ky1 or kx0 >= kx1 or y0 >= y1 or x0 >= x1:
            return None, None, None
        
        tip_region = tip_pattern[ky0:ky1, kx0:kx1]
        
        # Get paper receptivity
        paper_region = self.paper.get_receptivity(y, x, half)
        # Align sizes (paper patch may be smaller near edges)
        pr_h, pr_w = paper_region.shape
        tr_h, tr_w = tip_region.shape
        min_h = min(pr_h, tr_h)
        min_w = min(pr_w, tr_w)
        
        tip_region = tip_region[:min_h, :min_w]
        paper_region = paper_region[:min_h, :min_w]
        
        # Deposit = tip_pattern * paper_receptivity
        deposit = tip_region * paper_region
        
        # Adjust target region size to match
        y1 = y0 + min_h
        x1 = x0 + min_w
        
        y_slice = slice(y0, y1)
        x_slice = slice(x0, x1)
        
        return deposit, y_slice, x_slice
    
    def compute_deposit_batch(self, points: np.ndarray, pressures: np.ndarray,
                              angles: np.ndarray = None) -> list:
        """
        Compute deposits for a batch of points.
        
        Args:
            points: (N, 2) array of (y, x) positions
            pressures: (N,) array of pressure values
            angles: (N,) array of stroke angles (optional)
            
        Returns:
            List of (deposit, y_slice, x_slice) tuples
        """
        results = []
        if angles is None:
            angles = np.zeros(len(points), dtype=np.float32)
            
        for i in range(len(points)):
            y, x = int(points[i, 0]), int(points[i, 1])
            deposit, ys, xs = self.compute_deposit(y, x, float(pressures[i]),
                                                   float(angles[i]))
            if deposit is not None:
                results.append((deposit, ys, xs))
                
        return results
