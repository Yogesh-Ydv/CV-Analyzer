"""
knowledge_base.py
------------------
Static domain knowledge used by the CV Analyzer:
  - Role -> required skills taxonomy (used for scoring + gap analysis)
  - Skill -> learning resource recommendations
  - Section keyword lists for resume structure detection

In a production system this would live in a database (see README/Documentation
for the proposed schema) and be continuously updated from labour-market APIs
(LinkedIn Skills Graph, O*NET, Lightcast) rather than hardcoded. It is
hardcoded here only to keep the prototype self-contained and fully offline.
"""

ROLE_SKILLS = {
    "Data Scientist": {
        "core": ["python", "sql", "machine learning", "statistics", "pandas",
                 "numpy", "scikit-learn", "data visualization", "deep learning"],
        "good_to_have": ["tensorflow", "pytorch", "spark", "tableau", "power bi",
                          "nlp", "aws", "docker", "airflow"],
    },
    "Software Engineer": {
        "core": ["python", "java", "javascript", "git", "data structures",
                 "algorithms", "rest api", "sql", "object oriented programming"],
        "good_to_have": ["docker", "kubernetes", "aws", "ci/cd", "react",
                          "node.js", "microservices", "system design"],
    },
    "Frontend Developer": {
        "core": ["javascript", "html", "css", "react", "git", "responsive design"],
        "good_to_have": ["typescript", "redux", "next.js", "tailwind css",
                          "webpack", "testing", "figma"],
    },
    "Business Analyst": {
        "core": ["sql", "excel", "data analysis", "stakeholder management",
                 "requirements gathering", "power bi"],
        "good_to_have": ["tableau", "python", "agile", "jira", "sql server",
                          "process modelling"],
    },
    "Digital Marketing": {
        "core": ["seo", "google analytics", "content marketing", "social media marketing",
                 "campaign management", "email marketing"],
        "good_to_have": ["google ads", "sem", "hubspot", "a/b testing",
                          "marketing automation", "canva"],
    },
}

# Flat skill vocabulary used by the matcher (lowercase, multi-word ok)
ALL_SKILLS = sorted({s for role in ROLE_SKILLS.values()
                      for bucket in role.values() for s in bucket})

# Minimal resource map for the recommendation engine. In production this
# would call an external content/course API (Coursera, Udemy, LinkedIn
# Learning) — see Documentation, Section 6: API Integration Plan.
LEARNING_RESOURCES = {
    "python": "Python for Everybody (Coursera) / Official Python docs",
    "sql": "Mode SQL Tutorial / W3Schools SQL",
    "machine learning": "Andrew Ng's Machine Learning Specialization (Coursera)",
    "statistics": "Khan Academy – Statistics & Probability",
    "pandas": "Pandas official 10-minute guide + Kaggle micro-course",
    "numpy": "NumPy Quickstart (official docs)",
    "scikit-learn": "scikit-learn User Guide + Kaggle micro-courses",
    "data visualization": "Storytelling with Data (book) / Tableau Public tutorials",
    "deep learning": "DeepLearning.AI Deep Learning Specialization",
    "tensorflow": "TensorFlow official tutorials",
    "pytorch": "PyTorch 60-min Blitz tutorial",
    "spark": "Databricks Academy – Apache Spark",
    "tableau": "Tableau eLearning (free)",
    "power bi": "Microsoft Learn – Power BI Fundamentals",
    "nlp": "Hugging Face NLP Course",
    "aws": "AWS Cloud Practitioner Essentials",
    "docker": "Docker official Get Started guide",
    "airflow": "Astronomer Academy – Apache Airflow 101",
    "java": "Java Programming Masterclass / Oracle Java Tutorials",
    "javascript": "JavaScript.info / The Odin Project",
    "git": "Git official Pro Git book (free)",
    "data structures": "NeetCode / GeeksforGeeks DSA roadmap",
    "algorithms": "NeetCode / Grokking the Coding Interview",
    "rest api": "freeCodeCamp – REST API tutorial",
    "object oriented programming": "GeeksforGeeks OOP Concepts",
    "kubernetes": "Kubernetes official basics tutorial",
    "ci/cd": "GitHub Actions / GitLab CI documentation",
    "react": "React official docs (react.dev)",
    "node.js": "Node.js official guides",
    "microservices": "Building Microservices (book, Sam Newman)",
    "system design": "Grokking the System Design Interview / ByteByteGo",
    "html": "MDN Web Docs – HTML",
    "css": "MDN Web Docs – CSS / CSS Tricks",
    "responsive design": "freeCodeCamp Responsive Web Design",
    "typescript": "TypeScript official Handbook",
    "redux": "Redux official Essentials tutorial",
    "next.js": "Next.js official Learn course",
    "tailwind css": "Tailwind CSS official docs",
    "webpack": "Webpack official Getting Started guide",
    "testing": "Testing JavaScript (Kent C. Dodds)",
    "figma": "Figma official tutorials",
    "excel": "Microsoft Excel Skills for Business (Coursera)",
    "data analysis": "Google Data Analytics Certificate",
    "stakeholder management": "PMI – Stakeholder Engagement guide",
    "requirements gathering": "BABOK Guide (IIBA)",
    "agile": "Atlassian Agile Coach",
    "jira": "Atlassian Jira official training",
    "sql server": "Microsoft Learn – SQL Server Fundamentals",
    "process modelling": "BPMN Quick Guide",
    "seo": "Google SEO Starter Guide",
    "google analytics": "Google Analytics Academy",
    "content marketing": "HubSpot Content Marketing Certification",
    "social media marketing": "Meta Social Media Marketing Certificate (Coursera)",
    "campaign management": "Google Ads Certification",
    "email marketing": "HubSpot Email Marketing Certification",
    "google ads": "Google Ads Certification",
    "sem": "Google Skillshop – Search Ads",
    "hubspot": "HubSpot Academy",
    "a/b testing": "CXL – A/B Testing Fundamentals",
    "marketing automation": "HubSpot Marketing Automation course",
    "canva": "Canva Design School",
}

SECTION_KEYWORDS = {
    "contact": ["email", "phone", "linkedin", "github"],
    "summary": ["summary", "objective", "profile"],
    "experience": ["experience", "employment", "work history"],
    "education": ["education", "academic", "qualification"],
    "skills": ["skills", "technical skills", "competencies"],
    "projects": ["projects", "portfolio"],
    "certifications": ["certification", "certificate", "license"],
}
