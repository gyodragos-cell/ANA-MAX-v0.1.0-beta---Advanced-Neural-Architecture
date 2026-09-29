import sys
sys.path.append('C:/Users/billy/Desktop/Unlimited-OCR-main')

# Test direct Transformers API (fara server)
try:
    from transformers import AutoModel, AutoTokenizer
    import torch
    
    model_name = 'baidu/Unlimited-OCR'
    
    print("Incarcare tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    
    print("Incarcare model...")
    model = AutoModel.from_pretrained(
        model_name,
        trust_remote_code=True,
        use_safetensors=True,
        torch_dtype=torch.float16,  # Folosim float16 pentru economie memorie
    )
    
    print("Model incarcat cu succes!")
    print(f"Model device: {model.device}")
    
except Exception as e:
    print(f"Eroare la incarcare model: {e}")
    print("Probabil nu este instalat Transformers sau nu este GPU disponibil.")
