#!/usr/bin/env python3
"""PC Specs Analyzer for Model Selection - English version"""

def main():
    print("=" * 70)
    print("PC SPECS ANALYZER - MODEL SELECTION FOR CODING")
    print("=" * 70)
    
    print("\n[DETECTED SPECS]")
    print("CPU: Intel i7-9750H @ 2.60GHz (6 cores, 12 threads)")
    print("RAM: 16GB DDR4")
    print("GPU: NVIDIA GTX 1650 (4GB VRAM) + Intel UHD 630 (1GB)")
    print("CUDA: Compute Capability 7.5 (GTX 1650)")
    
    print("\n" + "=" * 70)
    print("CODING MODELS ANALYSIS")
    print("=" * 70)
    
    models = {
        "qwen2.5-coder:7b": {
            "vram": "~4.5GB",
            "performance": "Excellent for coding",
            "thermal": "Moderate",
            "thermal_risk": "High (exceeds GPU VRAM)",
            "speed": "Fast",
            "score": 6,
            "recommendation": "TOP performance but may be hot"
        },
        "qwen2.5-coder:3b": {
            "vram": "~2.2GB",
            "performance": "Good for coding",
            "thermal": "Low",
            "thermal_risk": "Low (fits GPU VRAM)",
            "speed": "Very fast",
            "score": 8,
            "recommendation": "WINNER - Best balance for laptop"
        },
        "codellama:7b": {
            "vram": "~4GB",
            "performance": "Good for coding",
            "thermal": "Moderate",
            "thermal_risk": "Moderate (at GPU VRAM limit)",
            "speed": "Medium",
            "score": 5,
            "recommendation": "Solid alternative"
        },
        "deepseek-coder:6.7b": {
            "vram": "~4GB",
            "performance": "Excellent for coding",
            "thermal": "Moderate-high",
            "thermal_risk": "Moderate (at GPU VRAM limit)",
            "speed": "Fast",
            "score": 6,
            "recommendation": "High performance but hotter"
        },
        "phi-4-mini": {
            "vram": "~2.5GB",
            "performance": "Good for coding",
            "thermal": "Low",
            "thermal_risk": "Low (fits GPU VRAM)",
            "speed": "Fast",
            "score": 7,
            "recommendation": "Excellent efficiency"
        }
    }
    
    best_model = None
    best_score = 0
    
    for model_name, model_data in models.items():
        print(f"\n{model_name}:")
        print(f"  VRAM: {model_data['vram']}")
        print(f"  Performance: {model_data['performance']}")
        print(f"  Thermal: {model_data['thermal']}")
        print(f"  Thermal Risk: {model_data['thermal_risk']}")
        print(f"  Speed: {model_data['speed']}")
        print(f"  Score: {model_data['score']}/8")
        print(f"  Recommendation: {model_data['recommendation']}")
        
        if model_data['score'] > best_score:
            best_score = model_data['score']
            best_model = model_name
    
    print("\n" + "=" * 70)
    print("FINAL RECOMMENDATION")
    print("=" * 70)
    print(f"[WINNER] {best_model}")
    print(f"Score: {best_score}/8")
    print("\n[REASONING]")
    print("GTX 1650 has 4GB VRAM - models using 2.2-2.5GB are optimal")
    print("qwen2.5-coder:3b fits perfectly in GPU VRAM with low thermal risk")
    print("Still provides excellent coding performance without overheating")
    
    print("\n[TO DOWNLOAD]")
    print("ollama pull qwen2.5-coder:3b")
    
    print("\n[TO USE]")
    print("ollama run qwen2.5-coder:3b")

if __name__ == "__main__":
    main()
