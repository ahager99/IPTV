import logging
import time
import subprocess
import sys
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def run_script(script_name):
    """
    Run a Python script and return its exit code.
    """
    logging.info(f"{'='*60}")
    logging.info(f"Starting: {script_name}")
    logging.info(f"{'='*60}")
    
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
        
        # Print output in real-time
        for line in process.stdout:
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
        
        logging.info(f"Time taken: {int(hours)}h {int(minutes)}m {int(seconds)}s")
        logging.info("")
        
        return exit_code
        
    except Exception as e:
        logging.error(f"Error running {script_name}: {str(e)}")
        return 1


def main():
    overall_start = time.time()
    
    logging.info("")
    logging.info(f"{'#'*60}")
    logging.info(f"IPTV PARSE AND CHECK WORKFLOW")
    logging.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info(f"{'#'*60}")
    logging.info("")
    
    # Define the scripts to run in order
    parse_scripts = [
        "PARSE_LINKS_alaaeldinee.py",
        "PARSE_LINKS_iptvlinkseuro.py"
    ]
    
    check_script = "CHECK_macs.py"
    
    # Step 1: Run parse scripts
    logging.info("PHASE 1: Parsing IPTV links from sources")
    logging.info("-" * 60)
    
    parse_failed = False
    for script in parse_scripts:
        exit_code = run_script(script)
        if exit_code != 0:
            logging.error(f"Parse script {script} failed. Continuing with next script...")
            parse_failed = True
    
    if parse_failed:
        logging.warning("Some parse scripts failed, but continuing to check phase...")
    
    logging.info("")
    
    # Step 2: Run check script
    logging.info("PHASE 2: Checking MACs")
    logging.info("-" * 60)
    
    check_exit_code = run_script(check_script)
    
    # Summary
    overall_end = time.time()
    total_elapsed = overall_end - overall_start
    hours, remainder = divmod(total_elapsed, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    logging.info("")
    logging.info(f"{'#'*60}")
    logging.info(f"WORKFLOW COMPLETED")
    logging.info(f"Started at:  {datetime.fromtimestamp(overall_start).strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info(f"Finished at: {datetime.fromtimestamp(overall_end).strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info(f"Total time:  {int(hours)}h {int(minutes)}m {int(seconds)}s")
    
    if check_exit_code == 0 and not parse_failed:
        logging.info("Status: SUCCESS ✓")
    else:
        logging.warning("Status: COMPLETED WITH ERRORS ✗")
    
    logging.info(f"{'#'*60}")
    logging.info("")


if __name__ == "__main__":
    main()
