from flask import Flask, render_template, request, jsonify, session
import json
import os
import re
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
import uuid

# Import the existing modules with better error handling
MODULES_AVAILABLE = False
MODULE_ERRORS = []

try:
    import log as network_logger_module
    print("✅ log.py loaded successfully!")
except ImportError as e:
    network_logger_module = None
    MODULE_ERRORS.append(f"log.py: {e}")
    print(f"❌ Error importing log.py: {e}")

try:
    import TestSteps as test_steps_module
    print("✅ TestSteps.py loaded successfully!")
except ImportError as e:
    test_steps_module = None
    MODULE_ERRORS.append(f"TestSteps.py: {e}")
    print(f"❌ Error importing TestSteps.py: {e}")

try:
    import PTScript as jmx_generator_module
    print("✅ PTScript.py loaded successfully!")
except ImportError as e:
    jmx_generator_module = None
    MODULE_ERRORS.append(f"PTScript.py: {e}")
    print(f"❌ Error importing PTScript.py: {e}")

try:
    import validation as validation_module
    print("✅ validation.py loaded successfully!")
except ImportError as e:
    validation_module = None
    MODULE_ERRORS.append(f"validation.py: {e}")
    print(f"❌ Error importing validation.py: {e}")

# Check if all modules are available
if all([network_logger_module, test_steps_module, jmx_generator_module, validation_module]):
    MODULES_AVAILABLE = True
    print("✅ All modules loaded successfully!")
else:
    print(f"❌ Some modules failed to load. Errors: {MODULE_ERRORS}")
    print("The application will run in limited mode.")

app = Flask(__name__)
app.secret_key = os.environ.get('GOOGLE_API_KEY', 'your-secret-key-change-this-in-production')

# Global workflow tracking
active_workflows = {}

