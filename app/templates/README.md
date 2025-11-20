# Frontend Templates

This directory contains Jinja2 templates for the Company Credit Rating System web interface.

## Templates

- **base.html** - Base template with navigation, footer, and common includes
- **index.html** - Home page
- **search.html** - Company search page with autocomplete
- **rating.html** - Rating display page with metrics and charts
- **history.html** - Historical ratings timeline
- **methodology.html** - Methodology information page

## Template Inheritance

All templates extend `base.html` which provides:
- Navigation bar
- Footer
- Bootstrap 5 CSS
- Chart.js library
- Custom CSS and JavaScript

## Blocks

Templates can override these blocks from `base.html`:
- `{% block title %}` - Page title
- `{% block content %}` - Main content area
- `{% block extra_head %}` - Additional head content
- `{% block extra_scripts %}` - Additional scripts

## Static Assets

Templates reference static assets using Flask's `url_for()`:
- CSS: `{{ url_for('static', filename='css/style.css') }}`
- JS: `{{ url_for('static', filename='js/main.js') }}`

## Usage

Templates are rendered by Flask routes in `app/main.py`:

```python
@app.route('/')
def index():
    return render_template('index.html')
```

## Development

When modifying templates:
1. Edit the template file
2. Refresh the browser (Flask auto-reloads in debug mode)
3. Check browser console for JavaScript errors
4. Verify responsive design on different screen sizes
