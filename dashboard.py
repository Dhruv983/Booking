import os
from datetime import datetime
from pathlib import Path
import shutil
from jinja2 import Environment, FileSystemLoader
import glob

class ScreenshotDashboard:
    def __init__(self, screenshots_dir="screenshots"):
        self.screenshots_dir = screenshots_dir
        self.template_dir = "templates"
        self.output_dir = "dashboard"
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.template_dir, exist_ok=True)

    def get_screenshot_data(self):
        """Get screenshots organized by date and user."""
        data = {}
        
        # Get all date directories
        date_dirs = sorted(glob.glob(f"{self.screenshots_dir}/*"), reverse=True)
        
        for date_dir in date_dirs:
            date = os.path.basename(date_dir)
            try:
                # Validate date format
                datetime.strptime(date, "%Y-%m-%d")
                data[date] = {}
                
                # Get all workflow runs for this date
                workflow_dirs = sorted(glob.glob(f"{date_dir}/workflow_*"))
                
                for workflow_dir in workflow_dirs:
                    workflow_id = os.path.basename(workflow_dir)
                    
                    # Get all process directories
                    process_dirs = glob.glob(f"{workflow_dir}/process_*")
                    
                    for process_dir in process_dirs:
                        # Get all user directories
                        user_dirs = glob.glob(f"{process_dir}/*")
                        
                        for user_dir in user_dirs:
                            user = os.path.basename(user_dir)
                            if user not in data[date]:
                                data[date][user] = []
                            
                            # Get all screenshots for this user
                            screenshots = sorted(glob.glob(f"{user_dir}/*.png"))
                            
                            # Create relative paths for screenshots
                            rel_screenshots = [os.path.relpath(s, self.output_dir) for s in screenshots]
                            data[date][user].extend(rel_screenshots)
                            
            except ValueError:
                continue  # Skip invalid date directories
                
        return data

    def generate_dashboard(self):
        """Generate HTML dashboard."""
        # Copy screenshots to dashboard directory
        if os.path.exists(self.screenshots_dir):
            dest_screenshots = os.path.join(self.output_dir, "screenshots")
            if os.path.exists(dest_screenshots):
                shutil.rmtree(dest_screenshots)
            shutil.copytree(self.screenshots_dir, dest_screenshots)

        # Get screenshot data
        screenshot_data = self.get_screenshot_data()

        # Create HTML template
        template_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Booking Screenshots Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .date-section { margin-bottom: 30px; }
        .date-header { 
            background: #f0f0f0; 
            padding: 10px; 
            margin-bottom: 15px;
            border-radius: 5px;
        }
        .user-section { margin-bottom: 20px; }
        .user-header { 
            background: #e0e0e0; 
            padding: 5px 10px;
            border-radius: 3px;
        }
        .screenshots { 
            display: grid; 
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 10px;
            padding: 10px;
        }
        .screenshot {
            position: relative;
            cursor: pointer;
        }
        .screenshot img {
            max-width: 100%;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        .screenshot:hover img {
            transform: scale(1.05);
            transition: transform 0.2s;
        }
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.9);
            z-index: 1000;
        }
        .modal-content {
            max-width: 90%;
            max-height: 90%;
            margin: auto;
            display: block;
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
        }
    </style>
</head>
<body>
    <h1>Booking Screenshots Dashboard</h1>
    {% for date, users in screenshots.items() %}
    <div class="date-section">
        <div class="date-header">
            <h2>{{ date }}</h2>
        </div>
        {% for user, images in users.items() %}
        <div class="user-section">
            <div class="user-header">
                <h3>{{ user }}</h3>
            </div>
            <div class="screenshots">
                {% for image in images %}
                <div class="screenshot" onclick="showModal('{{ image }}')">
                    <img src="{{ image }}" alt="{{ image.split('/')[-1] }}">
                </div>
                {% endfor %}
            </div>
        </div>
        {% endfor %}
    </div>
    {% endfor %}

    <div id="imageModal" class="modal" onclick="hideModal()">
        <img class="modal-content" id="modalImage">
    </div>

    <script>
        function showModal(imageSrc) {
            const modal = document.getElementById('imageModal');
            const modalImg = document.getElementById('modalImage');
            modal.style.display = "block";
            modalImg.src = imageSrc;
        }

        function hideModal() {
            document.getElementById('imageModal').style.display = "none";
        }
    </script>
</body>
</html>
"""

        # Save template
        template_path = os.path.join(self.template_dir, "dashboard.html")
        with open(template_path, "w") as f:
            f.write(template_content)

        # Generate dashboard
        env = Environment(loader=FileSystemLoader(self.template_dir))
        template = env.get_template("dashboard.html")
        
        dashboard_html = template.render(screenshots=screenshot_data)
        
        with open(os.path.join(self.output_dir, "index.html"), "w") as f:
            f.write(dashboard_html)

if __name__ == "__main__":
    dashboard = ScreenshotDashboard()
    dashboard.generate_dashboard()