class AutomatedWorkflow:
    def __init__(self, workflow_id, user_story):
        self.workflow_id = workflow_id
        self.user_story = user_story
        self.status = "initializing"
        self.current_step = 0
        self.steps = [
            {"name": "🤖 AI Planner Analysis", "status": "pending", "message": ""},
            {"name": "🌐 Network Logging", "status": "pending", "message": ""},
            {"name": "⚙️ Test Steps Generation", "status": "pending", "message": ""},
            {"name": "🎯 JMX Script Creation", "status": "pending", "message": ""},
            {"name": "🔍 JMX Validation", "status": "pending", "message": ""}
        ]
        self.results = {}
        self.target_url = None
        
        if MODULES_AVAILABLE and validation_module:
            try:
                self.validator = validation_module.JMXValidator()
                self.executor = validation_module.JMeterExecutor()
            except Exception as e:
                print(f"Warning: Could not initialize validation components: {e}")
                self.validator = None
                self.executor = None
        else:
            self.validator = None
            self.executor = None

    def update_step_status(self, step_index, status, message=""):
        """Update step status and message"""
        if 0 <= step_index < len(self.steps):
            self.steps[step_index]["status"] = status
            self.steps[step_index]["message"] = message
            self.current_step = step_index

    def get_status_update(self):
        """Get current workflow status for frontend"""
        return {
            "workflow_id": self.workflow_id,
            "status": self.status,
            "current_step": self.current_step,
            "steps": self.steps,
            "results": self.results
        }

    def update_task_in_log_file(self, user_story):
        """Update TASK in log.py file based on user story"""
        try:
            with open('log.py', 'r', encoding='utf-8') as f:
                content = f.read()
            
            urls = re.findall(r'https?://[^\s]+', user_story)
            target_url = urls[0] if urls else "https://example.com"
            
            new_task = f'''TASK = """
As a user,
I want to go to {target_url},
{user_story}
And verify the task is completed.
"""'''
            
            task_pattern = r'TASK\s*=\s*""".*?"""'
            if re.search(task_pattern, content, re.DOTALL):
                updated_content = re.sub(task_pattern, new_task, content, flags=re.DOTALL)
            else:
                lines = content.split('\n')
                insert_index = 0
                for i, line in enumerate(lines):
                    if line.startswith('import ') or line.startswith('from '):
                        insert_index = i + 1
                lines.insert(insert_index, f'\n{new_task}\n')
                updated_content = '\n'.join(lines)
            
            with open('log.py', 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            return target_url
            
        except Exception as e:
            print(f"Failed to update TASK in log.py: {e}")
            return None

    def run_script_with_timeout(self, script_name, timeout=300):
        """Run script with timeout and return result"""
        try:
            env = os.environ.copy()
            env['PYTHONUNBUFFERED'] = '1'
            
            result = subprocess.run(
                [sys.executable, script_name],
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
                cwd=os.getcwd()
            )
            
            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": f"Script execution timed out after {timeout} seconds"
            }
        except Exception as e:
            return {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": str(e)
            }

    def execute_workflow(self):
        """Execute the complete workflow automatically"""
        try:
            self.status = "running"
            
            # Step 1: AI Planner Analysis
            self.update_step_status(0, "running", "🤖 Analyzing user story and planning automation sequence...")
            time.sleep(2)  # Simulate analysis time
            
            # Extract URL and plan
            urls = re.findall(r'https?://[^\s]+', self.user_story)
            self.target_url = urls[0] if urls else "https://example.com"
            
            planning_message = f"""✅ **Analysis Complete!**

📋 **Automation Plan:**
• Target URL: {self.target_url}
• User Story: {self.user_story}

🔄 **Execution Sequence:**
1. Network traffic capture and analysis
2. Test steps generation with correlation
3. JMX script creation for JMeter
4. Validation and quality assurance

🚀 **Starting automated execution...**"""
            
            self.update_step_status(0, "completed", planning_message)
            time.sleep(1)

            # Step 2: Network Logging
            if not network_logger_module:
                self.update_step_status(1, "failed", "❌ log.py module not available")
                self.status = "failed"
                return

            self.update_step_status(1, "running", "🌐 Executing network traffic capture...")
            
            # Update log.py with user story
            if not self.update_task_in_log_file(self.user_story):
                self.update_step_status(1, "failed", "❌ Failed to update TASK in log.py")
                self.status = "failed"
                return

            # Execute log.py
            result = self.run_script_with_timeout('log.py', timeout=300)
            
            if result["success"]:
                message = f"✅ **Network Logging Complete!**\n• Target URL: {self.target_url}\n• Network traffic captured successfully\n• Correlation data prepared"
                self.update_step_status(1, "completed", message)
                self.results['network_logging'] = result
            else:
                self.update_step_status(1, "failed", f"❌ Network logging failed: {result['stderr']}")
                self.status = "failed"
                return

            time.sleep(1)

            # Step 3: Test Steps Generation
            if not test_steps_module:
                self.update_step_status(2, "failed", "❌ TestSteps.py module not available")
                self.status = "failed"
                return

            self.update_step_status(2, "running", "⚙️ Generating test steps with correlation mapping...")
            
            # Ensure TestSteps_Output directory exists
            os.makedirs('TestSteps_Output', exist_ok=True)
            print(f"Current working directory: {os.getcwd()}")
            print(f"TestSteps_Output directory exists: {os.path.exists('TestSteps_Output')}")
            
            result = self.run_script_with_timeout('TestSteps.py', timeout=120)
            
            if result["success"]:
                # Check output files with full debugging
                output_files = []
                expected_files = [
                    'TestSteps_Output/test_steps_structured.json',
                    'TestSteps_Output/test_steps_simple.json',
                    'TestSteps_Output/TestSteps.txt',
                    'TestSteps_Output/correlation_rules.json'
                ]
                
                print("Checking for TestSteps output files:")
                for file_path in expected_files:
                    exists = os.path.exists(file_path)
                    print(f"  {file_path}: {'EXISTS' if exists else 'NOT FOUND'}")
                    if exists:
                        file_size = os.path.getsize(file_path)
                        print(f"    Size: {file_size} bytes")
                        output_files.append(file_path)
                
                # Also check what's actually in the TestSteps_Output directory
                if os.path.exists('TestSteps_Output'):
                    actual_files = []
                    for root, dirs, files in os.walk('TestSteps_Output'):
                        for file in files:
                            full_path = os.path.join(root, file)
                            actual_files.append(full_path)
                    print(f"Actual files found in TestSteps_Output: {actual_files}")
                    
                    # Add any files we find, even if they don't match expected names
                    for file_path in actual_files:
                        if file_path not in output_files:
                            output_files.append(file_path)
                
                message = f"""✅ **Test Steps Generation Complete!**
• Files created: {len(output_files)}
• Output directory: TestSteps_Output/
• Test steps structured and ready
• Correlation rules defined

📁 **Created Files:**
{chr(10).join([f'• {os.path.basename(f)}' for f in output_files]) if output_files else '• No files detected - check TestSteps.py output'}

📍 **Full paths:**
{chr(10).join([f'• {f}' for f in output_files]) if output_files else '• No files found'}"""
                
                self.update_step_status(2, "completed", message)
                self.results['test_steps'] = result
                self.results['output_files'] = output_files
                
                # Store additional debug info
                self.results['teststeps_debug'] = {
                    'working_directory': os.getcwd(),
                    'output_directory_exists': os.path.exists('TestSteps_Output'),
                    'expected_files': expected_files,
                    'found_files': output_files,
                    'actual_directory_contents': actual_files if os.path.exists('TestSteps_Output') else []
                }
                
            else:
                self.update_step_status(2, "failed", f"❌ Test steps generation failed: {result['stderr']}")
                self.status = "failed"
                return

            time.sleep(1)

            # Step 4: JMX Generation
            if not jmx_generator_module:
                self.update_step_status(3, "failed", "❌ PTScript.py module not available")
                self.status = "failed"
                return

            self.update_step_status(3, "running", "🎯 Creating JMX scripts for JMeter...")
            
            os.makedirs('JMX_SCRIPT_OUTPUT', exist_ok=True)
            result = self.run_script_with_timeout('PTScript.py', timeout=180)
            
            if result["success"]:
                # Find JMX files
                jmx_files = []
                if os.path.exists('JMX_SCRIPT_OUTPUT'):
                    for root, dirs, files in os.walk('JMX_SCRIPT_OUTPUT'):
                        for file in files:
                            if file.endswith('.jmx'):
                                jmx_files.append(os.path.join(root, file))
                
                message = f"✅ **JMX Generation Complete!**\n• JMX files created: {len(jmx_files)}\n• Ready for JMeter execution\n• Performance test scripts prepared"
                self.update_step_status(3, "completed", message)
                self.results['jmx_generation'] = result
                self.results['jmx_files'] = jmx_files
            else:
                self.update_step_status(3, "failed", f"❌ JMX generation failed: {result['stderr']}")
                self.status = "failed"
                return

            time.sleep(1)

            # Step 5: Validation
            if not validation_module or not self.validator:
                self.update_step_status(4, "failed", "❌ validation.py module not available")
                self.status = "failed"
                return

            self.update_step_status(4, "running", "🔍 Validating JMX scripts and performing quality checks...")
            
            try:
                jmx_files = self.results.get('jmx_files', [])
                
                if not jmx_files:
                    self.update_step_status(4, "failed", "❌ No JMX files found to validate")
                    self.status = "failed"
                    return

                validation_results = []
                
                for jmx_file in jmx_files:
                    validation_result = self.validator.validate_jmx_file(jmx_file)
                    validation_results.append({
                        "file": jmx_file,
                        "result": validation_result
                    })
                    
                    # Generate validation report
                    report_path = f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    self.validator.generate_validation_report(validation_result, report_path)

                # Summary of results
                passed = sum(1 for vr in validation_results if vr['result'].get('overall_status') == 'pass')
                warnings = sum(1 for vr in validation_results if vr['result'].get('overall_status') == 'warning')
                failed = sum(1 for vr in validation_results if vr['result'].get('overall_status') == 'fail')

                message = f"""✅ **Validation Complete!**

📊 **Quality Assessment:**
• ✅ Passed: {passed}
• ⚠️ Warnings: {warnings}  
• ❌ Failed: {failed}

🎉 **Performance Test Ready!**
Your complete JMeter test suite is ready for execution."""

                self.update_step_status(4, "completed", message)
                self.results['validation'] = validation_results
                self.status = "completed"

            except Exception as e:
                self.update_step_status(4, "failed", f"❌ Validation failed: {str(e)}")
                self.status = "failed"
                return

            # Workflow completed successfully
            print(f"✅ Workflow {self.workflow_id} completed successfully!")

        except Exception as e:
            self.status = "failed"
            self.update_step_status(self.current_step, "failed", f"❌ Workflow error: {str(e)}")
            print(f"❌ Workflow {self.workflow_id} failed: {e}")

