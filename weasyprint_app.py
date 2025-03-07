from flask import Flask, request, render_template, redirect, url_for, session, jsonify
import openai
import os
import json
import time
from datetime import datetime
from weasyprint import HTML, CSS
from io import BytesIO

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = 'resumegenie_secret_key'

openai.api_key = "your_openai_api_key_here"  

def init_session():
    if 'resume_data' not in session:
        session['resume_data'] = {
            'name': '',
            'contact': '',
            'education': [],
            'technical_skills': [],
            'internships': [],
            'experience': [],
            'activities': []
        }
        session['current_section'] = 'intro'
        session.modified = True

@app.route('/')
def index():
    init_session()
    return render_template('index.html')

@app.route('/process_form', methods=['POST'])
def process_form():
    form_data = request.form
    
    name = form_data.get('name', '')
    email = form_data.get('email', '')
    phone = form_data.get('phone', '')
    linkedin = form_data.get('linkedin', '')
    location = form_data.get('location', '')
    
    education_data = []
    education_count = int(form_data.get('education_count', 0))
    for i in range(education_count):
        education = {
            'institution': form_data.get(f'institution_{i}', ''),
            'degree': form_data.get(f'degree_{i}', ''),
            'field': form_data.get(f'field_{i}', ''),
            'start_date': form_data.get(f'edu_start_date_{i}', ''),
            'end_date': form_data.get(f'edu_end_date_{i}', ''),
            'gpa': form_data.get(f'gpa_{i}', '')
        }
        education_data.append(education)
    
    skills = form_data.get('skills', '')
    skill_list = [skill.strip() for skill in skills.split(',')] if skills else []
    
    internship_data = []
    internship_count = int(form_data.get('internship_count', 0))
    for i in range(internship_count):
        internship = {
            'company': form_data.get(f'intern_company_{i}', ''),
            'position': form_data.get(f'intern_position_{i}', ''),
            'start_date': form_data.get(f'intern_start_date_{i}', ''),
            'end_date': form_data.get(f'intern_end_date_{i}', ''),
            'description': form_data.get(f'intern_description_{i}', '')
        }
        if internship['description']:
            internship['enhanced_description'] = generate_improved_description(
                internship['company'], 
                internship['position'], 
                internship['description'],
                "internship"
            )
        internship_data.append(internship)
    
    experience_data = []
    experience_count = int(form_data.get('experience_count', 0))
    for i in range(experience_count):
        experience = {
            'company': form_data.get(f'exp_company_{i}', ''),
            'position': form_data.get(f'exp_position_{i}', ''),
            'start_date': form_data.get(f'exp_start_date_{i}', ''),
            'end_date': form_data.get(f'exp_end_date_{i}', ''),
            'description': form_data.get(f'exp_description_{i}', '')
        }
        if experience['description']:
            experience['enhanced_description'] = generate_improved_description(
                experience['company'], 
                experience['position'], 
                experience['description'],
                "experience"
            )
        experience_data.append(experience)
    
    activities = form_data.get('activities', '')
    activity_list = [activity.strip() for activity in activities.split(',')] if activities else []
    
    resume_data = {
        'name': name,
        'contact': {
            'email': email,
            'phone': phone,
            'linkedin': linkedin,
            'location': location
        },
        'education': education_data,
        'technical_skills': skill_list,
        'internships': internship_data,
        'experience': experience_data,
        'activities': activity_list
    }
    
    session['resume_data'] = resume_data
    session.modified = True
    
    ats_score, ats_suggestions = analyze_ats_compatibility(resume_data)
    resume_data['ats_score'] = ats_score
    resume_data['ats_suggestions'] = ats_suggestions
    
    return render_template('resume.html', data=resume_data)

def generate_improved_description(company, position, original_description, section_type):
    try:
        if section_type == "internship":
            prompt = f"""
            I need to enhance my internship description for my resume. Please improve it to be ATS-friendly and impactful:
            
            Company: {company}
            Position: {position}
            Original Description: {original_description}
            
            Please create a bullet-point style description (3-4 points) highlighting achievements, skills used, 
            and quantifiable results where possible. Use action verbs and focus on achievements.
            """
        else:  # experience
            prompt = f"""
            I need to enhance my work experience description for my resume. Please improve it to be ATS-friendly and impactful:
            
            Company: {company}
            Position: {position}
            Original Description: {original_description}
            
            Please create a bullet-point style description (4-5 points) highlighting achievements, skills used, 
            and quantifiable results where possible. Use strong action verbs and focus on accomplishments.
            """
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert resume writer who creates impactful, ATS-friendly content."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.7
        )
        
        enhanced_description = response.choices[0].message.content.strip()
        return enhanced_description
    
    except Exception as e:
        return original_description

