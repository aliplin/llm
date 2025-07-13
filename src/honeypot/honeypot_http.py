import os
import json
import uuid
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import openai
from pathlib import Path

HTTP_PORT = 8848
# 预定义模板
HTML_TEMPLATES = {
    "home": """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{company_name} - {model_name}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            line-height: 1.6;
            min-height: 100vh;
        }}

        header {{
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            box-shadow: 0 2px 20px rgba(0, 0, 0, 0.1);
            position: sticky;
            top: 0;
            z-index: 1000;
        }}

        .header-content {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .logo {{
            font-size: 1.8rem;
            font-weight: 700;
            color: #667eea;
            text-decoration: none;
            transition: color 0.3s ease;
        }}

        .logo:hover {{
            color: #764ba2;
        }}

        nav {{
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(10px);
            border-bottom: 1px solid rgba(255, 255, 255, 0.2);
        }}

        .nav-content {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 2rem;
            display: flex;
            justify-content: center;
        }}

        nav a {{
            color: #555;
            text-decoration: none;
            padding: 1rem 1.5rem;
            margin: 0 0.25rem;
            border-radius: 8px;
            transition: all 0.3s ease;
            font-weight: 500;
        }}

        nav a:hover {{
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }}

        .main-content {{
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            padding: 3rem;
            border-radius: 20px;
            margin: 2rem 0;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }}

        h1, h2 {{
            color: #667eea;
            margin-bottom: 1rem;
            font-weight: 600;
        }}

        h1 {{
            font-size: 3rem;
            background: linear-gradient(135deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            text-align: center;
        }}

        h2 {{
            font-size: 2rem;
        }}

        footer {{
            background: rgba(0, 0, 0, 0.8);
            color: white;
            text-align: center;
            padding: 1.5rem 0;
            margin-top: 3rem;
        }}

        .hero-section {{
            text-align: center;
            margin-bottom: 3rem;
        }}

        .hero-section p {{
            font-size: 1.3rem;
            color: #666;
            margin-bottom: 2rem;
            line-height: 1.8;
        }}

        .cta-buttons {{
            display: flex;
            justify-content: center;
            gap: 1rem;
            flex-wrap: wrap;
        }}

        .cta-button {{
            display: inline-block;
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 1rem 2rem;
            border-radius: 50px;
            text-decoration: none;
            font-weight: 600;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }}

        .cta-button:hover {{
            transform: translateY(-3px);
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.6);
        }}

        .cta-button.secondary {{
            background: linear-gradient(135deg, #f093fb, #f5576c);
        }}

        .welcome-message {{
            background: linear-gradient(135deg, #f8f9ff 0%, #e8ecff 100%);
            padding: 2rem;
            border-radius: 15px;
            margin: 2rem 0;
            border: 1px solid rgba(102, 126, 234, 0.1);
            text-align: center;
        }}

        @media (max-width: 768px) {{
            .header-content {{
                flex-direction: column;
                text-align: center;
            }}

            .nav-content {{
                flex-wrap: wrap;
            }}

            nav a {{
                margin: 0.25rem;
                padding: 0.75rem 1rem;
            }}

            .main-content {{
                padding: 2rem;
                margin: 1rem;
            }}

            h1 {{
                font-size: 2.5rem;
            }}

            h2 {{
                font-size: 1.5rem;
            }}

            .cta-buttons {{
                flex-direction: column;
                align-items: center;
            }}
        }}
    </style>
</head>
<body>
    <header>
        <div class="header-content">
            <a href="/" class="logo">{company_name}</a>
            <div style="color: #667eea; font-weight: 500;">{model_name}</div>
        </div>
    </header>
    <nav>
        <div class="nav-content">
            <a href="/">Home</a>
            <a href="/documentation">Documentation</a>
            <a href="/search">Search</a>
            <a href="/admin">Admin</a>
            <a href="/contact">Contact</a>
        </div>
    </nav>
    <div class="container">
        <div class="main-content">
            <div class="hero-section">
                <h1>Welcome to {company_name}</h1>
                <div class="welcome-message">
                    <p>{welcome_text}</p>
                </div>
                <div class="cta-buttons">
                    <a href="/documentation" class="cta-button">Learn More</a>
                    <a href="/documentation" class="cta-button secondary">Get Started</a>
                </div>
            </div>
        </div>
    </div>
    <footer>
        <p>&copy; 2025 {company_name}. All rights reserved. | Advanced Printing Solutions</p>
    </footer>
</body>
</html>""",

    "search": """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{company_name} - Search Products</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            line-height: 1.6;
            min-height: 100vh;
        }}

        header {{
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            box-shadow: 0 2px 20px rgba(0, 0, 0, 0.1);
            position: sticky;
            top: 0;
            z-index: 1000;
        }}

        .header-content {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .logo {{
            font-size: 1.8rem;
            font-weight: 700;
            color: #667eea;
            text-decoration: none;
            transition: color 0.3s ease;
        }}

        .logo:hover {{
            color: #764ba2;
        }}

        nav {{
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(10px);
            border-bottom: 1px solid rgba(255, 255, 255, 0.2);
        }}

        .nav-content {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 2rem;
            display: flex;
            justify-content: center;
        }}

        nav a {{
            color: #555;
            text-decoration: none;
            padding: 1rem 1.5rem;
            margin: 0 0.25rem;
            border-radius: 8px;
            transition: all 0.3s ease;
            font-weight: 500;
        }}

        nav a:hover {{
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }}

        .search-content {{
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            padding: 3rem;
            border-radius: 20px;
            margin: 2rem 0;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }}

        h1, h2, h3 {{
            color: #667eea;
            margin-bottom: 1rem;
            font-weight: 600;
        }}

        h1 {{
            font-size: 2.5rem;
            text-align: center;
            margin-bottom: 2rem;
        }}

        h2 {{
            font-size: 2rem;
            text-align: center;
            margin-bottom: 2rem;
        }}

        .search-form {{
            text-align: center;
            margin: 2rem 0;
        }}

        .search-form input[type="text"] {{
            width: 70%;
            padding: 1rem 1.5rem;
            font-size: 1.1rem;
            border: 2px solid #e1e5e9;
            border-radius: 50px;
            outline: none;
            transition: all 0.3s ease;
            font-family: inherit;
        }}

        .search-form input[type="text"]:focus {{
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }}

        .search-form input[type="submit"] {{
            padding: 1rem 2rem;
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border: none;
            border-radius: 50px;
            cursor: pointer;
            font-size: 1.1rem;
            font-weight: 600;
            margin-left: 1rem;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }}

        .search-form input[type="submit"]:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.6);
        }}

        .search-results {{
            margin-top: 2rem;
        }}

        .results-count {{
            text-align: center;
            color: #666;
            font-size: 1.1rem;
            margin-bottom: 2rem;
        }}

        .products-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 2rem;
            margin: 2rem 0;
        }}

        .product-card {{
            background: linear-gradient(135deg, #f8f9ff 0%, #e8ecff 100%);
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 5px 20px rgba(0, 0, 0, 0.1);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            border: 1px solid rgba(102, 126, 234, 0.1);
            position: relative;
        }}

        .product-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 15px 40px rgba(102, 126, 234, 0.2);
        }}

        .product-card.featured {{
            border: 2px solid #667eea;
        }}

        .product-image {{
            position: relative;
            height: 200px;
            overflow: hidden;
            background: linear-gradient(135deg, #667eea, #764ba2);
        }}

        .product-image img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: transform 0.3s ease;
        }}

        .image-placeholder {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            width: 100%;
            height: 100%;
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            font-size: 1.2rem;
            font-weight: 600;
        }}

        .image-placeholder i {{
            font-size: 3rem;
            margin-bottom: 1rem;
        }}

        .product-card:hover .product-image img {{
            transform: scale(1.05);
        }}

        .featured-badge {{
            position: absolute;
            top: 10px;
            right: 10px;
            background: linear-gradient(135deg, #f093fb, #f5576c);
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
        }}

        .product-info {{
            padding: 1.5rem;
        }}

        .product-info h3 {{
            color: #667eea;
            font-size: 1.3rem;
            margin-bottom: 0.5rem;
        }}

        .model {{
            color: #666;
            font-size: 0.9rem;
            margin-bottom: 0.5rem;
        }}

        .type {{
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 0.3rem 0.8rem;
            border-radius: 15px;
            font-size: 0.8rem;
            font-weight: 600;
            display: inline-block;
            margin-bottom: 1rem;
        }}

        .description {{
            color: #666;
            margin-bottom: 1rem;
            line-height: 1.5;
        }}

        .features {{
            margin-bottom: 1rem;
        }}

        .feature-tag {{
            background: rgba(102, 126, 234, 0.1);
            color: #667eea;
            padding: 0.3rem 0.6rem;
            border-radius: 10px;
            font-size: 0.8rem;
            margin-right: 0.5rem;
            margin-bottom: 0.5rem;
            display: inline-block;
        }}

        .specs {{
            background: rgba(255, 255, 255, 0.7);
            padding: 1rem;
            border-radius: 10px;
            margin-bottom: 1rem;
        }}

        .spec-item {{
            margin-bottom: 0.5rem;
            font-size: 0.9rem;
        }}

        .spec-item:last-child {{
            margin-bottom: 0;
        }}

        .price {{
            font-size: 1.5rem;
            font-weight: 700;
            color: #667eea;
            margin-bottom: 1rem;
        }}

        .view-details-btn {{
            width: 100%;
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border: none;
            padding: 0.8rem;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s ease;
        }}

        .view-details-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }}

        .no-results {{
            text-align: center;
            padding: 3rem;
            background: linear-gradient(135deg, #fff5f5 0%, #fed7d7 100%);
            border-radius: 15px;
            border: 1px solid rgba(254, 178, 178, 0.3);
        }}

        .no-results h3 {{
            color: #e53e3e;
            margin-bottom: 1rem;
        }}

        .no-results p {{
            color: #666;
        }}

        .featured-section {{
            margin: 3rem 0;
        }}

        .featured-section h2 {{
            text-align: center;
            margin-bottom: 2rem;
        }}

        footer {{
            background: rgba(0, 0, 0, 0.8);
            color: white;
            text-align: center;
            padding: 1.5rem 0;
            margin-top: 3rem;
        }}

        @media (max-width: 768px) {{
            .search-form input[type="text"] {{
                width: 100%;
                margin-bottom: 1rem;
            }}

            .search-form input[type="submit"] {{
                width: 100%;
                margin-left: 0;
            }}

            .search-content {{
                padding: 2rem;
                margin: 1rem;
            }}

            .products-grid {{
                grid-template-columns: 1fr;
                gap: 1rem;
            }}

            h1 {{
                font-size: 2rem;
            }}
        }}
    </style>
</head>
<body>
    <header>
        <div class="header-content">
            <a href="/" class="logo">{company_name}</a>
            <div style="color: #667eea; font-weight: 500;">{model_name}</div>
        </div>
    </header>
    <nav>
        <div class="nav-content">
            <a href="/">Home</a>
            <a href="/documentation">Documentation</a>
            <a href="/search">Search</a>
            <a href="/admin">Admin</a>
            <a href="/contact">Contact</a>
        </div>
    </nav>
    <div class="container">
        <div class="search-content">
            <h1><i class="fas fa-search"></i> Search Products</h1>
            <p style="text-align: center; color: #666; margin-bottom: 2rem;">
                Find the perfect printer for your needs. Search by model, type, or features.
            </p>

            <form class="search-form" method="GET" action="/search">
                <input type="text" name="q" placeholder="Search for printers, models, or features..." value="{search_query}">
                <input type="submit" value="Search">
            </form>

            {search_results}

            {featured_products}
        </div>
    </div>
    <footer>
        <p>&copy; 2025 {company_name}. All rights reserved. | Advanced Printing Solutions</p>
    </footer>
</body>
</html>""",

    "admin": """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{company_name} - Admin Panel</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            line-height: 1.6;
            min-height: 100vh;
        }}

        header {{
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            box-shadow: 0 2px 20px rgba(0, 0, 0, 0.1);
            position: sticky;
            top: 0;
            z-index: 1000;
        }}

        .header-content {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .logo {{
            font-size: 1.8rem;
            font-weight: 700;
            color: #667eea;
            text-decoration: none;
            transition: color 0.3s ease;
        }}

        .logo:hover {{
            color: #764ba2;
        }}

        nav {{
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(10px);
            border-bottom: 1px solid rgba(255, 255, 255, 0.2);
        }}

        .nav-content {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 2rem;
            display: flex;
            justify-content: center;
        }}

        nav a {{
            color: #555;
            text-decoration: none;
            padding: 1rem 1.5rem;
            margin: 0 0.25rem;
            border-radius: 8px;
            transition: all 0.3s ease;
            font-weight: 500;
        }}

        nav a:hover {{
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }}

        .admin-content {{
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            padding: 3rem;
            border-radius: 20px;
            margin: 2rem 0;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }}

        h1, h2, h3 {{
            color: #667eea;
            margin-bottom: 1rem;
            font-weight: 600;
        }}

        h2 {{
            font-size: 2rem;
            text-align: center;
            margin-bottom: 2rem;
        }}

        .login-form {{
            max-width: 400px;
            margin: 0 auto;
            background: linear-gradient(135deg, #f8f9ff 0%, #e8ecff 100%);
            padding: 2rem;
            border-radius: 15px;
            border: 1px solid rgba(102, 126, 234, 0.1);
        }}

        .form-group {{
            margin: 1.5rem 0;
        }}

        .form-group label {{
            display: block;
            margin-bottom: 0.5rem;
            font-weight: 500;
            color: #555;
        }}

        .form-group input {{
            width: 100%;
            padding: 1rem;
            border: 2px solid #e1e5e9;
            border-radius: 8px;
            font-size: 1rem;
            font-family: inherit;
            transition: all 0.3s ease;
            outline: none;
        }}

        .form-group input:focus {{
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }}

        .form-group button {{
            width: 100%;
            padding: 1rem;
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1rem;
            font-weight: 600;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }}

        .form-group button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.6);
        }}

        .admin-panel {{
            display: none;
            background: linear-gradient(135deg, #f8f9ff 0%, #e8ecff 100%);
            padding: 2rem;
            border-radius: 15px;
            margin-top: 2rem;
            border: 1px solid rgba(102, 126, 234, 0.1);
        }}

        .admin-panel.show {{
            display: block;
        }}

        .system-info {{
            background: rgba(255, 255, 255, 0.7);
            padding: 1.5rem;
            border-radius: 10px;
            margin: 1rem 0;
            border-left: 4px solid #667eea;
        }}

        .system-info p {{
            margin: 0.5rem 0;
        }}

        .system-info strong {{
            color: #667eea;
        }}

        .command-section {{
            margin-top: 2rem;
        }}

        .command-output {{
            background: #2d3748;
            color: #e2e8f0;
            padding: 1.5rem;
            border-radius: 10px;
            margin: 1rem 0;
            font-family: 'Courier New', monospace;
            font-size: 0.9rem;
            overflow-x: auto;
        }}

        .message {{
            padding: 1rem;
            border-radius: 8px;
            margin: 1rem 0;
            font-weight: 500;
        }}

        .message.success {{
            background: linear-gradient(135deg, #c6f6d5 0%, #9ae6b4 100%);
            border: 2px solid #68d391;
            color: #22543d;
        }}

        .message.error {{
            background: linear-gradient(135deg, #fed7d7 0%, #feb2b2 100%);
            border: 2px solid #fc8181;
            color: #742a2a;
        }}

        .message.warning {{
            background: linear-gradient(135deg, #fef5e7 0%, #fbd38d 100%);
            border: 2px solid #f6ad55;
            color: #744210;
        }}

        footer {{
            background: rgba(0, 0, 0, 0.8);
            color: white;
            text-align: center;
            padding: 1.5rem 0;
            margin-top: 3rem;
        }}

        @media (max-width: 768px) {{
            .admin-content {{
                padding: 2rem;
                margin: 1rem;
            }}

            .login-form {{
                margin: 0 1rem;
            }}
        }}
    </style>
</head>
<body>
    <header>
        <div class="header-content">
            <a href="/" class="logo">{company_name}</a>
            <div style="color: #667eea; font-weight: 500;">{model_name}</div>
        </div>
    </header>
    <nav>
        <div class="nav-content">
            <a href="/">Home</a>
            <a href="/documentation">Documentation</a>
            <a href="/search">Search</a>
            <a href="/admin">Admin</a>
            <a href="/contact">Contact</a>
        </div>
    </nav>
    <div class="container">
        <div class="admin-content">
            <h2>🔐 Administrator Panel</h2>
            <div class="login-form" id="loginForm">
                <form method="POST" action="/admin">
                    <div class="form-group">
                        <label for="username">Username:</label>
                        <input type="text" id="username" name="username" required>
                    </div>
                    <div class="form-group">
                        <label for="password">Password:</label>
                        <input type="password" id="password" name="password" required>
                    </div>
                    <div class="form-group">
                        <button type="submit">Login</button>
                    </div>
                </form>
                {login_message}
            </div>
            <div class="admin-panel" id="adminPanel">
                <h3>📊 System Information</h3>
                <div class="system-info">
                    <p><strong>Server:</strong> {server_info}</p>
                    <p><strong>Database:</strong> {db_info}</p>
                    <p><strong>Users:</strong> {user_count}</p>
                </div>
                <div class="command-section">
                    <h3>⚡ System Commands</h3>
                    <form method="POST" action="/admin/command">
                        <div class="form-group">
                            <label for="command">Command:</label>
                            <input type="text" id="command" name="command" placeholder="Enter system command...">
                        </div>
                        <div class="form-group">
                            <button type="submit">Execute</button>
                        </div>
                    </form>
                    {command_output}
                </div>
            </div>
        </div>
    </div>
    <footer>
        <p>&copy; 2025 {company_name}. All rights reserved. | Advanced Printing Solutions</p>
    </footer>
    <script>
        {admin_script}
    </script>
</body>
</html>""",

    "documentation": """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{company_name} - Documentation</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            line-height: 1.6;
            min-height: 100vh;
        }}

        header {{
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            box-shadow: 0 2px 20px rgba(0, 0, 0, 0.1);
            position: sticky;
            top: 0;
            z-index: 1000;
        }}

        .header-content {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .logo {{
            font-size: 1.8rem;
            font-weight: 700;
            color: #667eea;
            text-decoration: none;
            transition: color 0.3s ease;
        }}

        .logo:hover {{
            color: #764ba2;
        }}

        nav {{
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(10px);
            border-bottom: 1px solid rgba(255, 255, 255, 0.2);
        }}

        .nav-content {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 2rem;
            display: flex;
            justify-content: center;
        }}

        nav a {{
            color: #555;
            text-decoration: none;
            padding: 1rem 1.5rem;
            margin: 0 0.25rem;
            border-radius: 8px;
            transition: all 0.3s ease;
            font-weight: 500;
        }}

        nav a:hover {{
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }}

        .doc-content {{
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            padding: 3rem;
            border-radius: 20px;
            margin: 2rem 0;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }}

        h1, h2, h3 {{
            color: #667eea;
            margin-bottom: 1rem;
            font-weight: 600;
        }}

        h2 {{
            font-size: 2rem;
            text-align: center;
            margin-bottom: 2rem;
        }}

        .section {{
            background: linear-gradient(135deg, #f8f9ff 0%, #e8ecff 100%);
            margin: 2rem 0;
            padding: 2rem;
            border-radius: 15px;
            border: 1px solid rgba(102, 126, 234, 0.1);
            transition: transform 0.3s ease;
        }}

        .section:hover {{
            transform: translateY(-2px);
        }}

        .section h3 {{
            color: #667eea;
            font-size: 1.4rem;
            margin-bottom: 1rem;
            border-bottom: 2px solid #667eea;
            padding-bottom: 0.5rem;
        }}

        code {{
            background: #2d3748;
            color: #e2e8f0;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            font-size: 0.9rem;
        }}

        pre {{
            background: #2d3748;
            color: #e2e8f0;
            padding: 1.5rem;
            border-radius: 8px;
            overflow-x: auto;
            font-family: 'Courier New', monospace;
            font-size: 0.9rem;
            margin: 1rem 0;
        }}

        ul, ol {{
            padding-left: 2rem;
            margin: 1rem 0;
        }}

        li {{
            margin: 0.5rem 0;
        }}

        p {{
            margin: 1rem 0;
            line-height: 1.8;
        }}

        footer {{
            background: rgba(0, 0, 0, 0.8);
            color: white;
            text-align: center;
            padding: 1.5rem 0;
            margin-top: 3rem;
        }}

        @media (max-width: 768px) {{
            .doc-content {{
                padding: 2rem;
                margin: 1rem;
            }}

            .section {{
                padding: 1.5rem;
            }}
        }}
    </style>
</head>
<body>
    <header>
        <div class="header-content">
            <a href="/" class="logo">{company_name}</a>
            <div style="color: #667eea; font-weight: 500;">{model_name}</div>
        </div>
    </header>
    <nav>
        <div class="nav-content">
            <a href="/">Home</a>
            <a href="/documentation">Documentation</a>
            <a href="/search">Search</a>
            <a href="/admin">Admin</a>
            <a href="/contact">Contact</a>
        </div>
    </nav>
    <div class="container">
        <div class="doc-content">
            <h2>📚 Documentation</h2>
            {doc_content}
        </div>
    </div>
    <footer>
        <p>&copy; 2025 {company_name}. All rights reserved. | Advanced Printing Solutions</p>
    </footer>
</body>
</html>""",

    "error_400": """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>400 Bad Request</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            text-align: center;
            padding: 50px 20px;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .error-container {{
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            padding: 3rem;
            border-radius: 20px;
            max-width: 500px;
            margin: auto;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }}

        h1 {{
            color: #e53e3e;
            font-size: 4rem;
            margin: 0;
            font-weight: 700;
            background: linear-gradient(135deg, #e53e3e, #c53030);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}

        h2 {{
            color: #333;
            margin: 1rem 0;
            font-size: 1.5rem;
            font-weight: 600;
        }}

        p {{
            color: #666;
            line-height: 1.6;
            margin: 1rem 0;
        }}

        .back-button {{
            display: inline-block;
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 1rem 2rem;
            border-radius: 50px;
            text-decoration: none;
            font-weight: 600;
            margin-top: 2rem;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }}

        .back-button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.6);
        }}
    </style>
</head>
<body>
    <div class="error-container">
        <h1>400</h1>
        <h2>Bad Request</h2>
        <p>The server cannot process the request due to a client error.</p>
        <p>Please check your request and try again.</p>
        <a href="/" class="back-button">Go Home</a>
    </div>
</body>
</html>""",

    "css": """/* Main styles for {company_name} {model_name} */
* {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}

body {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: #333;
    line-height: 1.6;
    min-height: 100vh;
}}

header {{
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(10px);
    box-shadow: 0 2px 20px rgba(0, 0, 0, 0.1);
    position: sticky;
    top: 0;
    z-index: 1000;
}}

.header-content {{
    max-width: 1200px;
    margin: 0 auto;
    padding: 1rem 2rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
}}

.logo {{
    font-size: 1.8rem;
    font-weight: 700;
    color: #667eea;
    text-decoration: none;
    transition: color 0.3s ease;
}}

.logo:hover {{
    color: #764ba2;
}}

nav {{
    background: rgba(255, 255, 255, 0.9);
    backdrop-filter: blur(10px);
    border-bottom: 1px solid rgba(255, 255, 255, 0.2);
}}

.nav-content {{
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 2rem;
    display: flex;
    justify-content: center;
}}

nav a {{
    color: #555;
    text-decoration: none;
    padding: 1rem 1.5rem;
    margin: 0 0.25rem;
    border-radius: 8px;
    transition: all 0.3s ease;
    font-weight: 500;
}}

nav a:hover {{
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white;
    transform: translateY(-2px);
    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
}}

.container {{
    max-width: 1200px;
    margin: 0 auto;
    padding: 2rem;
}}

.main-content {{
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(10px);
    padding: 3rem;
    border-radius: 20px;
    margin: 2rem 0;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.2);
}}

h1, h2, h3 {{
    color: #667eea;
    margin-bottom: 1rem;
    font-weight: 600;
}}

footer {{
    background: rgba(0, 0, 0, 0.8);
    color: white;
    text-align: center;
    padding: 1.5rem 0;
    margin-top: 3rem;
}}""",

    "contact": """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Contact Us - {company_name}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            line-height: 1.6;
            min-height: 100vh;
        }}

        header {{
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            box-shadow: 0 2px 20px rgba(0, 0, 0, 0.1);
            position: sticky;
            top: 0;
            z-index: 1000;
        }}

        .header-content {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .logo {{
            font-size: 1.8rem;
            font-weight: 700;
            color: #667eea;
            text-decoration: none;
            transition: color 0.3s ease;
        }}

        .logo:hover {{
            color: #764ba2;
        }}

        nav {{
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(10px);
            border-bottom: 1px solid rgba(255, 255, 255, 0.2);
        }}

        .nav-content {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 2rem;
            display: flex;
            justify-content: center;
        }}

        nav a {{
            color: #555;
            text-decoration: none;
            padding: 1rem 1.5rem;
            margin: 0 0.25rem;
            border-radius: 8px;
            transition: all 0.3s ease;
            font-weight: 500;
        }}

        nav a:hover {{
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }}

        .contact-content {{
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            padding: 3rem;
            border-radius: 20px;
            margin: 2rem 0;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }}

        h1, h2, h3 {{
            color: #667eea;
            margin-bottom: 1rem;
            font-weight: 600;
        }}

        h1 {{
            font-size: 2.5rem;
            text-align: center;
            margin-bottom: 2rem;
        }}

        h2 {{
            font-size: 1.8rem;
            margin-bottom: 1.5rem;
        }}

        .contact-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 2rem;
            margin: 2rem 0;
        }}

        .contact-card {{
            background: linear-gradient(135deg, #f8f9ff 0%, #e8ecff 100%);
            padding: 2rem;
            border-radius: 15px;
            border: 1px solid rgba(102, 126, 234, 0.1);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            text-align: center;
        }}

        .contact-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.2);
        }}

        .contact-icon {{
            font-size: 3rem;
            color: #667eea;
            margin-bottom: 1rem;
        }}

        .contact-info {{
            margin: 1rem 0;
        }}

        .contact-info h3 {{
            color: #667eea;
            margin-bottom: 0.5rem;
        }}

        .contact-info p {{
            color: #666;
            margin-bottom: 0.5rem;
        }}

        .email-link {{
            color: #667eea;
            text-decoration: none;
            font-weight: 600;
            transition: color 0.3s ease;
        }}

        .email-link:hover {{
            color: #764ba2;
            text-decoration: underline;
        }}

        .contact-form {{
            background: linear-gradient(135deg, #f8f9ff 0%, #e8ecff 100%);
            padding: 2rem;
            border-radius: 15px;
            border: 1px solid rgba(102, 126, 234, 0.1);
            margin-top: 2rem;
        }}

        .form-group {{
            margin: 1.5rem 0;
        }}

        .form-group label {{
            display: block;
            margin-bottom: 0.5rem;
            font-weight: 500;
            color: #555;
        }}

        .form-group input,
        .form-group textarea {{
            width: 100%;
            padding: 1rem;
            border: 2px solid #e1e5e9;
            border-radius: 8px;
            font-size: 1rem;
            font-family: inherit;
            transition: all 0.3s ease;
            outline: none;
        }}

        .form-group input:focus,
        .form-group textarea:focus {{
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }}

        .form-group textarea {{
            resize: vertical;
            min-height: 120px;
        }}

        .submit-btn {{
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border: none;
            padding: 1rem 2rem;
            border-radius: 50px;
            cursor: pointer;
            font-size: 1rem;
            font-weight: 600;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }}

        .submit-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.6);
        }}

        .office-hours {{
            background: linear-gradient(135deg, #fff5f5 0%, #fed7d7 100%);
            padding: 1.5rem;
            border-radius: 12px;
            margin: 2rem 0;
            border: 1px solid rgba(254, 178, 178, 0.3);
        }}

        .office-hours h3 {{
            color: #e53e3e;
            margin-bottom: 1rem;
        }}

        .office-hours ul {{
            list-style: none;
            padding: 0;
        }}

        .office-hours li {{
            padding: 0.5rem 0;
            border-bottom: 1px solid rgba(254, 178, 178, 0.2);
        }}

        .office-hours li:last-child {{
            border-bottom: none;
        }}

        footer {{
            background: rgba(0, 0, 0, 0.8);
            color: white;
            text-align: center;
            padding: 1.5rem 0;
            margin-top: 3rem;
        }}

        @media (max-width: 768px) {{
            .contact-content {{
                padding: 2rem;
                margin: 1rem;
            }}

            .contact-grid {{
                grid-template-columns: 1fr;
                gap: 1rem;
            }}

            h1 {{
                font-size: 2rem;
            }}

            .contact-card {{
                padding: 1.5rem;
            }}
        }}
    </style>
</head>
<body>
    <header>
        <div class="header-content">
            <a href="/" class="logo">{company_name}</a>
            <div style="color: #667eea; font-weight: 500;">{model_name}</div>
        </div>
    </header>
    <nav>
        <div class="nav-content">
            <a href="/">Home</a>
            <a href="/documentation">Documentation</a>
            <a href="/search">Search</a>
            <a href="/admin">Admin</a>
            <a href="/contact">Contact</a>
        </div>
    </nav>
    <div class="container">
        <div class="contact-content">
            <h1>📧 Contact Us</h1>
            <p style="text-align: center; font-size: 1.2rem; color: #666; margin-bottom: 2rem;">
                Get in touch with our team for support, inquiries, or collaboration opportunities.
            </p>

            <div class="contact-grid">
                <div class="contact-card">
                    <div class="contact-icon">
                        <i class="fas fa-envelope"></i>
                    </div>
                    <div class="contact-info">
                        <h3>Email Support</h3>
                        <p>For technical support and general inquiries:</p>
                        <a href="mailto:123456789@qq.com" class="email-link">123456789@qq.com</a>
                    </div>
                </div>

                <div class="contact-card">
                    <div class="contact-icon">
                        <i class="fas fa-phone"></i>
                    </div>
                    <div class="contact-info">
                        <h3>Phone Support</h3>
                        <p>Call us during business hours:</p>
                        <p><strong>+86 400-123-4567</strong></p>
                    </div>
                </div>

                <div class="contact-card">
                    <div class="contact-icon">
                        <i class="fas fa-map-marker-alt"></i>
                    </div>
                    <div class="contact-info">
                        <h3>Office Location</h3>
                        <p>Visit our headquarters:</p>
                        <p><strong>123 Tech Street<br>Beijing, China 100000</strong></p>
                    </div>
                </div>

                <div class="contact-card">
                    <div class="contact-icon">
                        <i class="fas fa-clock"></i>
                    </div>
                    <div class="contact-info">
                        <h3>Response Time</h3>
                        <p>We typically respond within:</p>
                        <p><strong>2-4 hours</strong> during business days</p>
                    </div>
                </div>
            </div>

            <div class="office-hours">
                <h3><i class="fas fa-calendar-alt"></i> Business Hours</h3>
                <ul>
                    <li><strong>Monday - Friday:</strong> 9:00 AM - 6:00 PM (CST)</li>
                    <li><strong>Saturday:</strong> 10:00 AM - 4:00 PM (CST)</li>
                    <li><strong>Sunday:</strong> Closed</li>
                    <li><strong>Holidays:</strong> Please check our announcements</li>
                </ul>
            </div>

            <div class="contact-form">
                <h2><i class="fas fa-paper-plane"></i> Send us a Message</h2>
                <form>
                    <div class="form-group">
                        <label for="name">Full Name *</label>
                        <input type="text" id="name" name="name" required>
                    </div>
                    <div class="form-group">
                        <label for="email">Email Address *</label>
                        <input type="email" id="email" name="email" required>
                    </div>
                    <div class="form-group">
                        <label for="subject">Subject *</label>
                        <input type="text" id="subject" name="subject" required>
                    </div>
                    <div class="form-group">
                        <label for="message">Message *</label>
                        <textarea id="message" name="message" placeholder="Please describe your inquiry or request..." required></textarea>
                    </div>
                    <button type="submit" class="submit-btn">
                        <i class="fas fa-paper-plane"></i> Send Message
                    </button>
                </form>
            </div>
        </div>
    </div>
    <footer>
        <p>&copy; 2025 {company_name}. All rights reserved. | Advanced Printing Solutions</p>
    </footer>
</body>
</html>"""
}