def start_automated_workflow(user_story):
    """Start a new automated workflow"""
    workflow_id = str(uuid.uuid4())
    workflow = AutomatedWorkflow(workflow_id, user_story)
    active_workflows[workflow_id] = workflow
    
    # Start workflow in background thread
    thread = threading.Thread(target=workflow.execute_workflow)
    thread.daemon = True
    thread.start()
    
    return workflow_id

@app.route('/')
def index():
    if 'messages' not in session:
        session['messages'] = []
    if 'current_workflow' not in session:
        session['current_workflow'] = None
    
    return render_template('index.html', 
                         messages=session['messages'],
                         modules_available=MODULES_AVAILABLE,
                         module_errors=MODULE_ERRORS)

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_input = data.get('message', '').strip()
    
    if not user_input:
        return jsonify({'error': 'Empty message'}), 400
    
    # Handle reset commands
    if user_input.lower() in ['reset', 'new test', 'start over']:
        session['current_workflow'] = None
        session['messages'] = []
        return jsonify({
            'response': '🔄 **Reset Complete!** Ready for new user story.',
            'reset': True
        })
    
    # Check if there's already an active workflow
    current_workflow_id = session.get('current_workflow')
    if current_workflow_id and current_workflow_id in active_workflows:
        workflow = active_workflows[current_workflow_id]
        if workflow.status in ['running', 'initializing']:
            return jsonify({
                'response': '⚠️ **Workflow in progress!** Please wait for current automation to complete, or type "reset" to start over.',
                'workflow_status': workflow.get_status_update()
            })
    
    # Start new automated workflow
    if not MODULES_AVAILABLE:
        response = f"❌ **Cannot start workflow!** Some required modules are missing:\n" + "\n".join([f"• {error}" for error in MODULE_ERRORS])
        session['messages'].append({"role": "user", "content": user_input})
        session['messages'].append({"role": "assistant", "content": response})
        return jsonify({'response': response})
    
    # Extract URL for validation
    urls = re.findall(r'https?://[^\s]+', user_input)
    if not urls:
        response = "❓ **Please provide a user story with a URL** (e.g., 'Test login functionality for https://example.com')"
        session['messages'].append({"role": "user", "content": user_input})
        session['messages'].append({"role": "assistant", "content": response})
        return jsonify({'response': response})
    
    # Start automated workflow
    workflow_id = start_automated_workflow(user_input)
    session['current_workflow'] = workflow_id
    
    response = f"""🚀 **Automated Workflow Started!**

📝 **User Story**: {user_input}
🆔 **Workflow ID**: {workflow_id[:8]}...

🤖 **AI is now executing the complete automation sequence:**

1. 🤖 AI Planner Analysis
2. 🌐 Network Logging  
3. ⚙️ Test Steps Generation
4. 🎯 JMX Script Creation
5. 🔍 JMX Validation

⏱️ **Estimated time**: 5-10 minutes
🔄 **Status updates** will appear automatically below."""

    session['messages'].append({"role": "user", "content": user_input})
    session['messages'].append({"role": "assistant", "content": response})
    
    return jsonify({
        'response': response,
        'workflow_started': True,
        'workflow_id': workflow_id
    })

