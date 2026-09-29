"""
Setup RAG for HTML/CSS/JS Coding Knowledge
=========================================
Adauga documentatie HTML/CSS/JS in Memory Cortex pentru a imbunatati modelul
"""

from tools.memory_cortex import MemoryCortex

cortex = MemoryCortex()

print("=== RAG SETUP: HTML/CSS/JS Knowledge Base ===\n")

# HTML5 Modern Features
print("Adding HTML5 knowledge...")
cortex.remember(
    key="html5_modern_features",
    value="""
HTML5 Modern Features:
- Semantic tags: <header>, <nav>, <main>, <section>, <article>, <footer>
- Audio/Video: <audio>, <video> cu src si controls
- Forms: input types (email, date, number, range), required, pattern
- Accessibility: aria-label, role, alt text
- Meta tags: viewport, description, charset
""",
    memory_type="semantic"
)

# CSS3 Modern Features
print("Adding CSS3 knowledge...")
cortex.remember(
    key="css3_modern_features",
    value="""
CSS3 Modern Features:
- Gradients: linear-gradient(angle, color1, color2), radial-gradient()
- Flexbox: display: flex, justify-content, align-items, flex-direction
- Grid: display: grid, grid-template-columns, gap
- Animations: @keyframes, animation-name, animation-duration
- Transitions: transition-property, transition-duration, transition-timing-function
- Responsive: @media (max-width: 768px)
- Shadows: box-shadow, text-shadow
- Rounded corners: border-radius
- Transform: rotate(), scale(), translate()
""",
    memory_type="semantic"
)

# CSS Gradients
print("Adding CSS gradients...")
cortex.remember(
    key="css_gradients_examples",
    value="""
CSS Gradients Examples:
- Linear gradient: background: linear-gradient(45deg, #6a11cb, #2575fc)
- Radial gradient: background: radial-gradient(circle, #color1, #color2)
- Multiple colors: background: linear-gradient(to right, #color1, #color2, #color3)
- Gradient text: background-clip: text; -webkit-text-fill-color: transparent
""",
    memory_type="semantic"
)

# CSS Flexbox
print("Adding CSS flexbox...")
cortex.remember(
    key="css_flexbox_complete",
    value="""
CSS Flexbox Complete Guide:
- Container: display: flex
- Direction: flex-direction: row | column | row-reverse | column-reverse
- Justify content: justify-content: flex-start | center | space-between | space-around
- Align items: align-items: flex-start | center | flex-end | stretch
- Wrap: flex-wrap: nowrap | wrap | wrap-reverse
- Item: flex: 1 (grow), flex-shrink: 0, flex-basis: auto
- Responsive: flex-direction: column on mobile
""",
    memory_type="semantic"
)

# CSS Animations
print("Adding CSS animations...")
cortex.remember(
    key="css_animations_examples",
    value="""
CSS Animations Examples:
- Keyframes:
  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }
- Apply: animation: fadeIn 0.5s ease-in
- Hover animation: element:hover { animation: pulse 1s infinite; }
- Smooth scroll: html { scroll-behavior: smooth; }
- Fade in: animation: fadeIn 0.3s ease-in
- Slide in: transform: translateX(-100%); animation: slideIn 0.5s
""",
    memory_type="semantic"
)

# JavaScript Modern Features
print("Adding JavaScript knowledge...")
cortex.remember(
    key="javascript_modern_features",
    value="""
JavaScript Modern Features (ES6+):
- Arrow functions: const func = () => {}
- Template literals: `Hello ${name}`
- Destructuring: const {name, age} = person
- Spread operator: [...array], {...object}
- Async/await: async function() { await promise }
- Classes: class MyClass { constructor() {} }
- Modules: import/export
- DOM query: document.querySelector(), document.querySelectorAll()
- Event listeners: addEventListener('click', handler)
""",
    memory_type="semantic"
)

# JavaScript Form Validation
print("Adding JavaScript form validation...")
cortex.remember(
    key="javascript_form_validation",
    value="""
JavaScript Form Validation:
- Prevent default: event.preventDefault()
- Get form: document.querySelector('form')
- Get inputs: form.querySelectorAll('input')
- Validate: input.checkValidity()
- Custom validation: input.setCustomValidity('message')
- Submit handler: form.addEventListener('submit', (e) => { e.preventDefault(); validate(); })
- Real-time: input.addEventListener('input', validate)
- Show errors: create error element, append after input
""",
    memory_type="semantic"
)

