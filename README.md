# Work Memory Helper

A FastAPI-based task management system for capturing work context and resuming where you left off.

## Quick Start

### 1. Set up Python Virtual Environment

```bash
# Create virtual environment
python3 -m venv fastapi_env

# Activate it (macOS/Linux)
source fastapi_env/bin/activate

# Activate it (Windows)
fastapi_env\Scripts\activate

# Your terminal prompt should now show (fastapi_env)
```

### 2. Install Dependencies

```bash
# Install all required packages
pip install fastapi uvicorn sqlalchemy python-multipart

# OR install FastAPI with all optional dependencies
pip install fastapi[all] sqlalchemy
```

### 3. Run the Application

**Option A: Using uvicorn (recommended)**
```bash
uvicorn app:app --reload
```

**Option B: Direct Python execution**
```bash
python3 app.py
```

### 4. Access the Application

- **Web Interface**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Resume Page**: http://localhost:8000/resume/ui

## Key Features

- **Quick Capture**: Save tasks with context and next actions
- **Resume**: Pick up where you left off on your most recent task
- **Projects**: Organize tasks by project
- **Notes**: Add timestamped notes to tasks (note, decision, blocker, snapshot)
- **Task Management**: Create, update, delete tasks with priorities and status tracking
- **Dark/Light Theme**: Toggle in the UI
- **Individual Task Views**: Detailed view for each task with markdown support

## API Endpoints

### Web Interface
- `GET /` - Main web interface
- `POST /quick-capture` - Save task via web form
- `GET /resume/ui` - Resume page (HTML)
- `GET /tasks/{id}/ui` - Individual task view (HTML)

### API Endpoints
- `GET /resume` - Get most recent active task (JSON)
- `GET /api/tasks` - List all tasks
- `POST /api/tasks` - Create new task
- `GET /api/tasks/{id}` - Get specific task
- `PATCH /api/tasks/{id}` - Update task
- `DELETE /api/tasks/{id}` - Delete task
- `POST /api/notes` - Add note to task
- `GET /api/tasks/{id}/notes` - Get task notes
- `DELETE /api/notes/{id}` - Delete note
- `GET /api/projects` - List all projects
- `POST /api/projects` - Create new project

## File Structure

```
workflow/
├── app.py           # Main FastAPI application
├── worklog.db       # SQLite database (auto-created)
├── fastapi_env/     # Virtual environment
└── README.md        # This file
```

## Database Schema

The application uses SQLite with three main tables:

- **Projects**: Organize related tasks
- **Tasks**: Main work items with status, priority, and context
- **Notes**: Timestamped entries linked to tasks

## Troubleshooting

### Common Issues

**ModuleNotFoundError**
```bash
# Make sure virtual environment is activated
source fastapi_env/bin/activate

# Install missing packages
pip install fastapi uvicorn sqlalchemy python-multipart
```

**Port already in use**
```bash
# Use a different port
uvicorn app:app --reload --port 8001
```

**Database issues**
```bash
# Delete and recreate database
rm worklog.db

# Restart the app to recreate tables
uvicorn app:app --reload
```

**Tasks not loading in UI**
```bash
# Check browser console for JavaScript errors
# Ensure you're using a modern browser
# Try hard refresh (Ctrl+F5 or Cmd+Shift+R)
```

### Checking Your Setup

```bash
# Verify Python version (3.7+ required)
python3 --version

# Check if virtual environment is active
which python3
# Should show path with fastapi_env

# List installed packages
pip list

# Verify FastAPI installation
python3 -c "import fastapi; print(f'FastAPI version: {fastapi.__version__}')"
```

## Development Commands

```bash
# Activate environment
source fastapi_env/bin/activate

# Install new dependencies
pip install package_name

# Save current dependencies
pip freeze > requirements.txt

# Install from requirements (future setup)
pip install -r requirements.txt

# Run with auto-reload for development
uvicorn app:app --reload --host 0.0.0.0 --port 8000

# Deactivate environment when done
deactivate
```

## Usage Tips

1. **Quick Capture**: Use the main form to quickly save context when switching tasks
2. **Next Actions**: Keep these concrete and actionable (10-15 words)
3. **Notes**: Use different note types:
   - `note`: General observations
   - `decision`: Important choices made
   - `blocker`: Issues preventing progress
   - `snapshot`: Current state captures
4. **Resume**: Always check the resume page when returning to work
5. **Projects**: Group related tasks for better organization

## Next Time Setup

If you return to this project later:

```bash
# Navigate to project directory
cd /path/to/workflow

# Activate virtual environment
source fastapi_env/bin/activate

# Run the application
uvicorn app:app --reload

# Open browser to http://localhost:8000
```

That's it! The database and all your data will persist between sessions.

## Contributing

This is a personal productivity tool. Feel free to modify the code to suit your workflow needs.

## License

This project is for personal use.
