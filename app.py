#!/usr/bin/env python3
"""
Gmail Storage Optimizer - Web Interface
Author: Shabul

Flask web application providing a user-friendly interface for Gmail cleaning.
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_cors import CORS
import json
import os
import threading
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Global state for tracking running processes
cleaner_status = {
    "running": False,
    "progress": 0,
    "current_keyword": "",
    "logs": []
}

@app.route('/')
def dashboard():
    """Main dashboard page"""
    stats = get_stats()
    return render_template('dashboard.html', stats=stats)

@app.route('/analyzer')
def analyzer():
    """Analyzer page"""
    return render_template('analyzer.html')

@app.route('/keywords')
def keywords_page():
    """Keywords management page"""
    keywords_data = load_keywords()
    return render_template('keywords.html', keywords=keywords_data)

@app.route('/cleaner')
def cleaner():
    """Cleaner page"""
    return render_template('cleaner.html', status=cleaner_status)

@app.route('/history')
def history():
    """History viewer page"""
    deleted = load_json_file('deleted_history.json')
    safe_skipped = load_json_file('safe_not_deleted.json')
    return render_template('history.html', deleted=deleted, safe_skipped=safe_skipped)

# API Endpoints

@app.route('/api/run-analyzer', methods=['POST'])
def run_analyzer():
    """Run the analyzer script"""
    data = request.json
    pages = data.get('pages', 500)
    
    # TODO: Run analyzer in background thread
    return jsonify({"status": "started", "message": f"Analyzer started with {pages} pages"})

@app.route('/api/keywords', methods=['GET', 'POST', 'DELETE'])
def api_keywords():
    """Manage keywords"""
    if request.method == 'GET':
        return jsonify(load_keywords())
    
    elif request.method == 'POST':
        data = request.json
        email = data.get('email')
        if email:
            add_keyword(email)
            return jsonify({"status": "success", "message": f"Added {email}"})
        return jsonify({"status": "error", "message": "No email provided"}), 400
    
    elif request.method == 'DELETE':
        data = request.json
        email = data.get('email')
        if email:
            remove_keyword(email)
            return jsonify({"status": "success", "message": f"Removed {email}"})
        return jsonify({"status": "error", "message": "No email provided"}), 400

@app.route('/api/run-cleaner', methods=['POST'])
def run_cleaner():
    """Start the cleaner process"""
    if cleaner_status["running"]:
        return jsonify({"status": "error", "message": "Cleaner already running"}), 400
    
    # TODO: Run cleaner in background thread
    cleaner_status["running"] = True
    cleaner_status["logs"] = []
    return jsonify({"status": "started", "message": "Cleaner started"})

@app.route('/api/cleaner-status')
def get_cleaner_status():
    """Get current cleaner status"""
    return jsonify(cleaner_status)

# Helper Functions

def get_stats():
    """Get dashboard statistics"""
    deleted = load_json_file('deleted_history.json')
    safe_skipped = load_json_file('safe_not_deleted.json')
    keywords_data = load_keywords()
    
    return {
        "total_deleted": len(deleted),
        "total_safe_skipped": len(safe_skipped),
        "total_keywords": len(keywords_data.get('emails', [])),
        "total_protected": len(keywords_data.get('protected_emails', []))
    }

def load_keywords():
    """Load keywords from keywords.py"""
    try:
        import keywords
        return {
            "emails": getattr(keywords, 'emails', []),
            "protected_emails": getattr(keywords, 'protected_emails', [])
        }
    except ImportError:
        return {"emails": [], "protected_emails": []}

def add_keyword(email):
    """Add a keyword to keywords.py"""
    keywords_data = load_keywords()
    if email not in keywords_data['emails']:
        keywords_data['emails'].append(email)
        save_keywords(keywords_data)

def remove_keyword(email):
    """Remove a keyword from keywords.py"""
    keywords_data = load_keywords()
    if email in keywords_data['emails']:
        keywords_data['emails'].remove(email)
        save_keywords(keywords_data)

def save_keywords(keywords_data):
    """Save keywords to keywords.py"""
    with open('keywords.py', 'w') as f:
        f.write('emails = [\n')
        for email in keywords_data['emails']:
            f.write(f'    "{email}",\n')
        f.write(']\n\n')
        f.write('# Emails in this list will be skipped by the cleaner\n')
        f.write('protected_emails = [\n')
        for email in keywords_data.get('protected_emails', []):
            f.write(f'    "{email}",\n')
        f.write(']\n')

def load_json_file(filename):
    """Load a JSON file"""
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []

if __name__ == '__main__':
    app.run(debug=True, port=5000)
