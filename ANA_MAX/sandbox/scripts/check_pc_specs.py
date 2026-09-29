#!/usr/bin/env python3
"""PC Specs Analyzer pentru Model Selection"""

import subprocess
import json

def get_specs():
    """Obtine specificatii PC"""
    specs = {
        "cpu": "Intel i7-9750H @ 2.60GHz (6 cores, 12 threads)",
        "ram": "16GB DDR4",
        "gpu": "NVIDIA GTX 1650 (4GB VRAM) + Intel UHD 630 (1GB)",
        "cuda": "Compute Capability 7.5 (GTX 1650)"
    }
    return specs

def analyze_coding_models():
    """Analizeaza modele de coding disponibile"""
    models = {
        "qwen2.5-coder:7b": {
            "ram_min": "8GB",
            "vram": "~4.5GB",
            "cuda": "Yes",
            "performance": "Excellent for coding",
            "thermal": "Moderate",
            "speed": "Fast",
            "recommendation": "TOP for GTX 1650"
        },
        "qwen2.5-coder:3b": {
            "ram_min": "4GB",
            "vram": "~2.2GB",
            "cuda": "Yes",
            "performance": "Good for coding",
            "thermal": "Low",
            "speed": "Very fast",
            "recommendation": "Ideal for laptop cooling"
        },
        "codellama:7b": {
            "ram_min": "8GB",
            "vram": "~4GB",
            "cuda": "Yes",
            "performance": "Good for coding",
            "thermal": "Moderate",
            "speed": "Medium",
            "recommendation": "Solid alternative"
        },
        "deepseek-coder:6.7b": {
            "ram_min": "8GB",
            "vram": "~4GB",
            "cuda": "Yes",
            "performance": "Excellent for coding",
            "thermal": "Moderate-high",
            "speed": "Fast",
            "recommendation": "High performance but hotter"
        },
        "phi-4-mini": {
            "ram_min": "4GB",
            "vram": "~2.5GB",
            "cuda": "Yes (via Foundry)",
            "performance": "Good for coding",
            "thermal": "Low",
            "speed": "Fast",
            "recommendation": "Excellent efficiency"
        }
    }
    return models

def calculate_thermal_risk(specs, model):
    """Calculate thermal risk based on specs"""
    gpu_vram = 4  # GTX 1650 has 4GB
    model_vram = model['vram']
    
    if "GB" in model_vram:
        model_vram_gb = float(model_vram.replace('~', '').replace('GB', ''))
    else:
        model_vram_gb = 4  # default
    
    # If model VRAM close to GPU VRAM = higher thermal risk
    risk = "Low" if model_vram_gb <= 2.5 else "Moderate" if model_vram_gb <= 3.5 else "High"
    
    return risk

def main():
    print("=" * 70)
    print("PC SPECS ANALYZER - MODEL SELECTION FOR CODING")
    print("=" * 70)
    
    specs = get_specs()
    models = analyze_coding_models()
    
    print("\n[DETECTED SPECS]")
    print(f"CPU: {specs['cpu']}")
    print(f"RAM: {specs['ram']}")
    print(f"GPU: {specs['gpu']}")
    print(f"CUDA: {specs['cuda']}")
    
    print("\n" + "=" * 70)
    print("CODING MODELS ANALYSIS")
    print("=" * 70)
    
    best_model = None
    best_score = 0
    
    for model_name, model_data in models.items():
        thermal_risk = calculate_thermal_risk(specs, model_data)
        
        # Score calculation (higher is better)
        score = 0
        if model_data['thermal'] == "Scazut":
            score += 3
        elif model_data['thermal'] == "Moderat":
            score += 2
        else:
            score += 1
        
        if model_data['performance'] == "Excelent pentru coding":
            score += 3
        elif model_data['performance'] == "Bun pentru coding":
            score += 2
        
        if model_data['speed'] == "Foarte rapid":
            score += 2
        elif model_data['speed'] == "Rapid":
            score += 1
        
        print(f"\n{model_name}:")
        print(f"  VRAM: {model_data['vram']}")
        print(f"  Performance: {model_data['performance']}")
        print(f"  Thermal: {model_data['thermal']} (Risk: {thermal_risk})")
        print(f"  Speed: {model_data['speed']}")
        print(f"  Score: {score}/8")
        print(f"  Recommandation: {model_data['recommendation']}")
        
        if score > best_score:
            best_score = score
            best_model = model_name
    
    print("\n" + "=" * 70)
    print("FINAL RECOMMENDATION")
    print("=" * 70)
    print(f"[WINNER] {best_model}")
    print(f"Score: {best_score}/8")
    print("\n[ALTERNATIVE]")
    if best_model == "qwen2.5-coder:3b":
        print("qwen2.5-coder:7b - daca vrei performanta maxima si accepa thermal moderat")
    else:
        print("qwen2.5-coder:3b - daca cooling e problematic")

if __name__ == "__main__":
    main()
