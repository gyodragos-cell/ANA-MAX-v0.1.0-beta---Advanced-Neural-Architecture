with open('c:/Users/billy/Desktop/ana-manus/test_large.json', 'w', encoding='utf-8') as f:
    for i in range(1, 10001):
        f.write(f"Linia {i}: Acesta este un test pentru OCR cu fisier mare. Verificam daca tool-ul poate procesa 10000 de linii si salva tokens corect.\n")
print("Fisier creat cu 10000 linii")
