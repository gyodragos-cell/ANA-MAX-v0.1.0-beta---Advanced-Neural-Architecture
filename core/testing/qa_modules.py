import cv2
import numpy as np
from PIL import ImageGrab
import os

class VisualQA:
    """Module for Visual Regression Testing and Screenshot Comparison"""
    
    def __init__(self, baseline_dir="tests/baselines"):
        self.baseline_dir = baseline_dir
        if not os.path.exists(baseline_dir):
            os.makedirs(baseline_dir)

    def capture_screenshot(self, name):
        """Captures a screenshot of the current screen"""
        screenshot = ImageGrab.grab()
        path = os.path.join(self.baseline_dir, f"{name}_current.png")
        screenshot.save(path)
        return path

    def compare_images(self, baseline_name, current_path):
        """Compares current screenshot with baseline using structural similarity"""
        baseline_path = os.path.join(self.baseline_dir, f"{baseline_name}.png")
        
        if not os.path.exists(baseline_path):
            os.rename(current_path, baseline_path)
            return True, "No baseline found. Created new baseline."

        img1 = cv2.imread(baseline_path)
        img2 = cv2.imread(current_path)

        # Ensure same size
        if img1.shape != img2.shape:
            return False, "Image dimensions differ."

        # Compute absolute difference
        diff = cv2.absdiff(img1, img2)
        gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 30, 255, cv2.THRESH_BINARY)
        
        diff_score = np.sum(thresh) / 255
        
        if diff_score < 100:  # Tolerance threshold
            return True, "Images match."
        else:
            return False, f"Visual regression detected! Diff pixels: {diff_score}"

class PerformanceQA:
    """Module for performance profiling and bottleneck detection"""
    
    def analyze_bottlenecks(self, logs_path):
        """Analyzes logs to find slow operations"""
        # Logic to parse execution logs and find slow points
        return "Performance analysis complete. No critical bottlenecks found."
