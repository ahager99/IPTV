import logging
import time
import subprocess
import sys
from datetime import datetime
from Library import Settings

logging.basicConfig(level=Settings.LOG_LEVEL, format=Settings.LOG_FORMAT)


def is_important_progress_line(line):
    if not line:
        return False

    important_markers = [
        "Processing [",
        "URL[",
        "INSERTING:",
        "summary:",
        "GLOBAL summary:",
    ]
    return any(marker in line for marker in important_markers)


def run_script(script_name):
    """
    Run a Python script and return its exit code.
    """
    logging.info(f"Starting: {script_name}")
    
    start_time = time.time()
    
    try:
        # Run the script and capture output in real-time
        process = subprocess.Popen(
            [sys.executable, script_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        output_lines = []
        for line in process.stdout:
            clean_line = line.rstrip("\n")
            output_lines.append(clean_line)
            if not Settings.VERBOSE_SUBPROCESS_OUTPUT and is_important_progress_line(clean_line):
                logging.info(clean_line)
            if Settings.VERBOSE_SUBPROCESS_OUTPUT:
                print(line, end='')
        
        process.wait()
        exit_code = process.returncode
        
        end_time = time.time()
        elapsed = end_time - start_time
        hours, remainder = divmod(elapsed, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if exit_code == 0:
            logging.info(f"✓ Completed: {script_name}")
        else:
            logging.error(f"✗ Failed: {script_name} (exit code: {exit_code})")
            if output_lines and not Settings.VERBOSE_SUBPROCESS_OUTPUT:
                logging.warning(f"Last output lines from {script_name}:")
                for line in output_lines[-20:]:
                    logging.warning(line)
        
        logging.info(f"Time taken: {int(hours)}h {int(minutes)}m {int(seconds)}s")
        return exit_code
        
    except Exception as e:
        logging.error(f"Error running {script_name}: {str(e)}")
        return 1


def main():
    overall_start = time.time()

    logging.info(f"{'#'*60}")
    logging.info(f"IPTV PARSE AND CHECK WORKFLOW")
    logging.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info(f"{'#'*60}")
    
    # Define the scripts to run in order
    parse_scripts = [
        "PARSE_LINKS_alaaeldinee.py",
        "PARSE_LINKS_iptvlinkseuro.py"
    ]
    
    check_script = "CHECK_macs.py"
    total_steps = len(parse_scripts) + 1
    completed_steps = 0
    
    # Step 1: Run parse scripts
    logging.info("PHASE 1: Parsing IPTV links from sources")
    logging.info("-" * 60)
    
    parse_failed = False
    for index, script in enumerate(parse_scripts, start=1):
        progress_percent = (completed_steps / total_steps) * 100
        logging.info(f"Progress: step {completed_steps + 1}/{total_steps} ({progress_percent:.0f}%) - parsing source {index}/{len(parse_scripts)}")
        exit_code = run_script(script)
        completed_steps += 1
        if exit_code != 0:
            logging.error(f"Parse script {script} failed. Continuing with next script...")
            parse_failed = True
    
    if parse_failed:
        logging.warning("Some parse scripts failed, but continuing to check phase...")

    progress_percent = (completed_steps / total_steps) * 100
    logging.info(f"Progress: completed parse phase ({progress_percent:.0f}%)")
    
    # Step 2: Run check script
    logging.info("PHASE 2: Checking MACs")
    logging.info("-" * 60)
    progress_percent = (completed_steps / total_steps) * 100
    logging.info(f"Progress: step {completed_steps + 1}/{total_steps} ({progress_percent:.0f}%) - running MAC checks")
    
    check_exit_code = run_script(check_script)
    completed_steps += 1
    
    # Summary
    overall_end = time.time()
    total_elapsed = overall_end - overall_start
    hours, remainder = divmod(total_elapsed, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    logging.info(f"{'#'*60}")
    logging.info(f"WORKFLOW COMPLETED")
    logging.info(f"Started at:  {datetime.fromtimestamp(overall_start).strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info(f"Finished at: {datetime.fromtimestamp(overall_end).strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info(f"Total time:  {int(hours)}h {int(minutes)}m {int(seconds)}s")
    logging.info(f"Progress: {completed_steps}/{total_steps} steps completed (100%)")
    
    if check_exit_code == 0 and not parse_failed:
        logging.info("Status: SUCCESS ✓")
    else:
        logging.warning("Status: COMPLETED WITH ERRORS ✗")
    
    logging.info(f"{'#'*60}")


if __name__ == "__main__":
    main()
