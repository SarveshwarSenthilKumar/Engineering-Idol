#!/usr/bin/env python3
"""
SCOPE Documentation Flask App
Simple standalone documentation server
"""

from flask import Flask, render_template, send_from_directory
import os

app = Flask(__name__)

@app.route('/')
def index():
    """Serve the main documentation page"""
    return render_template('scope-docs.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files"""
    return send_from_directory('static', filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    print(f"📚 SCOPE Documentation running on http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
