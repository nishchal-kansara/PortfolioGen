# PortfolioGen - AI Powered Portfolio Generator

PortfolioGen is an innovative web application that transforms resumes into professional portfolio websites using artificial intelligence. The platform allows users to upload their resumes in PDF format and automatically generates a fully functional, responsive portfolio website in minutes, eliminating the need for coding or design skills.

This solution bridges the gap between traditional resumes and modern digital portfolios by leveraging AI to analyze resume content and produce customized web portfolios that showcase professional experience, skills, and accomplishments in an engaging online format.

# Core Features
## Intelligent Resume Processing
- PDF resume upload with text extraction capabilities
- Automated content analysis and structuring
- Support for standard resume formats and layouts

## AI-Powered Generation
- Automatic conversion of resume content to portfolio sections
- Smart layout selection based on content type and volume
- Responsive design implementation for all device sizes

## Professional Output
- Complete HTML, CSS, and JavaScript files
- Clean, modern design templates
- Optimized for performance and accessibility
- Easy customization options for further personalization

## User Experience
- Simple three-step process: Upload, Generate, Download
- Real-time progress tracking during generation
- Preview functionality before final download
- Intuitive interface with clear guidance at each step

# How It Works
1. Upload Resume: Users upload their professional resume in PDF format through a secure upload interface. The system validates file type and size, then extracts text content for processing.
2. AI Analysis and Generation: Advanced AI algorithms analyze the extracted resume content, identifying key sections such as professional experience, education, skills, and projects. The system then generates appropriate HTML, CSS, and JavaScript code to create a cohesive portfolio website.
3. Preview and Download: Users can preview their generated portfolio in a browser before downloading the complete website package as a single HTML file. The output is ready for immediate use or further customization.

# Technology Stack
## Frontend
- HTML5 with semantic markup
- CSS3 with custom properties and modern layouts
- JavaScript for interactive functionality
- Bootstrap 5 for responsive framework
- Font Awesome for iconography
- Circular Std font for typography

## Backend
- Python Flask web framework
- PDF text extraction using pdfplumber
- AI integration with Google Gemini API
- Fallback support with Groq API
- Session-based job management
- File handling and storage system

## Development Tools
- Environment configuration via python-dotenv
- UUID generation for job tracking
- Comprehensive error handling
- Logging for debugging and monitoring
- File cleanup automation

# Project Structure
```
PortfolioGen/
├── app.py                    # Main Flask application
├── libraries.py              # Core AI and PDF processing logic
├── prompt_template.txt       # AI generation instructions
├── requirements.txt          # Python dependencies
├── .env                      # Environment configuration
├── static/
│   ├── uploads/             # Temporary resume storage
│   └── generated/           # Generated portfolio files
└── templates/
    └── index.html           # Frontend interface
```

# Installation
1. Clone or download the project files
```git clone https://github.com/nishchal-kansara/PortfolioGen.git```
2. Install required dependencies
```pip install -r requirements.txt```
3. Configure environment variables in ```.env``` file
```
GOOGLE_API_KEY=
GROQ_API_KEY=

FLASK_APP=app.py
FLASK_ENV=development
```
4. Run the application
```python app.py```
5. Access the application at
```http://localhost:5000```

# API Configuration
The application supports two AI service providers:
- Primary: Google Gemini API (gemini-2.5-flash model)
- Fallback: Groq API (Llama 4 Maverick model)

At least one API key must be configured in the ```.env``` file for the application to function. The system will automatically use the fallback service if the primary service encounters issues.

# Video Demonstration
https://drive.google.com/file/d/1WwTUiTSlHzuTHe5u-tYe8UgPi6oGR2B9/view

# Technical Details
## Resume Processing
The application uses pdfplumber library to extract text from PDF resumes. The extracted content is then structured and prepared for AI processing, ensuring accurate interpretation of professional information.

## AI Generation
A carefully crafted prompt template guides the AI in generating appropriate portfolio code. The system enforces consistent output format and includes necessary assets such as Bootstrap, Font Awesome, and Google Fonts.

## File Management
Uploaded files and generated portfolios are stored temporarily and automatically cleaned up to manage storage efficiently. Each generation job receives a unique identifier for tracking and management.

# Security Considerations
- File type validation for PDF uploads
- Size limits to prevent abuse
- Secure session management
- No persistent storage of sensitive information
- API key protection through environment variables

# Future Enhancements
Planned improvements for future versions include:
- Additional portfolio templates and styles
- Direct deployment options to hosting services
- Enhanced resume format support
- Portfolio customization interface
- Export options for different frameworks
- Integration with professional networking platforms