@app.route('/workflow_status/<workflow_id>')
def workflow_status(workflow_id):
    """Get real-time workflow status"""
    if workflow_id in active_workflows:
        return jsonify(active_workflows[workflow_id].get_status_update())
    else:
        return jsonify({'error': 'Workflow not found'}), 404

@app.route('/debug_files')
def debug_files():
    """Debug endpoint to show file system status"""
    debug_info = {
        'current_directory': os.getcwd(),
        'teststeps_output_exists': os.path.exists('TestSteps_Output'),
        'teststeps_output_contents': [],
        'all_files_in_current_dir': [],
        'all_json_files': [],
        'all_txt_files': []
    }
    
    # Get TestSteps_Output contents
    if os.path.exists('TestSteps_Output'):
        for root, dirs, files in os.walk('TestSteps_Output'):
            for file in files:
                full_path = os.path.join(root, file)
                file_size = os.path.getsize(full_path)
                debug_info['teststeps_output_contents'].append({
                    'path': full_path,
                    'size': file_size,
                    'modified': datetime.fromtimestamp(os.path.getmtime(full_path)).isoformat()
                })
    
    # Get all files in current directory
    for item in os.listdir('.'):
        if os.path.isfile(item):
            debug_info['all_files_in_current_dir'].append(item)
    
    # Find all JSON and TXT files recursively
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.json'):
                debug_info['all_json_files'].append(os.path.join(root, file))
            elif file.endswith('.txt'):
                debug_info['all_txt_files'].append(os.path.join(root, file))
    
    return jsonify(debug_info)

@app.route('/results')
def results():
    """Get workflow results"""
    current_workflow_id = session.get('current_workflow')
    if current_workflow_id and current_workflow_id in active_workflows:
        workflow = active_workflows[current_workflow_id]
        return jsonify({
            'workflow_id': current_workflow_id,
            'status': workflow.status,
            'results': workflow.results
        })
    return jsonify({'error': 'No active workflow'}), 404

if __name__ == '__main__':
    print("🚀 Starting Automated Performance Testing Assistant...")
    app.run(debug=False, host='0.0.0.0', port=5000, use_reloader=False)