# Deployment Guide for Material Planning Assistant

## Files to Upload to GitHub

You need to upload these 3 files to your GitHub repository:

1. **material_planning_assistant.py** - The main application code
2. **requirements.txt** - Python dependencies
3. **MV_Material_Study-*.xlsx** - Your Excel data file
4. **README.md** (optional) - Documentation

---

## Quick Deployment Steps

### 1. Create GitHub Repository
- Go to https://github.com/new
- Name: `material-planning-app`
- Visibility: Public
- Click "Create repository"

### 2. Upload Files
- Click "Add file" → "Upload files"
- Drag and drop all files
- Click "Commit changes"

### 3. Deploy to Streamlit Cloud
- Go to https://share.streamlit.io
- Sign in with GitHub
- Click "New app"
- Select your repository
- Main file: `material_planning_assistant.py`
- Click "Deploy!"

### 4. Your App is Live!
- You'll get a URL like: `https://your-app.streamlit.app`
- Share with your team

---

## Updating Your App

To update your deployed app:

1. Edit files on GitHub (or push from local)
2. Streamlit Cloud will automatically redeploy
3. Changes will be live in 1-2 minutes

---

## Troubleshooting

**Problem**: App won't start
**Solution**: Check that all files are uploaded and requirements.txt is correct

**Problem**: "File not found" error
**Solution**: Make sure your Excel file is in the repository

**Problem**: Import errors
**Solution**: Add missing packages to requirements.txt

---

## Support

For issues with:
- **Streamlit Cloud**: https://discuss.streamlit.io
- **The app code**: Check the README.md file

---

## Tips

- Keep your repository public for free hosting
- Add `.streamlit/config.toml` for custom themes
- Use secrets management for sensitive data
- Monitor app usage in Streamlit Cloud dashboard

Good luck with your deployment! 🚀
