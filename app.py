import os
import io
import traceback
import json
import uuid
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, Response
from werkzeug.utils import secure_filename

# Import from our libraries
from libraries import extract_text_from_pdf, call_ai_api, get_last_model_used

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['GENERATED_FOLDER'] = 'static/generated'
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}

# Ensure folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['GENERATED_FOLDER'], exist_ok=True)

# Store active jobs in memory (for simplicity, use a dict)
active_jobs = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Only PDF files are allowed'}), 400
    
    try:
        # Create a unique job ID
        job_id = str(uuid.uuid4())
        
        # Save file temporarily
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{job_id}_{filename}")
        file.save(filepath)
        
        # Extract text from PDF
        resume_text = extract_text_from_pdf(filepath)
        
        if not resume_text.strip():
            os.remove(filepath)
            return jsonify({'error': 'Could not extract text from PDF. Please ensure it contains text.'}), 400
        
        # Store job info
        active_jobs[job_id] = {
            'filepath': filepath,
            'filename': filename,
            'resume_text': resume_text,
            'file_size': os.path.getsize(filepath),
            'status': 'uploaded',
            'created_at': datetime.now().isoformat()
        }
        
        # Clean up old files (keep only last 10 files)
        cleanup_old_files(app.config['UPLOAD_FOLDER'], max_files=10)
        cleanup_old_files(app.config['GENERATED_FOLDER'], max_files=10)
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'filename': filename,
            'fileSize': f"{(os.path.getsize(filepath) / (1024 * 1024)):.2f} MB"
        })
        
    except Exception as e:
        app.logger.error(f"Upload error: {str(e)}")
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/generate', methods=['POST'])
def generate_portfolio():
    job_id = request.json.get('job_id')
    
    if not job_id or job_id not in active_jobs:
        return jsonify({'error': 'Invalid job ID or file not uploaded'}), 400
    
    try:
        job = active_jobs[job_id]
        resume_text = job['resume_text']
        
        # Update job status
        job['status'] = 'generating'
        job['generation_started'] = datetime.now().isoformat()
        
        # Load prompt template
        with open('prompt_template.txt', 'r') as f:
            prompt_template = f.read()
        
        # Format prompt with resume text
        prompt = prompt_template.format(resume_text=resume_text)
        
        # Call AI API
        app.logger.info(f"Calling AI API for job {job_id}...")
        
        try:
            # ai_response, model_used = call_ai_api(prompt)
            ai_response = call_ai_api(prompt)
            model_used = "AI"  # Generic name for frontend if needed
        except Exception as ai_error:
            app.logger.error(f"AI API error: {ai_error}")
            job['status'] = 'failed'
            job['error'] = str(ai_error)
            return jsonify({
                'error': f'AI generation failed: {str(ai_error)}'
            }), 500
        
        if not ai_response:
            job['status'] = 'failed'
            return jsonify({'error': 'AI returned empty response'}), 500
        
        # Parse AI response and create complete HTML
        complete_html = parse_and_create_complete_html(ai_response)
        
        if not complete_html:
            job['status'] = 'failed'
            return jsonify({'error': 'Could not parse AI response'}), 500
        
        # Save generated HTML to file
        html_filename = f"{job_id}_portfolio.html"
        html_filepath = os.path.join(app.config['GENERATED_FOLDER'], html_filename)
        
        with open(html_filepath, 'w', encoding='utf-8') as f:
            f.write(complete_html)
        
        # Update job info
        job['status'] = 'completed'
        job['generated_html_path'] = html_filepath
        job['model_used'] = model_used  # Store for backend reference only
        job['completed_at'] = datetime.now().isoformat()
        job['html_size'] = len(complete_html)
        
        return jsonify({
            'success': True,
            'message': 'Portfolio generated successfully!',
            'job_id': job_id,
            'preview_url': f'/preview/{job_id}',
            'download_url': f'/download/{job_id}',
            'view_url': f'/view/{job_id}'
        })
        
    except Exception as e:
        app.logger.error(f"Generation error: {str(e)}\n{traceback.format_exc()}")
        if job_id in active_jobs:
            active_jobs[job_id]['status'] = 'failed'
            active_jobs[job_id]['error'] = str(e)
        return jsonify({'error': f'Generation failed: {str(e)}'}), 500

