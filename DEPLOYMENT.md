# English Level Quiz - Deployment Guide

## 🚀 Quick Deploy (Server)

### Step 1: Update pip
```bash
pip install --upgrade pip
```

### Step 2: Install dependencies one by one
```bash
# Core dependencies
pip install flask
pip install flask-cors
pip install aiogram

# For production server
pip install gunicorn

# Optional - for PDF certificates (may fail on some systems)
pip install reportlab
```

### Step 3: Run the application

**Development mode:**
```bash
python app.py
```

**Production mode (recommended for server):**
```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

**Run on specific port:**
```bash
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

### Step 4: Run Telegram Bot (optional)
```bash
python bot.py
```

---

## 🐛 Troubleshooting

### ❌ If you get "metadata-generation-failed" error:

**Solution 1:** Install packages individually instead of using requirements.txt
```bash
pip install --upgrade pip
pip install flask flask-cors aiogram gunicorn
```

**Solution 2:** Skip reportlab if it fails
```bash
pip install aiogram flask flask-cors gunicorn
# Skip reportlab - PDF certificates will be disabled but app will work
```

**Solution 3:** Use virtual environment
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

pip install --upgrade pip
pip install flask flask-cors aiogram gunicorn
```

### ❌ Python version too old:
Make sure you have Python 3.8 or higher:
```bash
python --version
# or
python3 --version
```

### ❌ Port already in use:
Change the port in deployment command:
```bash
gunicorn -w 4 -b 0.0.0.0:8080 app:app
```

---

## 🌐 Deploy to Cloud Platforms

### **Render.com**
1. Connect GitHub repository
2. Set build command: `pip install flask flask-cors aiogram gunicorn`
3. Set start command: `gunicorn -w 4 app:app`

### **Heroku**
1. Create `Procfile`:
   ```
   web: gunicorn app:app
   ```
2. Push to Heroku:
   ```bash
   heroku create
   git push heroku main
   ```

### **PythonAnywhere**
1. Upload files
2. Setup virtual environment
3. Install packages: `pip install flask flask-cors`
4. Configure WSGI file

### **Railway**
1. Connect GitHub
2. Auto-detects Python and installs dependencies
3. Set start command: `gunicorn -w 4 app:app`

---

## ✅ Minimal Installation (If having issues)

If you're having trouble installing all dependencies, use this minimal setup:

```bash
pip install flask flask-cors
python app.py
```

This will run the web app without:
- PDF certificate generation (reportlab)
- Telegram bot features (aiogram)

The web quiz will still work perfectly! 🎯

---

## 📋 Environment Variables (Optional)

Create `.env` file:
```
FLASK_SECRET_KEY=your-secret-key-here
FLASK_DEBUG=False
DATABASE_PATH=english_quiz.db
```

---

## 🔒 Security for Production

1. **Change secret key in app.py:**
   ```python
   app.secret_key = 'YOUR-SECURE-RANDOM-KEY-HERE'
   ```

2. **Disable debug mode:**
   ```python
   app.run(debug=False)  # in app.py
   ```

3. **Use environment variables for sensitive data**

4. **Set up HTTPS** (use platform's SSL/TLS)

---

## ✨ Success!

Once deployed, your web app will be available at:
- Local: `http://localhost:5000`
- Server: `http://your-server-ip:5000`

Enjoy your English Level Quiz! 🎓
