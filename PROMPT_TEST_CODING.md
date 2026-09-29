# PROMPT TEST CODING - Nivel Model qwen2.5-coder:3b

---

## Prompt de Test

```
Creeaza un site HTML complet cu urmatoarele caracteristici:

1. **Structura HTML5** semantica
2. **CSS modern** cu:
   - Gradient background
   - Flexbox/Grid layout
   - Responsive design
   - Hover effects
   - Animations
3. **JavaScript** pentru:
   - Interactive elements
   - Dynamic content
   - Event handlers
4. **Continut:**
   - Hero section cu call-to-action
   - Feature cards
   - Contact form cu validation
   - Footer

5. **Design requirements:**
   - Color scheme: Modern purple/blue gradient
   - Typography: Sans-serif (Inter/Roboto)
   - Rounded corners, shadows
   - Smooth transitions

6. **Functionalitati:**
   - Mobile menu toggle
   - Scroll animations
   - Form validation in real-time
   - Smooth scroll navigation

**Dupa creare:**
- Salveaza fisierul ca `index.html` pe desktop
- Deschide in browser
- Verifica functionalitatile

**Raporteaza:**
- Timpul de creare
- Calitatea codului
- Erori intampinate
- Nivelul de completitudine
```

---

## Prompt Simplificat (Daca vrei test rapid)

```
Creeaza un website HTML/CSS/JS modern cu:
- Hero section
- 3 feature cards
- Contact form
- Responsive design
- Animations

Salveaza ca index.html pe desktop si deschide in browser.
```

---

## Prompt Avansat (Daca vrei test complet)

```
Creeaza o aplicatie web dashboard cu:

**Frontend:**
- HTML5 + CSS3 + JavaScript (ES6+)
- Tailwind CSS (via CDN)
- Alpine.js pentru interactivitate

**Features:**
- Sidebar navigation
- Dashboard cu charts (Chart.js)
- Data table cu sort/filter
- Dark mode toggle
- User profile card
- Notification system
- Real-time clock

**Requirements:**
- Single file HTML
- LocalStorage pentru persistence
- Responsive design
- Smooth animations
- Error handling

**After creation:**
- Save as dashboard.html on desktop
- Open in browser
- Test all features
- Report performance and code quality
```

---

## Cum sa rulezi testul:

### Optiunea 1: Prin Chat Ana
1. Deschide chat-ul Ana
2. Copiaza prompt-ul
3. Trimite
4. Urmareste procesul de creare
5. Verifica rezultatul

### Optiunea 2: Prin MCP
```bash
curl -X POST http://127.0.0.1:8766/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc":"2.0",
    "id":1,
    "method":"tools/call",
    "params":{
      "name":"terminal",
      "arguments":{
        "operation":"run",
        "command":"echo PROMPT_AICI"
      }
    }
  }'
```

### Optiunea 3: Direct in terminal
```bash
# Creaza un fisier cu prompt-ul
echo "PROMPT_AICI" > test_prompt.txt

# Da-l modelului prin Ana
python -c "from core.backends.ollama_backend import OllamaBackend; backend = OllamaBackend(); print(backend.generate('$(cat test_prompt.txt)'))"
```

---

## Ce sa verifici:

### 1. **Cod Quality**
- HTML valid?
- CSS well-structured?
- JavaScript fara erori?
- Best practices?

### 2. **Functionalitate**
- Responsive?
- Interactive elements work?
- Animations smooth?
- Form validation?

### 3. **Design**
- Modern aesthetics?
- Good UX?
- Accessibility?
- Color contrast?

### 4. **Performance**
- Load time?
- File size?
- Render performance?

### 5. **Model Behavior**
- Speed of generation?
- Accuracy?
- Creativity?
- Follows instructions?

---

## Rating Scale (1-10)

### **Coding Skills:**
- 1-3: Basic HTML, no CSS/JS
- 4-6: Good HTML/CSS, basic JS
- 7-8: Modern HTML/CSS/JS, frameworks
- 9-10: Professional, production-ready

### **Creativity:**
- 1-3: Generic template
- 4-6: Some originality
- 7-8: Creative design
- 9-10: Unique, innovative

### **Technical Accuracy:**
- 1-3: Many errors
- 4-6: Minor issues
- 7-8: Mostly correct
- 9-10: Flawless

---

## Prompt pentru Test Specific (Tool Calling)

```
Task: Creeaza un site HTML modern si deschide-l in browser

Use tools:
1. Create file: write HTML/CSS/JS code to C:\Users\billy\Desktop\index.html
2. Open browser: Use desktop_control or browser_control to open the file
3. Test functionality: Verify elements work correctly

Report:
- File created successfully?
- Browser opened?
- All features working?
- Any errors encountered?
```

---

**Care prompt vrei sa folosesti?**