# JavaScript Smooth Scroll
print("Adding JavaScript smooth scroll...")
cortex.remember(
    key="javascript_smooth_scroll",
    value="""
JavaScript Smooth Scroll:
- Scroll to element: element.scrollIntoView({ behavior: 'smooth' })
- Scroll to top: window.scrollTo({ top: 0, behavior: 'smooth' })
- Scroll to position: window.scrollTo({ top: 500, behavior: 'smooth' })
- Navigation click: document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
      e.preventDefault();
      document.querySelector(this.getAttribute('href')).scrollIntoView({ behavior: 'smooth' });
    });
  });
""",
    memory_type="semantic"
)

# Mobile Menu Toggle
print("Adding JavaScript mobile menu...")
cortex.remember(
    key="javascript_mobile_menu",
    value="""
JavaScript Mobile Menu Toggle:
- Toggle class: menu.classList.toggle('active')
- Add event: hamburger.addEventListener('click', () => menu.classList.toggle('active'))
- Close on click outside: document.addEventListener('click', (e) => {
    if (!menu.contains(e.target) && !hamburger.contains(e.target)) {
      menu.classList.remove('active');
    }
  });
- Close on link click: menu.querySelectorAll('a').forEach(link => {
    link.addEventListener('click', () => menu.classList.remove('active'));
  });
""",
    memory_type="semantic"
)

# Modern Design Patterns
print("Adding modern design patterns...")
cortex.remember(
    key="modern_design_principles",
    value="""
Modern Web Design Principles:
- Color schemes: Use complementary or analogous colors
- Gradients: Subtle gradients for depth
- Typography: Sans-serif fonts (Inter, Roboto, Open Sans)
- Spacing: Consistent padding/margins (4px, 8px, 16px, 32px, 64px)
- Shadows: Subtle box-shadow for depth (0 2px 4px rgba(0,0,0,0.1))
- Rounded corners: border-radius: 4px-8px for modern look
- Hover effects: Transform, color change, shadow increase
- Transitions: transition: all 0.3s ease
- White space: Generous spacing for readability
- Mobile-first: Design for mobile, then scale up
""",
    memory_type="semantic"
)

# Color Schemes
print("Adding color schemes...")
cortex.remember(
    key="modern_color_schemes",
    value="""
Modern Color Schemes:
- Purple/Blue Gradient: linear-gradient(45deg, #6a11cb, #2575fc)
- Green/Teal: linear-gradient(45deg, #11998e, #38ef7d)
- Orange/Red: linear-gradient(45deg, #f12711, #f5af19)
- Dark theme: #1a1a2e, #16213e, #0f3460
- Light theme: #ffffff, #f8f9fa, #e9ecef
- Accent colors: #6a11cb (purple), #2575fc (blue), #38ef7d (green)
- Neutral: #6c757d, #495057, #343a40
- Success: #28a745, Warning: #ffc107, Danger: #dc3545, Info: #17a2b8
""",
    memory_type="semantic"
)

# Responsive Design
print("Adding responsive design...")
cortex.remember(
    key="responsive_design_best_practices",
    value="""
Responsive Design Best Practices:
- Mobile breakpoints: 320px, 375px, 414px, 768px, 1024px, 1200px
- Media queries: @media (max-width: 768px) { ... }
- Fluid typography: font-size: clamp(1rem, 2.5vw, 1.5rem)
- Fluid images: max-width: 100%, height: auto
- Flexbox for layout: display: flex, flex-wrap: wrap
- Grid for complex layouts: display: grid, grid-template-columns: repeat(auto-fit, minmax(300px, 1fr))
- Mobile menu: Hamburger icon, slide-in or dropdown
- Touch targets: Minimum 44x44px for mobile
- Readable text: 16px minimum font size on mobile
""",
    memory_type="semantic"
)

# Accessibility
print("Adding accessibility...")
cortex.remember(
    key="web_accessibility_a11y",
    value="""
Web Accessibility (A11y) Best Practices:
- Alt text: <img src="image.jpg" alt="Description">
- Semantic HTML: Use <nav>, <main>, <article>, <section>
- ARIA labels: <button aria-label="Close menu">
- Heading hierarchy: h1 > h2 > h3 (don't skip)
- Color contrast: Minimum 4.5:1 for text
- Focus states: outline: 2px solid #color for keyboard navigation
- Form labels: <label for="input-id">Label</label>
- Screen readers: aria-live, aria-hidden, aria-expanded
- Skip links: Skip to main content link
- Keyboard navigation: All interactive elements accessible via keyboard
""",
    memory_type="semantic"
)

print("\n=== RAG SETUP COMPLETE ===")
print("Knowledge base added to Memory Cortex!")
print("Model will now have access to HTML/CSS/JS documentation when coding.")
