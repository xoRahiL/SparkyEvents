# Deployment Guide: PostgreSQL + Render

## ✅ What's Done

- ✓ PostgreSQL support added to `settings.py`
- ✓ `requirements.txt` created with all dependencies
- ✓ `render.yaml` configured for Render deployment
- ✓ Gunicorn added (web server for production)
- ✓ Celery disabled for production (Render free tier limitation)
- ✓ ALLOWED_HOSTS configured for Render domains

---

## 🔧 Local Testing (PostgreSQL)

### 1. Install PostgreSQL

**Mac:**
```bash
brew install postgresql@15
brew services start postgresql@15
```

**Windows:** https://www.postgresql.org/download/windows/

**Linux:**
```bash
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql
```

### 2. Create Database

```bash
psql -U postgres

# In psql:
CREATE DATABASE sparky;
CREATE USER sparky_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE sparky TO sparky_user;
\q
```

### 3. Update `.env` for Local PostgreSQL

```env
DEBUG=True
IS_PRODUCTION=False
SECRET_KEY=your-secret-key

DB_ENGINE=postgresql
DB_NAME=sparky
DB_USER=sparky_user
DB_PASSWORD=secure_password
DB_HOST=localhost
DB_PORT=5432

EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

### 4. Install & Migrate

```bash
pip install -r requirements.txt
cd projectspark
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### 5. Test Profile Upload

Upload a landscape screenshot to verify circular profile pic works.

---

## 🚀 Deploy to Render

### Step 1: Push to GitHub

```bash
git add .
git commit -m "PostgreSQL setup + Render deployment config"
git push origin optimized-version
```

### Step 2: Create Render Account

1. Go to https://render.com
2. Sign up (use GitHub)
3. Create new Web Service

### Step 3: Configure Web Service

1. **Name:** `sparky-events` (or your choice)
2. **Environment:** Python
3. **Build Command:**
   ```
   pip install -r requirements.txt && python projectspark/manage.py collectstatic --noinput && python projectspark/manage.py migrate
   ```
4. **Start Command:**
   ```
   gunicorn projectspark.wsgi:application --bind 0.0.0.0:$PORT
   ```

### Step 4: Add Environment Variables

In Render dashboard, add:

```
DEBUG=False
IS_PRODUCTION=True
SECRET_KEY=<generate a new random key>
ALLOWED_HOSTS=sparky-events.onrender.com
EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
USE_CELERY=False
```

### Step 5: Create PostgreSQL Database

1. In Render dashboard, click **Create New** → **PostgreSQL**
2. **Name:** `sparky-postgres`
3. **Plan:** Free
4. Link to your Web Service (it auto-generates DATABASE_URL)

### Step 6: Deploy

Click **Deploy** and watch logs for success!

---

## ⚠️ Known Limitations (Free Tier)

| Feature | Status | Notes |
|---------|--------|-------|
| Static Files | ✅ Works | WhiteNoise handles this |
| Database | ✅ Works | PostgreSQL free tier |
| Media Upload | ⚠️ Ephemeral | Files deleted on restart → **Need S3 next** |
| Background Jobs | ❌ No | USE_CELERY=False (emails sync) |
| HTTPS | ✅ Auto | Render provides SSL cert |
| Cold Starts | ⚠️ 15+ sec | Free tier spins down after inactivity |

---

## 🔜 Next: Add AWS S3 for Media Storage

Profile pictures currently get deleted on app restart. For persistence, add S3:

```bash
pip install boto3 django-storages
```

Then configure in settings.py:
```python
if IS_PRODUCTION:
    STORAGES = {
        'default': {
            'BACKEND': 'storages.backends.s3boto3.S3Boto3Storage',
            'OPTIONS': {
                'AWS_STORAGE_BUCKET_NAME': 'sparky-media',
                'AWS_S3_REGION_NAME': 'us-east-1',
            }
        }
    }
```

But first, test PostgreSQL locally and on Render!

---

## 🐛 Troubleshooting

**Issue: "psycopg2.OperationalError: FATAL"**
- ✓ Check DATABASE_URL is set in Render dashboard
- ✓ Wait 2-3 minutes for PostgreSQL to be ready

**Issue: Static files not loading**
- ✓ Run: `python manage.py collectstatic --noinput`
- ✓ Check WhiteNoise is in MIDDLEWARE

**Issue: "ALLOWED_HOSTS" error**
- ✓ Update ALLOWED_HOSTS in .env with your Render domain

---

## 📝 Checklist Before Deploying

- [ ] PostgreSQL works locally
- [ ] All migrations run: `python manage.py migrate`
- [ ] Static files collected: `python manage.py collectstatic`
- [ ] SECRET_KEY is strong and in .env
- [ ] DEBUG=False in production
- [ ] IS_PRODUCTION=True in production
- [ ] EMAIL credentials set
- [ ] ALLOWED_HOSTS includes Render domain
- [ ] Code committed to GitHub
- [ ] render.yaml in project root

---

Good luck! 🎉