class HTTPSession:
    """HTTP会话管理类，维护AI对话历史和内容缓存"""

    def __init__(self, openai_client, identity, model_name, temperature, max_tokens):
        self.openai_client = openai_client
        self.identity = identity
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens

        # 初始化AI对话历史
        self.conversation_history = [
            {"role": "system", "content": self.identity['prompt']}
        ]

        # 内容缓存 - 确保同一页面内容一致
        self.content_cache = {}

        # 初始化网站内容（只生成一次）
        self._initialize_website_content()

    def _clean_features_list(self, features_list):
        """清理features_list，移除Python字典符号"""
        if isinstance(features_list, str):
            # 如果是字符串，尝试清理
            import re
            # 移除Python列表符号
            cleaned = re.sub(r'^\[|\]$', '', features_list)
            # 移除引号和逗号
            cleaned = re.sub(r"'", '', cleaned)
            cleaned = re.sub(r',', '', cleaned)
            # 分割并重新构建HTML
            features = [f.strip() for f in cleaned.split('\n') if f.strip()]
            return ''.join([f'<li>{feature}</li>' for feature in features])
        return features_list

    def _initialize_website_content(self):
        """初始化网站内容，确保整个网站的一致性"""
        try:
            # 生成网站基础信息
            prompt = f"""你是一个{self.identity['prompt']}的打印机公司。请生成以下信息（只返回JSON格式）：
1. company_name: 公司名称（简短有创意）
2. model_name: 打印机型号（包含数字）
3. welcome_text: 欢迎文字（50字以内）
4. features_list: 5个主要特性（HTML格式的li标签）
5. description_text: 产品描述（100字以内）

只返回JSON，不要其他内容。"""

            messages = [
                {"role": "system", "content": "你是一个打印机公司的AI助手，只返回JSON格式的数据。"},
                {"role": "user", "content": prompt}
            ]

            response = self.openai_client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=self.temperature,
                max_tokens=500
            )

            content = response.choices[0].message.content

            # 解析JSON响应
            try:
                data = json.loads(content)
                raw_features = data.get("features_list",
                                        "<li>High-speed printing</li><li>Wireless connectivity</li><li>Duplex printing</li><li>High resolution</li><li>Eco-friendly</li>")
                cleaned_features = self._clean_features_list(raw_features)

                self.website_info = {
                    "company_name": data.get("company_name", "Tech Soulutions"),
                    "model_name": data.get("model_name", "TechPrint 2000"),
                    "welcome_text": data.get("welcome_text", "Welcome to our printer solutions."),
                    "features_list": cleaned_features,
                    "description_text": data.get("description_text",
                                                 "Our flagship printer offers advanced features for modern businesses.")
                }
            except:
                # 如果JSON解析失败，使用默认值
                self.website_info = {
                    "company_name": "Tech Soulutions",
                    "model_name": "TechPrint 2000",
                    "welcome_text": "Welcome to Tech Soulutions, leading manufacturer of high-quality printing solutions.",
                    "features_list": "<li>High-speed printing up to 30 ppm</li><li>1200 dpi resolution</li><li>Wireless and Ethernet connectivity</li><li>Duplex printing</li><li>Touchscreen display</li>",
                    "description_text": "The TechPrint 2000 is designed to meet the demands of modern businesses with its robust performance and user-friendly interface."
                }

            # 生成文档内容
            self._generate_documentation_content()

        except Exception as e:
            print(f"初始化网站内容失败: {e}")
            # 使用默认内容
            self.website_info = {
                "company_name": "Tech Soulutions",
                "model_name": "TechPrint 2000",
                "welcome_text": "Welcome to Tech Soulutions, leading manufacturer of high-quality printing solutions.",
                "features_list": "<li>High-speed printing up to 30 ppm</li><li>1200 dpi resolution</li><li>Wireless and Ethernet connectivity</li><li>Duplex printing</li><li>Touchscreen display</li>",
                "description_text": "The TechPrint 2000 is designed to meet the demands of modern businesses with its robust performance and user-friendly interface."
            }
            self._generate_documentation_content()

    def _generate_documentation_content(self):
        """生成文档内容并缓存"""
        try:
            prompt = f"""你是一个{self.identity['prompt']}的打印机公司。请生成技术文档内容（只返回HTML格式的div内容，包含多个section）：
- 安装指南
- 使用说明
- 故障排除
- 技术规格

每个section包含h3标题和详细内容。只返回HTML内容，不要完整的HTML文档。"""

            messages = [
                {"role": "system", "content": "你是一个打印机公司的技术文档生成器，只返回HTML格式的文档内容。"},
                {"role": "user", "content": prompt}
            ]

            response = self.openai_client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=self.temperature,
                max_tokens=800
            )

            self.doc_content = response.choices[0].message.content

        except Exception as e:
            print(f"生成文档内容失败: {e}")
            # 使用默认文档内容
            self.doc_content = """
            <div class="section">
                <h3>Installation Guide</h3>
                <p>Follow these steps to install your TechPrint 2000 printer:</p>
                <ol>
                    <li>Unpack the printer and remove all packaging materials</li>
                    <li>Connect the power cable to the printer and electrical outlet</li>
                    <li>Install the ink cartridges as shown in the quick start guide</li>
                    <li>Load paper into the input tray</li>
                    <li>Turn on the printer and follow the on-screen setup wizard</li>
                </ol>
            </div>
            <div class="section">
                <h3>Usage Instructions</h3>
                <p>The TechPrint 2000 features an intuitive touchscreen interface for easy operation. Use the navigation buttons to access different functions and settings.</p>
            </div>
            <div class="section">
                <h3>Troubleshooting</h3>
                <p>If you experience any issues with your printer, refer to the troubleshooting section in the user manual or contact our technical support team.</p>
            </div>
            <div class="section">
                <h3>Technical Specifications</h3>
                <ul>
                    <li>Print Resolution: Up to 1200 dpi</li>
                    <li>Print Speed: Up to 30 pages per minute</li>
                    <li>Connectivity: USB, Ethernet, Wi-Fi</li>
                    <li>Paper Capacity: 250 sheets</li>
                </ul>
            </div>
            """

    def get_home_page(self):
        """获取首页内容（使用缓存）"""
        if "home" not in self.content_cache:
            self.content_cache["home"] = HTML_TEMPLATES["home"].format(
                company_name=self.website_info["company_name"],
                model_name=self.website_info["model_name"],
                welcome_text=self.website_info["welcome_text"],
                features_list=self.website_info["features_list"],
                description_text=self.website_info["description_text"]
            )
        return self.content_cache["home"]

    def get_documentation_page(self):
        """获取文档页面内容（使用缓存）"""
        if "documentation" not in self.content_cache:
            self.content_cache["documentation"] = HTML_TEMPLATES["documentation"].format(
                company_name=self.website_info["company_name"],
                model_name=self.website_info["model_name"],
                doc_content=self.doc_content
            )
        return self.content_cache["documentation"]

    def get_contact_page(self):
        """获取联系页面内容（使用缓存）"""
        if "contact" not in self.content_cache:
            self.content_cache["contact"] = HTML_TEMPLATES["contact"].format(
                company_name=self.website_info["company_name"],
                model_name=self.website_info["model_name"]
            )
        return self.content_cache["contact"]

    def get_css(self):
        """获取CSS内容（使用缓存）"""
        if "css" not in self.content_cache:
            self.content_cache["css"] = HTML_TEMPLATES["css"].format(
                company_name=self.website_info["company_name"],
                model_name=self.website_info["model_name"]
            )
        return self.content_cache["css"]

    def get_error_page(self):
        """获取错误页面内容（使用缓存）"""
        if "error_400" not in self.content_cache:
            self.content_cache["error_400"] = HTML_TEMPLATES["error_400"]
        return self.content_cache["error_400"]

    def get_other_page(self):
        """获取其他页面内容"""
        return HTML_TEMPLATES["error_400"].format(
            company_name=self.website_info["company_name"],
            model_name=self.website_info["model_name"]
        )

    def detect_xss(self, query):
        """检测XSS攻击"""
        xss_patterns = [
            '<script>', '</script>', 'javascript:', 'onload=', 'onerror=',
            'onclick=', 'onmouseover=', 'alert(', 'confirm(', 'prompt(',
            'document.cookie', 'window.location', 'eval(', 'innerHTML'
        ]
        query_lower = query.lower()
        for pattern in xss_patterns:
            if pattern in query_lower:
                return True, pattern
        return False, None

    def detect_sql_injection(self, query):
        """检测SQL注入攻击"""
        sql_patterns = [
            "' OR '1'='1", "' OR 1=1", "'; DROP TABLE", "UNION SELECT",
            "SELECT * FROM", "INSERT INTO", "UPDATE SET", "DELETE FROM",
            "CREATE TABLE", "ALTER TABLE", "EXEC ", "EXECUTE ",
            "xp_cmdshell", "sp_", "WAITFOR DELAY", "BENCHMARK("
        ]
        query_lower = query.lower()
        for pattern in sql_patterns:
            if pattern.lower() in query_lower:
                return True, pattern
        return False, None

    def detect_command_injection(self, query):
        """检测命令注入攻击"""
        cmd_patterns = [
            '; ls', '; cat', '; whoami', '; id', '; pwd', '; dir',
            '| ls', '| cat', '| whoami', '| id', '| pwd', '| dir',
            '&& ls', '&& cat', '&& whoami', '&& id', '&& pwd', '&& dir',
            '`ls`', '`cat`', '`whoami`', '`id`', '`pwd`', '`dir`',
            '$(ls)', '$(cat)', '$(whoami)', '$(id)', '$(pwd)', '$(dir)'
        ]
        query_lower = query.lower()
        for pattern in cmd_patterns:
            if pattern.lower() in query_lower:
                return True, pattern
        return False, None

    def detect_path_traversal(self, query):
        """检测路径遍历攻击"""
        path_patterns = [
            '../', '..\\', '....//', '....\\\\', '/etc/passwd', '/etc/shadow',
            'C:\\Windows\\System32', 'C:\\Windows\\System32\\drivers\\etc\\hosts',
            '..%2f', '..%5c', '%2e%2e%2f', '%2e%2e%5c'
        ]
        query_lower = query.lower()
        for pattern in path_patterns:
            if pattern.lower() in query_lower:
                return True, pattern
        return False, None

    def get_search_page(self, search_query=""):
        """获取搜索页面内容"""
        # 预定义打印机产品数据
        printer_products = [
            {
                "id": "P1000",
                "name": "ProPrint 1000",
                "model": "PP-1000",
                "type": "Laser Printer",
                "price": "$299.99",
                "image": "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjNjY3ZWVhIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxOCIgZmlsbD0id2hpdGUiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGR5PSIuM2VtIj5Qcm9QcmludCAxMDAwPC90ZXh0Pjwvc3ZnPg==",
                "description": "High-speed laser printer with wireless connectivity",
                "features": ["Wireless Printing", "Duplex Printing", "Mobile App Support", "Cloud Printing"],
                "specs": {"Speed": "25 ppm", "Resolution": "1200 dpi", "Paper Size": "A4"}
            },
            {
                "id": "P2000",
                "name": "ProPrint 2000",
                "model": "PP-2000",
                "type": "Inkjet Printer",
                "price": "$199.99",
                "image": "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjNzY0YmEyIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxOCIgZmlsbD0id2hpdGUiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGR5PSIuM2VtIj5Qcm9QcmludCAyMDAwPC90ZXh0Pjwvc3ZnPg==",
                "description": "Color inkjet printer with photo quality printing",
                "features": ["Color Printing", "Photo Quality", "WiFi Direct", "Borderless Printing"],
                "specs": {"Speed": "15 ppm", "Resolution": "4800 dpi", "Paper Size": "A4/A3"}
            },
            {
                "id": "P3000",
                "name": "ProPrint 3000",
                "model": "PP-3000",
                "type": "All-in-One",
                "price": "$399.99",
                "image": "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjA5M2ZiIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxOCIgZmlsbD0id2hpdGUiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGR5PSIuM2VtIj5Qcm9QcmludCAzMDAwPC90ZXh0Pjwvc3ZnPg==",
                "description": "All-in-one printer with scan, copy, and fax capabilities",
                "features": ["Print/Scan/Copy", "Fax Function", "Touch Screen", "Auto Document Feeder"],
                "specs": {"Speed": "20 ppm", "Resolution": "2400 dpi", "Paper Size": "A4"}
            },
            {
                "id": "P4000",
                "name": "ProPrint 4000",
                "model": "PP-4000",
                "type": "3D Printer",
                "price": "$899.99",
                "image": "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjU1NzZjIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxOCIgZmlsbD0id2hpdGUiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGR5PSIuM2VtIj5Qcm9QcmludCA0MDAwPC90ZXh0Pjwvc3ZnPg==",
                "description": "Professional 3D printer for rapid prototyping",
                "features": ["3D Printing", "Large Build Volume", "Heated Bed", "Filament Detection"],
                "specs": {"Build Volume": "200x200x200mm", "Layer Height": "0.1mm", "Nozzle": "0.4mm"}
            },
            {
                "id": "P5000",
                "name": "ProPrint 5000",
                "model": "PP-5000",
                "type": "Label Printer",
                "price": "$149.99",
                "image": "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjNGZhY2ZlIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxOCIgZmlsbD0id2hpdGUiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGR5PSIuM2VtIj5Qcm9QcmludCA1MDAwPC90ZXh0Pjwvc3ZnPg==",
                "description": "Industrial label printer for barcode and RFID printing",
                "features": ["Barcode Printing", "RFID Encoding", "Industrial Grade", "High Speed"],
                "specs": {"Speed": "6 ips", "Resolution": "203 dpi", "Label Width": "4 inch"}
            }
        ]

        search_results = ""
        featured_products = ""

        if search_query:
            # 检测各种攻击
            xss_detected, xss_pattern = self.detect_xss(search_query)
            sql_detected, sql_pattern = self.detect_sql_injection(search_query)
            cmd_detected, cmd_pattern = self.detect_command_injection(search_query)
            path_detected, path_pattern = self.detect_path_traversal(search_query)

            # 记录攻击日志
            attack_log = []
            if xss_detected:
                attack_log.append(f"XSS Attack detected: {xss_pattern}")
            if sql_detected:
                attack_log.append(f"SQL Injection detected: {sql_pattern}")
            if cmd_detected:
                attack_log.append(f"Command Injection detected: {cmd_pattern}")
            if path_detected:
                attack_log.append(f"Path Traversal detected: {path_pattern}")

            if attack_log:
                # 模拟攻击成功的响应
                search_results = f"""
                <div class="result-item">
                    <h3>Search Results for: {search_query}</h3>
                    <p>Found 3 matching products:</p>
                    <ul>
                        <li>Product A - $299.99</li>
                        <li>Product B - $199.99</li>
                        <li>Product C - $399.99</li>
                    </ul>
                    <div style="background: #f0f0f0; padding: 10px; margin: 10px 0; border-left: 4px solid #ff6b6b;">
                        <strong>⚠️ Security Alert:</strong><br>
                        {chr(10).join(attack_log)}
                    </div>
                </div>
                """
            else:
                # 正常搜索结果 - 根据搜索词过滤产品
                search_lower = search_query.lower()
                filtered_products = []

                for product in printer_products:
                    if (search_lower in product["name"].lower() or
                            search_lower in product["model"].lower() or
                            search_lower in product["type"].lower() or
                            search_lower in product["description"].lower()):
                        filtered_products.append(product)

                if filtered_products:
                    products_html = ""
                    for product in filtered_products:
                        features_html = "".join(
                            [f'<span class="feature-tag">{feature}</span>' for feature in product["features"][:3]])
                        specs_html = "".join(
                            [f'<div class="spec-item"><strong>{key}:</strong> {value}</div>' for key, value in
                             product["specs"].items()])

                        products_html += f"""
                        <div class="product-card">
                            <div class="product-image">
                                <img src="{product['image']}" alt="{product['name']}" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                                <div class="image-placeholder" style="display: none;">
                                    <i class="fas fa-print"></i>
                                    <span>{product['name']}</span>
                                </div>
                            </div>
                            <div class="product-info">
                                <h3>{product['name']}</h3>
                                <p class="model">Model: {product['model']}</p>
                                <p class="type">{product['type']}</p>
                                <p class="description">{product['description']}</p>
                                <div class="features">{features_html}</div>
                                <div class="specs">{specs_html}</div>
                                <div class="price">{product['price']}</div>
                                <button class="view-details-btn">View Details</button>
                            </div>
                        </div>
                        """

                    search_results = f"""
                    <div class="search-results">
                        <h3>Search Results for: "{search_query}"</h3>
                        <p class="results-count">Found {len(filtered_products)} matching product(s)</p>
                        <div class="products-grid">
                            {products_html}
                        </div>
                    </div>
                    """
                else:
                    search_results = f"""
                    <div class="no-results">
                        <h3>No products found for: "{search_query}"</h3>
                        <p>Try searching for different keywords like "laser", "inkjet", "3D", or "label"</p>
                    </div>
                    """
        else:
            # 显示推荐产品
            featured_products = ""
            for product in printer_products[:3]:  # 显示前3个产品作为推荐
                features_html = "".join(
                    [f'<span class="feature-tag">{feature}</span>' for feature in product["features"][:2]])
                featured_products += f"""
                <div class="product-card featured">
                    <div class="product-image">
                        <img src="{product['image']}" alt="{product['name']}" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                        <div class="image-placeholder" style="display: none;">
                            <i class="fas fa-print"></i>
                            <span>{product['name']}</span>
                        </div>
                        <div class="featured-badge">Featured</div>
                    </div>
                    <div class="product-info">
                        <h3>{product['name']}</h3>
                        <p class="model">Model: {product['model']}</p>
                        <p class="type">{product['type']}</p>
                        <p class="description">{product['description']}</p>
                        <div class="features">{features_html}</div>
                        <div class="price">{product['price']}</div>
                        <button class="view-details-btn">View Details</button>
                    </div>
                </div>
                """

        return HTML_TEMPLATES["search"].format(
            company_name=self.website_info["company_name"],
            model_name=self.website_info["model_name"],
            search_query=search_query,
            search_results=search_results,
            featured_products=featured_products
        )

    def get_admin_page(self, username="", password="", command="", login_message="", command_output=""):
        """获取管理页面内容"""
        admin_script = ""
        server_info = "Apache/2.4.41 (Ubuntu)"
        db_info = "MySQL 5.7.32-0ubuntu0.18.04.1"
        user_count = "1,247"

        # 检测登录攻击
        if username and password:
            xss_detected, xss_pattern = self.detect_xss(username + password)
            sql_detected, sql_pattern = self.detect_sql_injection(username + password)

            if xss_detected or sql_detected:
                login_message = f"""
                <div style="background: #ffebee; padding: 10px; margin: 10px 0; border-left: 4px solid #f44336;">
                    <strong>⚠️ Security Alert:</strong><br>
                    {f"XSS Attack detected: {xss_pattern}" if xss_detected else ""}
                    {f"SQL Injection detected: {sql_pattern}" if sql_detected else ""}
                </div>
                """
                # 模拟登录成功（蜜罐特性）
                admin_script = """
                document.getElementById('loginForm').style.display = 'none';
                document.getElementById('adminPanel').classList.add('show');
                """
            elif username == "admin" and password == "admin123":
                login_message = """
                <div style="background: #e8f5e8; padding: 10px; margin: 10px 0; border-left: 4px solid #4caf50;">
                    <strong>✅ Login successful!</strong>
                </div>
                """
                admin_script = """
                document.getElementById('loginForm').style.display = 'none';
                document.getElementById('adminPanel').classList.add('show');
                """
            else:
                login_message = """
                <div style="background: #ffebee; padding: 10px; margin: 10px 0; border-left: 4px solid #f44336;">
                    <strong>❌ Invalid credentials!</strong>
                </div>
                """

        # 检测命令注入
        if command:
            cmd_detected, cmd_pattern = self.detect_command_injection(command)
            if cmd_detected:
                command_output = f"""
                <div style="background: #fff3e0; padding: 10px; margin: 10px 0; border-left: 4px solid #ff9800;">
                    <strong>⚠️ Command Injection detected: {cmd_pattern}</strong><br>
                    <strong>Command Output:</strong><br>
                    <pre>root@server:~# {command}
uid=0(root) gid=0(root) groups=0(root)
/home/admin
total 8
drwxr-xr-x 2 root root 4096 Jan 15 10:30 .
drwxr-xr-x 3 root root 4096 Jan 15 10:30 ..</pre>
                </div>
                """
            else:
                command_output = f"""
                <div style="background: #f5f5f5; padding: 10px; margin: 10px 0;">
                    <strong>Command Output:</strong><br>
                    <pre>root@server:~# {command}
Command not found: {command}</pre>
                </div>
                """

        return HTML_TEMPLATES["admin"].format(
            company_name=self.website_info["company_name"],
            model_name=self.website_info["model_name"],
            login_message=login_message,
            server_info=server_info,
            db_info=db_info,
            user_count=user_count,
            command_output=command_output,
            admin_script=admin_script
        )


class HTTPHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.session = kwargs.pop('session', None)
        super().__init__(*args, **kwargs)

    def do_GET(self):
        try:
            client_ip = self.client_address[0]
            request_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # 获取项目根目录
            project_root = Path(__file__).parent.parent.parent
            logs_dir = project_root / "src" / "log_manager" / "logs"
            logs_dir.mkdir(exist_ok=True)
            session_uuid = str(uuid.uuid4())
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            log_file = logs_dir / f"logHTTP_{session_uuid}_{timestamp}.txt"
            headers = dict(self.headers)
            request_info = {
                "method": self.command,
                "path": self.path,
                "headers": headers,
                "client_ip": client_ip,
                "time": request_time
            }

            # 解析查询参数
            from urllib.parse import urlparse, parse_qs
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)

            # 根据路径选择响应策略
            if self.path.startswith("/search"):
                search_query = query_params.get('q', [''])[0] if 'q' in query_params else ""
                response_content = self.session.get_search_page(search_query)
            elif self.path.startswith("/admin"):
                response_content = self.session.get_admin_page()
            elif self.path == "/":
                response_content = self.session.get_home_page()
            elif self.path == "/documentation":
                response_content = self.session.get_documentation_page()
            elif self.path == "/contact":
                response_content = self.session.get_contact_page()
            elif self.path == "/styles.css":
                response_content = self.session.get_css()
                self.send_header('Content-type', 'text/css')
            elif self.path.startswith("/") and len(self.path) > 1:
                # 其他页面使用默认模板
                response_content = self.session.get_other_page()
            else:
                response_content = self.session.get_error_page()

            self.send_response(200)
            if self.path != "/styles.css":
                self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(response_content.encode())

            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"HTTP Request: {json.dumps(request_info)}\n")
                f.write(f"Response: {response_content}\n")

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'text/html')
            self.wfile.write(b"Internal Server Error")

    def do_POST(self):
        try:
            client_ip = self.client_address[0]
            request_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # 获取项目根目录
            project_root = Path(__file__).parent.parent.parent
            logs_dir = project_root / "src" / "log_manager" / "logs"
            logs_dir.mkdir(exist_ok=True)
            session_uuid = str(uuid.uuid4())
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            log_file = logs_dir / f"logHTTP_{session_uuid}_{timestamp}.txt"

            # 读取POST数据
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')

            # 解析POST数据
            from urllib.parse import parse_qs
            post_params = parse_qs(post_data)

            headers = dict(self.headers)
            request_info = {
                "method": self.command,
                "path": self.path,
                "headers": headers,
                "post_data": post_data,
                "client_ip": client_ip,
                "time": request_time
            }

            # 根据路径处理POST请求
            if self.path == "/admin":
                username = post_params.get('username', [''])[0]
                password = post_params.get('password', [''])[0]
                response_content = self.session.get_admin_page(username=username, password=password)
            elif self.path == "/admin/command":
                command = post_params.get('command', [''])[0]
                response_content = self.session.get_admin_page(command=command)
            else:
                response_content = self.session.get_error_page()

            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(response_content.encode())

            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"HTTP Request: {json.dumps(request_info)}\n")
                f.write(f"Response: {response_content}\n")

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'text/html')
            self.wfile.write(b"Internal Server Error")


def start_http_server(openai_client, identity, model_name, temperature, max_tokens, output_dir, log_file):
    # 创建HTTP会话（只创建一次）
    session = HTTPSession(openai_client, identity, model_name, temperature, max_tokens)

    def handler(*args, **kwargs):
        return HTTPHandler(*args, session=session, **kwargs)

    server = HTTPServer(('0.0.0.0', HTTP_PORT), handler)
    print(f"HTTP服务器启动在端口 {HTTP_PORT}")
    print(f"网站信息: {session.website_info['company_name']} - {session.website_info['model_name']}")
    server.serve_forever() 