def analyze_ats_compatibility(resume_data):
    try:
        resume_text = f"""
        Name: {resume_data.get('name', '')}
        
        Education:
        {format_education(resume_data.get('education', []))}
        
        Technical Skills:
        {', '.join(resume_data.get('technical_skills', []))}
        
        Internships:
        {format_experiences(resume_data.get('internships', []))}
        
        Work Experience:
        {format_experiences(resume_data.get('experience', []))}
        
        Activities/Interests:
        {', '.join(resume_data.get('activities', []))}
        """
        
        prompt = f"""
        Analyze the following resume for ATS (Applicant Tracking System) compatibility:
        
        {resume_text}
        
        Please provide:
        1. An overall compatibility score from 0-100
        2. A list of 3-5 specific suggestions to improve ATS compatibility
        
        Format your response as:
        SCORE: [number]
        SUGGESTIONS:
        - [suggestion 1]
        - [suggestion 2]
        - [suggestion 3]
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert in resume writing and ATS compatibility."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=400,
            temperature=0.5
        )
        
        analysis = response.choices[0].message.content.strip()
        
        score = 0
        suggestions = []
        
        lines = analysis.split('\n')
        for line in lines:
            if line.startswith('SCORE:'):
                try:
                    score = int(line.replace('SCORE:', '').strip())
                except ValueError:
                    score = 0
            elif line.startswith('-'):
                suggestions.append(line.strip())
        
        return score, suggestions
    
    except Exception as e:
        return 70, ["Unable to perform complete analysis due to an error."]

def format_education(education_list):
    result = ""
    for edu in education_list:
        result += f"{edu.get('institution', '')}, {edu.get('degree', '')} in {edu.get('field', '')}\n"
        result += f"{edu.get('start_date', '')} to {edu.get('end_date', '')}\n"
        if edu.get('gpa'):
            result += f"GPA: {edu.get('gpa')}\n"
        result += "\n"
    return result

def format_experiences(exp_list):
    result = ""
    for exp in exp_list:
        result += f"{exp.get('position', '')} at {exp.get('company', '')}\n"
        result += f"{exp.get('start_date', '')} to {exp.get('end_date', '')}\n"
        description = exp.get('enhanced_description', '') or exp.get('description', '')
        result += f"{description}\n\n"
    return result

@app.route('/generate-pdf')
def generate_pdf():
    resume_data = session.get('resume_data', {})
    
    html_content = render_template('resume_template.html', data=resume_data)
    
    html = HTML(string=html_content)
    css = CSS(string='''
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 0;
        }
        .container {
            width: 100%;
            max-width: 800px;
            margin: 0 auto;
            padding: 1rem;
        }
        .header {
            text-align: center;
            border-bottom: 2px solid #1a2a6c;
            padding-bottom: 1rem;
            margin-bottom: 2rem;
        }
        .name {
            font-size: 2.2rem;
            color: #1a2a6c;
            margin-bottom: 0.2rem;
        }
        .contact-info {
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 1rem;
            font-size: 0.9rem;
        }
        section {
            margin-bottom: 2rem;
        }
        h2 {
            color: #b21f1f;
            border-bottom: 1px solid #fdbb2d;
            padding-bottom: 0.3rem;
        }
        .section-content {
            padding-left: 1rem;
        }
        .item {
            margin-bottom: 1.5rem;
        }
        .item-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 0.5rem;
        }
        .item-title {
            font-weight: bold;
            color: #1a2a6c;
        }
        .item-subtitle {
            font-style: italic;
        }
        .item-dates {
            color: #666;
        }
        ul {
            margin-top: 0.5rem;
            padding-left: 1.5rem;
        }
        .skills-list, .activities-list {
            display: flex;
            flex-wrap: wrap;
            gap: 0.8rem;
        }
        .skill-tag, .activity-tag {
            background-color: #f0f2f5;
            padding: 0.3rem 0.8rem;
            border-radius: 20px;
            font-size: 0.9rem;
        }
    ''')
    
    pdf = html.write_pdf(stylesheets=[css])
    
    from flask import send_file
    return send_file(
        BytesIO(pdf),
        download_name=f"ResumeGenie_{resume_data['name'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf",
        mimetype='application/pdf'
    )

if __name__ == '__main__':
    app.run(debug=True)
