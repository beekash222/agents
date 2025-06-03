import streamlit as st

# Configure Streamlit page FIRST - before any other Streamlit commands
st.set_page_config(
    page_title="Automated Performance Testing Assistant",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

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

# Import the existing modules
try:
    import log as network_logger_module
    import TestSteps as test_steps_module  
    import PTScript as jmx_generator_module
    import validation as validation_module
    MODULES_AVAILABLE = True
    print("✅ All modules (log.py, TestSteps.py, PTScript.py, validation.py) loaded successfully!")
except ImportError as e:
    MODULES_AVAILABLE = False
    st.error(f"❌ Error importing modules: {e}")
    st.error("Please ensure log.py, TestSteps.py, PTScript.py, and validation.py are in the same directory as this UI file.")
    st.stop()

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        border-left: 5px solid #667eea;
        background-color: #f8f9fa;
    }
    .user-message {
        background-color: #e3f2fd;
        border-left-color: #2196f3;
    }
    .assistant-message {
        background-color: #f3e5f5;
        border-left-color: #9c27b0;
    }
    .tool-execution {
        background-color: #fff3e0;
        border-left-color: #ff9800;
        font-family: monospace;
        font-size: 0.9em;
    }
    .status-success {
        background-color: #e8f5e8;
        border-left-color: #4caf50;
    }
    .status-error {
        background-color: #ffebee;
        border-left-color: #f44336;
    }
    .progress-step {
        padding: 0.75rem;
        margin: 0.5rem 0;
        border-radius: 8px;
        font-weight: bold;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .step-completed {
        background-color: #d4edda;
        color: #155724;
        border-left: 4px solid #28a745;
    }
    .step-current {
        background-color: #fff3cd;
        color: #856404;
        border-left: 4px solid #ffc107;
    }
    .step-pending {
        background-color: #f8f9fa;
        color: #6c757d;
        border-left: 4px solid #dee2e6;
    }
    .step-failed {
        background-color: #f8d7da;
        color: #721c24;
        border-left: 4px solid #dc3545;
    }
    .module-info {
        background-color: #e9ecef;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        border-left: 4px solid #007bff;
    }
    .automation-status {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        text-align: center;
    }
    .step-details {
        background-color: #f8f9fa;
        padding: 0.5rem;
        border-radius: 4px;
        margin-top: 0.5rem;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

# Automated Workflow Class
class AutomatedWorkflow:
    def __init__(self):
        self.reset_progress()
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
    
    def reset_progress(self):
        """Reset workflow progress"""
        st.session_state.workflow_step = 0
        st.session_state.results = {}
        st.session_state.automation_status = "ready"
        st.session_state.current_step_message = ""
        st.session_state.target_url = ""
        
    def get_steps(self):
        """Get workflow steps configuration"""
        return [
            {"name": "🤖 AI Planner Analysis", "status": "pending", "message": ""},
            {"name": "🌐 Network Logging", "status": "pending", "message": ""},
            {"name": "⚙️ Test Steps Generation", "status": "pending", "message": ""},
            {"name": "🎯 JMX Script Creation", "status": "pending", "message": ""},
            {"name": "🔍 JMX Validation", "status": "pending", "message": ""}
        ]

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
            st.error(f"Failed to update TASK in log.py: {e}")
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

    def execute_automated_workflow(self, user_story):
        """Execute the complete automated workflow"""
        try:
            st.session_state.automation_status = "running"
            
            # Create containers for real-time updates
            status_container = st.empty()
            progress_container = st.empty()
            
            # Step 1: AI Planner Analysis
            with status_container.container():
                st.markdown('<div class="automation-status">🤖 AI Planner is analyzing your user story...</div>', unsafe_allow_html=True)
            
            st.session_state.workflow_step = 0
            time.sleep(2)  # Simulate analysis time
            
            # Extract URL and plan
            urls = re.findall(r'https?://[^\s]+', user_story)
            target_url = urls[0] if urls else "https://example.com"
            st.session_state.target_url = target_url
            
            planning_message = f"""✅ **Analysis Complete!**

📋 **Automation Plan:**
• Target URL: {target_url}
• User Story: {user_story}

🔄 **Execution Sequence:**
1. Network traffic capture and analysis
2. Test steps generation with correlation
3. JMX script creation for JMeter
4. Validation and quality assurance

🚀 **Starting automated execution...**"""
            
            with status_container.container():
                st.markdown('<div class="automation-status">🚀 Executing automated sequence...</div>', unsafe_allow_html=True)
                st.success(planning_message)

            # Step 2: Network Logging
            st.session_state.workflow_step = 1
            self.display_progress_inline(progress_container)
            
            if not network_logger_module:
                st.error("❌ log.py module not available")
                st.session_state.automation_status = "failed"
                return

            with st.spinner("🌐 Executing network traffic capture..."):
                # Update log.py with user story
                if not self.update_task_in_log_file(user_story):
                    st.error("❌ Failed to update TASK in log.py")
                    st.session_state.automation_status = "failed"
                    return

                # Execute log.py
                result = self.run_script_with_timeout('log.py', timeout=300)
                
                if result["success"]:
                    message = f"""✅ **Network Logging Complete!**
• Target URL: {target_url}
• Network traffic captured successfully
• Correlation data prepared"""
                    st.success(message)
                    st.session_state.results['network_logging'] = result
                else:
                    st.error(f"❌ Network logging failed: {result['stderr']}")
                    st.session_state.automation_status = "failed"
                    return

            # Step 3: Test Steps Generation
            st.session_state.workflow_step = 2
            self.display_progress_inline(progress_container)
            
            if not test_steps_module:
                st.error("❌ TestSteps.py module not available")
                st.session_state.automation_status = "failed"
                return

            with st.spinner("⚙️ Generating test steps with correlation mapping..."):
                # Execute TestSteps.py
                if hasattr(test_steps_module, 'main'):
                    result = test_steps_module.main()
                    result = {"status": "success", "output": str(result)}
                else:
                    result = self.run_script_with_timeout('TestSteps.py', timeout=120)
                
                if result.get("success", True):
                    # Check output files
                    output_files = []
                    expected_files = [
                        'TestSteps_Output/test_steps_structured.json',
                        'TestSteps_Output/test_steps_simple.json',
                        'TestSteps_Output/TestSteps.txt',
                        'TestSteps_Output/correlation_rules.json'
                    ]
                    
                    for file_path in expected_files:
                        if os.path.exists(file_path):
                            output_files.append(file_path)
                    
                    message = f"""✅ **Test Steps Generation Complete!**
• Files created: {len(output_files)}
• Test steps structured and ready
• Correlation rules defined"""
                    st.success(message)
                    st.session_state.results['test_steps'] = result
                    st.session_state.results['output_files'] = output_files
                else:
                    st.error(f"❌ Test steps generation failed: {result.get('stderr', 'Unknown error')}")
                    st.session_state.automation_status = "failed"
                    return

            # Step 4: JMX Generation
            st.session_state.workflow_step = 3
            self.display_progress_inline(progress_container)
            
            if not jmx_generator_module:
                st.error("❌ PTScript.py module not available")
                st.session_state.automation_status = "failed"
                return

            with st.spinner("🎯 Creating JMX scripts for JMeter..."):
                os.makedirs('JMX_SCRIPT_OUTPUT', exist_ok=True)
                
                if hasattr(jmx_generator_module, 'main'):
                    result = jmx_generator_module.main()
                    result = {"status": "success", "output": str(result)}
                    time.sleep(1)
                else:
                    result = self.run_script_with_timeout('PTScript.py', timeout=180)
                
                if result.get("success", True):
                    # Find JMX files
                    jmx_files = []
                    if os.path.exists('JMX_SCRIPT_OUTPUT'):
                        for root, dirs, files in os.walk('JMX_SCRIPT_OUTPUT'):
                            for file in files:
                                if file.endswith('.jmx'):
                                    jmx_files.append(os.path.join(root, file))
                    
                    message = f"""✅ **JMX Generation Complete!**
• JMX files created: {len(jmx_files)}
• Ready for JMeter execution
• Performance test scripts prepared"""
                    st.success(message)
                    st.session_state.results['jmx_generation'] = result
                    st.session_state.results['jmx_files'] = jmx_files
                else:
                    st.error(f"❌ JMX generation failed: {result.get('stderr', 'Unknown error')}")
                    st.session_state.automation_status = "failed"
                    return

            # Step 5: Validation
            st.session_state.workflow_step = 4
            self.display_progress_inline(progress_container)
            
            if not validation_module or not self.validator:
                st.error("❌ validation.py module not available")
                st.session_state.automation_status = "failed"
                return

            with st.spinner("🔍 Validating JMX scripts and performing quality checks..."):
                try:
                    jmx_files = st.session_state.results.get('jmx_files', [])
                    
                    if not jmx_files:
                        st.error("❌ No JMX files found to validate")
                        st.session_state.automation_status = "failed"
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

                    st.success(message)
                    st.session_state.results['validation'] = validation_results
                    st.session_state.automation_status = "completed"

                except Exception as e:
                    st.error(f"❌ Validation failed: {str(e)}")
                    st.session_state.automation_status = "failed"
                    return

            # Final status
            st.session_state.workflow_step = 5
            self.display_progress_inline(progress_container)
            
            with status_container.container():
                st.markdown('<div class="automation-status">🎉 Automation Complete! All modules executed successfully.</div>', unsafe_allow_html=True)
                st.balloons()

        except Exception as e:
            st.error(f"❌ Workflow error: {str(e)}")
            st.session_state.automation_status = "failed"

    def display_progress_inline(self, container):
        """Display progress in the given container"""
        with container.container():
            steps = self.get_steps()
            
            for i, step in enumerate(steps):
                if i < st.session_state.workflow_step:
                    st.markdown(f'<div class="progress-step step-completed">✅ {step["name"]}</div>', unsafe_allow_html=True)
                elif i == st.session_state.workflow_step:
                    st.markdown(f'<div class="progress-step step-current">🔄 {step["name"]}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="progress-step step-pending">⏳ {step["name"]}</div>', unsafe_allow_html=True)
            
            progress_percent = (st.session_state.workflow_step / len(steps)) * 100
            st.progress(progress_percent / 100)

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'workflow' not in st.session_state:
    st.session_state.workflow = AutomatedWorkflow()
if 'workflow_step' not in st.session_state:
    st.session_state.workflow_step = 0
if 'results' not in st.session_state:
    st.session_state.results = {}
if 'automation_status' not in st.session_state:
    st.session_state.automation_status = "ready"

def display_progress():
    """Display workflow progress in sidebar"""
    steps = [
        "🤖 AI Planner Analysis",
        "🌐 Network Logging",
        "⚙️ Test Steps Generation ", 
        "🎯 JMX Script Creation",
        "🔍 JMX Validation",
    ]
    
    for i, step in enumerate(steps):
        if i < st.session_state.workflow_step:
            st.markdown(f'<div class="progress-step step-completed">✅ {step}</div>', unsafe_allow_html=True)
        elif i == st.session_state.workflow_step:
            st.markdown(f'<div class="progress-step step-current">🔄 {step}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="progress-step step-pending">⏳ {step}</div>', unsafe_allow_html=True)
    
    progress_percent = (st.session_state.workflow_step / len(steps)) * 100
    st.progress(progress_percent / 100)

def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🚀 Automated Performance Testing Assistant</h1>
        <p><strong>AI-Powered Automation:</strong> AI Planner → Network Analysis → Test Steps → JMX Creation → Validation</p>
        <p>Complete automation from user story to validated JMeter script</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Show module status
    if MODULES_AVAILABLE:
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.markdown("""
            <div class="module-info">
                <h4>🤖 AI Planner</h4>
                <p>Story analysis<br>Automation planning</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="module-info">
                <h4>🌐 Network Agent</h4>
                <p>Traffic capture<br>Correlation detection</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div class="module-info">
                <h4>⚙️ TestSteps Agent</h4>
                <p>Test generation<br>Correlation mapping</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown("""
            <div class="module-info">
                <h4>🎯 JMX Agent</h4>
                <p>Script creation<br>JMeter integration</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col5:
            st.markdown("""
            <div class="module-info">
                <h4>🔍 Validation Agent</h4>
                <p>Quality assurance<br>Script validation</p>
            </div>
            """, unsafe_allow_html=True)
    
    # Main layout
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("🤖 Automated Performance Testing")
        
        # Show automation status
        if st.session_state.automation_status == "running":
            st.markdown('<div class="automation-status">⚡ Automation in Progress - Please wait...</div>', unsafe_allow_html=True)
        elif st.session_state.automation_status == "completed":
            st.markdown('<div class="automation-status">🎉 Automation Complete - All modules executed successfully!</div>', unsafe_allow_html=True)
        elif st.session_state.automation_status == "failed":
            st.markdown('<div class="automation-status">❌ Automation Failed - Check errors above</div>', unsafe_allow_html=True)
        
        # Chat messages
        chat_container = st.container()
        with chat_container:
            for message in st.session_state.messages:
                if message["role"] == "user":
                    st.markdown(f'<div class="chat-message user-message"><strong>You:</strong><br>{message["content"]}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="chat-message assistant-message"><strong>Assistant:</strong><br>{message["content"]}</div>', unsafe_allow_html=True)
        
        # Input section
        st.subheader("🚀 Start Automated Workflow")
        
        # Disable input during automation
        input_disabled = st.session_state.automation_status == "running"
        
        user_input = st.text_area(
            "Enter your user story with URL:",
            placeholder="e.g., 'Test login functionality for https://example.com'",
            disabled=input_disabled,
            height=100
        )
        
        col_btn1, col_btn2 = st.columns([1, 1])
        
        with col_btn1:
            if st.button("🚀 Start Automation", disabled=input_disabled or not user_input.strip()):
                if user_input.strip():
                    # Check for URL in user story
                    urls = re.findall(r'https?://[^\s]+', user_input)
                    if not urls:
                        st.error("❓ Please provide a user story with a URL (e.g., 'Test login for https://example.com')")
                    else:
                        # Add user message
                        st.session_state.messages.append({"role": "user", "content": user_input})
                        
                        # Start automated workflow
                        response = f"""🚀 **Automated Workflow Started!**

📝 **User Story**: {user_input}

🤖 **AI is now executing the complete automation sequence:**

1. 🤖 AI Planner Analysis
2. 🌐 Network Logging  
3. ⚙️ Test Steps Generation
4. 🎯 JMX Script Creation
5. 🔍 JMX Validation

⏱️ **Estimated time**: 5-10 minutes"""
                        
                        st.session_state.messages.append({"role": "assistant", "content": response})
                        
                        # Execute workflow
                        st.session_state.workflow.execute_automated_workflow(user_input)
                        st.rerun()
        
        with col_btn2:
            if st.button("🔄 New Test"):
                st.session_state.workflow.reset_progress()
                st.session_state.messages = []
                st.rerun()
    
    with col2:
        st.header("📋 Automation Progress")
        display_progress()
        
        # Show current target URL if available
        if st.session_state.get('target_url'):
            st.info(f"🎯 **Target URL**: {st.session_state.target_url}")
        
        st.header("🔄 Actions")
        
        col_action1, col_action2 = st.columns(2)
        with col_action1:
            if st.button("🔄 Reset"):
                st.session_state.workflow.reset_progress()
                st.session_state.messages = []
                st.rerun()
        
        with col_action2:
            if st.button("📊 Results") and st.session_state.results:
                with st.expander("Results Details", expanded=True):
                    st.json(st.session_state.results)
        
        # Manual execution section
        with st.expander("🛠️ Manual Module Execution"):
            st.markdown("**Execute modules individually:**")
            
            if st.button("🌐 Run Network Agent", key="manual_log"):
                try:
                    result = subprocess.run([sys.executable, 'log.py'], 
                                          capture_output=True, text=True, timeout=180)
                    if result.returncode == 0:
                        st.success("✅ log.py executed successfully!")
                    else:
                        st.error(f"❌ log.py failed: {result.stderr}")
                except Exception as e:
                    st.error(f"Error running log.py: {e}")
            
            if st.button("⚙️ Run TestSteps Agent", key="manual_teststeps"):
                try:
                    if hasattr(test_steps_module, 'main'):
                        result = test_steps_module.main()
                        st.success(f"TestSteps.py executed: {result}")
                    else:
                        st.info("TestSteps.py loaded but no main() function found")
                except Exception as e:
                    st.error(f"Error running TestSteps.py: {e}")
            
            if st.button("🎯 Run JMX Script Agent", key="manual_jmx"):
                try:
                    if hasattr(jmx_generator_module, 'main'):
                        result = jmx_generator_module.main()
                        st.success(f"PTScript.py executed: {result}")
                    else:
                        st.info("PTScript.py loaded but no main() function found")
                except Exception as e:
                    st.error(f"Error running PTScript.py: {e}")
            
            if st.button("🔍 Run Validation Agent", key="manual_validation"):
                try:
                    workflow = st.session_state.workflow
                    # Simple validation without full workflow
                    jmx_files = []
                    if os.path.exists('JMX_SCRIPT_OUTPUT'):
                        for root, dirs, files in os.walk('JMX_SCRIPT_OUTPUT'):
                            for file in files:
                                if file.endswith('.jmx'):
                                    jmx_files.append(os.path.join(root, file))
                    
                    if jmx_files and workflow.validator:
                        for jmx_file in jmx_files:
                            validation_result = workflow.validator.validate_jmx_file(jmx_file)
                            status = validation_result.get('overall_status', 'unknown')
                            if status == 'pass':
                                st.success(f"✅ {os.path.basename(jmx_file)}: PASSED")
                            elif status == 'warning':
                                st.warning(f"⚠️ {os.path.basename(jmx_file)}: WARNINGS")
                            else:
                                st.error(f"❌ {os.path.basename(jmx_file)}: FAILED")
                    else:
                        st.info("No JMX files found or validator not available")
                except Exception as e:
                    st.error(f"Error running validation: {e}")

if __name__ == "__main__":
    main()