@app.route('/preview/<job_id>')
def preview(job_id):
    if job_id not in active_jobs or active_jobs[job_id]['status'] != 'completed':
        return redirect(url_for('index'))
    
    try:
        job = active_jobs[job_id]
        with open(job['generated_html_path'], 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        return Response(html_content, mimetype='text/html')
        
    except Exception as e:
        app.logger.error(f"Preview error: {str(e)}")
        return f"<h1>Error loading preview</h1><p>{str(e)}</p>"

@app.route('/view/<job_id>')
def view_portfolio(job_id):
    if job_id not in active_jobs or active_jobs[job_id]['status'] != 'completed':
        return redirect(url_for('index'))
    
    try:
        job = active_jobs[job_id]
        
        # Read the generated HTML
        with open(job['generated_html_path'], 'r', encoding='utf-8') as f:
            portfolio_html = f.read()
        
        # Extract just the body content (remove head, etc.)
        body_start = portfolio_html.find('<body>')
        body_end = portfolio_html.find('</body>')
        
        if body_start != -1 and body_end != -1:
            body_content = portfolio_html[body_start + 6:body_end]
        else:
            body_content = portfolio_html
        
        # Create a view page with the portfolio
        view_html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Portfolio Preview by PortfolioGen</title>
            <!-- Bootstrap 5 CSS -->
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <!-- Font Awesome -->
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
            <style>
                body {{ 
                    font-family: Arial, sans-serif; 
                    margin: 0; 
                    padding: 0; 
                    background: #f5f5f5;
                }}
                .header {{
                    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
                    color: white;
                    padding: 25px;
                    text-align: center;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .actions {{
                    text-align: center;
                    padding: 25px;
                    background: white;
                    margin: 20px auto;
                    max-width: 1400px;
                    border-radius: 10px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                }}
                .btn-portfolio {{
                    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
                    color: white;
                    padding: 12px 30px;
                    border: none;
                    border-radius: 8px;
                    cursor: pointer;
                    text-decoration: none;
                    display: inline-block;
                    margin: 0 10px;
                    font-weight: bold;
                    font-size: 1.1em;
                    transition: transform 0.2s;
                }}
                .btn-portfolio:hover {{
                    transform: translateY(-2px);
                    color: white;
                    text-decoration: none;
                    box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
                }}
                .portfolio-container {{
                    background: white;
                    margin: 20px auto;
                    max-width: 1400px;
                    border-radius: 10px;
                    overflow: hidden;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    min-height: 500px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1><i class="fas fa-rocket me-2"></i>Portfolio Preview</h1>
                <p class="lead">Generated from: {job['filename']}</p>
            </div>
            
            <div class="actions container">
                <a href="/download/{job_id}" class="btn-portfolio">
                    <i class="fas fa-download me-2"></i>Download Portfolio
                </a>
                <a href="/" class="btn-portfolio" style="background: linear-gradient(135deg, #6b7280 0%, #4b5563 100%);">
                    <i class="fas fa-home me-2"></i>Back to Home
                </a>
                <a href="/preview/{job_id}" target="_blank" class="btn-portfolio" style="background: linear-gradient(135deg, #10b981 0%, #059669 100%);">
                    <i class="fas fa-external-link-alt me-2"></i>Open in New Tab
                </a>
            </div>
            
            <div class="portfolio-container">
                <iframe 
                    src="/preview/{job_id}" 
                    style="width: 100%; height: 800px; border: none;"
                    title="Portfolio Preview"
                ></iframe>
            </div>
            
            <div class="text-center mt-4 mb-5">
                <p class="text-muted">
                    <i class="fas fa-lightbulb me-2"></i>
                    This portfolio was generated using PortfolioGen. You can download and customize it as needed.
                </p>
            </div>
        </body>
        </html>
        """
        
        return view_html
        
    except Exception as e:
        app.logger.error(f"View error: {str(e)}")
        return f"<h1>Error loading portfolio</h1><p>{str(e)}</p>"

@app.route('/download/<job_id>')
def download(job_id):
    if job_id not in active_jobs or active_jobs[job_id]['status'] != 'completed':
        return redirect(url_for('index'))
    
    try:
        job = active_jobs[job_id]
        html_filepath = job['generated_html_path']
        
        # Generate filename
        filename = job['filename']
        base_name = os.path.splitext(filename)[0]
        download_filename = f"{base_name}_portfolio_{datetime.now().strftime('%Y%m%d')}.html"
        
        # Read file content
        with open(html_filepath, 'rb') as f:
            file_content = f.read()
        
        # Create response with HTML file
        response = send_file(
            io.BytesIO(file_content),
            as_attachment=True,
            download_name=download_filename,
            mimetype='text/html'
        )
        
        return response
        
    except Exception as e:
        app.logger.error(f"Download error: {str(e)}")
        return jsonify({'error': 'Download failed'}), 500

@app.route('/api/model')
def get_model_info():
    model_info = get_last_model_used()
    return jsonify({
        'status': 'active',
        'services_available': {
            'gemini': model_info.get('gemini_available', False),
            'groq': model_info.get('groq_available', False)
        }
    })

@app.route('/job/<job_id>/status')
def job_status(job_id):
    if job_id not in active_jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = active_jobs[job_id]
    return jsonify({
        'job_id': job_id,
        'status': job['status'],
        'filename': job['filename'],
        'created_at': job['created_at'],
        'error': job.get('error')
    })

@app.route('/cleanup', methods=['POST'])
def cleanup():
    try:
        # Clean up old files
        cleanup_old_files(app.config['UPLOAD_FOLDER'], max_files=5)
        cleanup_old_files(app.config['GENERATED_FOLDER'], max_files=5)
        
        # Clean up old jobs (older than 1 hour)
        current_time = datetime.now()
        jobs_to_delete = []
        
        for job_id, job in list(active_jobs.items()):
            created_at = datetime.fromisoformat(job['created_at'])
            age = (current_time - created_at).total_seconds() / 3600  # hours
            
            if age > 1:  # Delete jobs older than 1 hour
                jobs_to_delete.append(job_id)
        
        for job_id in jobs_to_delete:
            job = active_jobs.pop(job_id, None)
            if job and 'generated_html_path' in job and os.path.exists(job['generated_html_path']):
                try:
                    os.remove(job['generated_html_path'])
                except:
                    pass
        
        return jsonify({
            'success': True,
            'message': f'Cleaned up {len(jobs_to_delete)} old jobs',
            'active_jobs': len(active_jobs)
        })
        
    except Exception as e:
        app.logger.error(f"Cleanup error: {str(e)}")
        return jsonify({'error': 'Cleanup failed'}), 500

# Helper functions
def parse_and_create_complete_html(ai_text):
    try:
        # Initialize variables
        html_content = ""
        css_content = ""
        js_content = ""
        
        # Simple parsing logic
        if '===HTML===' in ai_text:
            parts = ai_text.split('===HTML===')
            if len(parts) > 1:
                remaining = parts[1]
                if '===CSS===' in remaining:
                    html_parts = remaining.split('===CSS===')
                    html_content = html_parts[0].strip()
                    remaining_css = html_parts[1] if len(html_parts) > 1 else ""
                    if '===JS===' in remaining_css:
                        css_parts = remaining_css.split('===JS===')
                        css_content = css_parts[0].strip()
                        js_content = css_parts[1].strip() if len(css_parts) > 1 else ""
                    else:
                        css_content = remaining_css.strip()
                else:
                    html_content = remaining.strip()
        
        # Clean up code blocks markers
        html_content = html_content.replace('```html', '').replace('```', '').strip()
        css_content = css_content.replace('```css', '').replace('```', '').strip()
        js_content = js_content.replace('```javascript', '').replace('```js', '').replace('```', '').strip()
        
        # If parsing failed, use simpler extraction
        if not html_content:
            # Try to find HTML between markers
            if '<!DOCTYPE' in ai_text:
                html_content = ai_text[ai_text.find('<!DOCTYPE'):]
            elif '<html' in ai_text:
                html_content = ai_text[ai_text.find('<html'):]
            else:
                html_content = ai_text
        
        # Create complete HTML document
        complete_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Generated Portfolio</title>
    <!-- Bootstrap 5 CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- Font Awesome -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <!-- Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        /* Base styles */
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Poppins', -apple-system, BlinkMacSystemFont, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f8fafc;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px;
        }}
        
        section {{
            padding: 80px 0;
        }}
        
        /* Responsive design */
        @media (max-width: 768px) {{
            .container {{
                padding: 0 15px;
            }}
            
            section {{
                padding: 60px 0;
            }}
        }}
        
        /* AI Generated CSS */
        {css_content if css_content else '/* No CSS generated by AI */'}
    </style>
</head>
<body>
    <!-- AI Generated Portfolio -->
    {html_content if html_content else '<!-- No HTML generated by AI -->'}
    
    <!-- Bootstrap 5 JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    
    <!-- AI Generated JavaScript -->
    <script>
        {js_content if js_content else '// No JavaScript generated by AI'}
    </script>
    
    <!-- Simple footer -->
    <div style="background: #1f2937; color: white; padding: 20px; text-align: center; margin-top: 50px;">
        <p style="margin: 0; font-size: 0.9em; opacity: 0.8;">
            Generated with PortfolioGen | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </p>
    </div>
</body>
</html>"""
        
        return complete_html
        
    except Exception as e:
        app.logger.error(f"HTML creation error: {str(e)}")
        # Return a simple HTML as fallback
        return f"""<!DOCTYPE html>
<html>
<head>
    <title>Portfolio Generated by PortfolioGen</title>
    <style>
        body {{ 
            font-family: Arial, sans-serif; 
            padding: 40px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 100vh;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background: rgba(255,255,255,0.1);
            padding: 40px;
            border-radius: 20px;
            backdrop-filter: blur(10px);
        }}
        .error {{ 
            color: #ff6b6b;
            background: rgba(0,0,0,0.2);
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
        }}
        pre {{
            background: rgba(0,0,0,0.3);
            padding: 20px;
            border-radius: 10px;
            overflow: auto;
            color: #f1f5f9;
            max-height: 400px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Portfolio Generated Successfully!</h1>
        <div class="error">
            <p>Note: There was an issue parsing the AI response.</p>
        </div>
        <pre>
{ai_text[:3000] + '...' if len(ai_text) > 3000 else ai_text}
        </pre>
        <p style="margin-top: 30px;">
            <a href="/" style="color: white; background: #6366f1; padding: 10px 20px; border-radius: 5px; text-decoration: none;">
                Back to Generator
            </a>
        </p>
    </div>
</body>
</html>"""

def cleanup_old_files(folder, max_files=10):
    try:
        files = []
        for filename in os.listdir(folder):
            filepath = os.path.join(folder, filename)
            if os.path.isfile(filepath):
                files.append((filepath, os.path.getmtime(filepath)))
        
        # Sort by modification time (oldest first)
        files.sort(key=lambda x: x[1])
        
        # Remove oldest files if we have more than max_files
        while len(files) > max_files:
            filepath, _ = files.pop(0)
            try:
                os.remove(filepath)
                app.logger.info(f"Cleaned up old file: {filepath}")
            except:
                pass
                
    except Exception as e:
        app.logger.error(f"Cleanup error: {str(e)}")

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File too large. Maximum size is 10MB.'}), 413

if __name__ == '__main__':
    # Clean up on startup
    cleanup_old_files(app.config['UPLOAD_FOLDER'], max_files=5)
    cleanup_old_files(app.config['GENERATED_FOLDER'], max_files=5)
    
    print("=" * 60)
    print("PortfolioGen")
    print("=" * 60)
    
    # Check available models
    model_info = get_last_model_used()
    print(f"Available Models:")
    print(f"Gemini: {'Available' if model_info['gemini_available'] else 'Not available'}")
    print(f"Groq: {'Available' if model_info['groq_available'] else 'Not available'}")
    print("=" * 60)
    
    app.run(debug=True, port=5000)