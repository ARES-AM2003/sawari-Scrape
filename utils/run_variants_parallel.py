#!/usr/bin/env python3
"""
Script to run variant spider with multiple browsers, each with multiple tabs.
- Reads URLs from variants_urls.txt (comma or newline separated)
- Spawns multiple browser instances, each with multiple tabs for parallel processing
- Balances memory usage with parallelism
- Outputs to Output/[ModelName]/Variants.csv
"""

import subprocess
import sys
import time
import os
import csv
from multiprocessing import Process
from datetime import datetime
import re
import math


def read_urls_from_file(filename):
    """
    Read URLs from a text file that can be comma-separated or newline-separated.

    Args:
        filename: Path to the file containing URLs

    Returns:
        List of cleaned URLs
    """
    if not os.path.exists(filename):
        print(f"[ERROR] File '{filename}' not found!")
        return []

    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split by both commas and newlines
    urls = re.split(r'[,\n]', content)

    # Clean up URLs (strip whitespace and remove empty strings)
    urls = [url.strip() for url in urls if url.strip()]

    return urls


def extract_model_name_from_csv(csv_file):
    """
    Extract model name from the first row of CSV data.

    Args:
        csv_file: Path to CSV file

    Returns:
        Model name string or None
    """
    try:
        if not os.path.exists(csv_file):
            return None

        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            first_row = next(reader, None)
            if first_row and 'modelName' in first_row:
                return first_row['modelName']
    except Exception as e:
        print(f"[WARNING] Could not extract model name from {csv_file}: {e}")

    return None


def create_urls_file(urls, temp_file_path):
    """
    Create a temporary file with URLs for the spider to process.
    
    Args:
        urls: List of URLs
        temp_file_path: Path to write the temporary file
    """
    with open(temp_file_path, 'w', encoding='utf-8') as f:
        for url in urls:
            f.write(f"{url}\n")




def run_spider_process(spider_name, urls, tabs_per_browser, project_root, browser_id, total_browsers):
    """
    Run a single spider process (one browser with multiple tabs) with a batch of URLs.
    
    Args:
        spider_name: Name of the spider to run
        urls: List of URLs for this browser to process
        tabs_per_browser: Number of tabs in this browser
        project_root: Root directory of the scrapy project
        browser_id: ID of this browser instance
        total_browsers: Total number of browsers being used
    
    Returns:
        Success status
    """
    total_urls = len(urls)
    
    print(f"\n[Browser {browser_id}/{total_browsers}] Starting with {total_urls} URLs and {tabs_per_browser} tabs")
    
    # Create temporary file with URLs for this browser
    temp_urls_file = os.path.join(project_root, 'utils', f'temp_browser_{browser_id}_urls.txt')
    create_urls_file(urls, temp_urls_file)
    
    start_time = time.time()
    
    try:
        # Run spider process with this batch of URLs
        result = subprocess.run(
            [
                'scrapy', 'crawl', spider_name,
                '-a', f'urls_file={temp_urls_file}',
                '-s', 'LOG_LEVEL=INFO',
                '-s', f'CONCURRENT_REQUESTS_PER_DOMAIN={tabs_per_browser}',
                '-s', f'SELENIUM_MAX_TABS={tabs_per_browser}',
                '-s', 'DOWNLOAD_DELAY=1'
            ],
            capture_output=True,
            text=True,
            cwd=project_root
        )
        
        elapsed_time = time.time() - start_time
        
        # Cleanup temp file
        if os.path.exists(temp_urls_file):
            os.remove(temp_urls_file)
        
        if result.returncode == 0:
            print(f"[Browser {browser_id}/{total_browsers}] ✅ Completed in {elapsed_time:.2f}s")
            return True
        else:
            print(f"[Browser {browser_id}/{total_browsers}] ❌ Failed with exit code {result.returncode}")
            if result.stderr:
                print(f"[Browser {browser_id}] Error: {result.stderr[:200]}")
            return False
            
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"[Browser {browser_id}/{total_browsers}] ❌ Error: {e}")
        
        # Cleanup temp file on error
        if os.path.exists(temp_urls_file):
            os.remove(temp_urls_file)
        
        return False


def run_multi_browser_spider(spider_name, urls, num_browsers, tabs_per_browser, project_root):
    """
    Run multiple browser instances, each with multiple tabs, for parallel processing.
    
    Args:
        spider_name: Name of the spider to run
        urls: List of all URLs to process
        num_browsers: Number of browser instances to spawn
        tabs_per_browser: Number of tabs per browser
        project_root: Root directory of the scrapy project
    
    Returns:
        Tuple of (success_count, failed_count, elapsed_time)
    """
    total_urls = len(urls)
    total_tabs = num_browsers * tabs_per_browser
    total_memory = num_browsers * (400 + tabs_per_browser * 25)  # Rough estimate
    
    print("=" * 80)
    print("🚀 RUNNING MULTI-BROWSER VARIANT SPIDER")
    print("=" * 80)
    print(f"Total URLs to process: {total_urls}")
    print(f"Number of browsers: {num_browsers}")
    print(f"Tabs per browser: {tabs_per_browser}")
    print(f"Total concurrent tabs: {total_tabs}")
    print(f"Estimated memory usage: ~{total_memory}MB")
    print(f"Output: Output/[ModelName]/Variants.csv")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()
    
    # Split URLs evenly across browsers
    urls_per_browser = math.ceil(total_urls / num_browsers)
    url_batches = []
    
    for i in range(num_browsers):
        start_idx = i * urls_per_browser
        end_idx = min((i + 1) * urls_per_browser, total_urls)
        batch = urls[start_idx:end_idx]
        if batch:  # Only add non-empty batches
            url_batches.append(batch)
    
    actual_browsers = len(url_batches)
    print(f"[INFO] Split {total_urls} URLs into {actual_browsers} batches")
    for i, batch in enumerate(url_batches, 1):
        print(f"  Browser {i}: {len(batch)} URLs")
    print()
    
    overall_start_time = time.time()
    
    # Start all browser processes
    processes = []
    for i, batch in enumerate(url_batches, 1):
        process = Process(
            target=run_spider_process,
            args=(spider_name, batch, tabs_per_browser, project_root, i, actual_browsers)
        )
        process.start()
        processes.append(process)
        time.sleep(0.5)  # Small delay between browser launches
    
    # Wait for all processes to complete
    print(f"\n[INFO] All {actual_browsers} browsers started. Waiting for completion...")
    for process in processes:
        process.join()
    
    total_time = time.time() - overall_start_time
    
    # Display summary
    print("\n" + "=" * 80)
    print("EXECUTION SUMMARY")
    print("=" * 80)
    print(f"Total browsers used: {actual_browsers}")
    print(f"Tabs per browser: {tabs_per_browser}")
    print(f"Total URLs processed: {total_urls}")
    print(f"Total execution time: {total_time:.2f}s")
    print(f"Average time per URL: {total_time/total_urls:.2f}s")
    print(f"Theoretical speedup: ~{total_tabs}x")
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    return total_time


def main():
    """Main function to orchestrate the entire process."""

    # Get the script's directory and project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)  # Parent directory (scrapy project root)

    # Configuration
    INPUT_FILE = os.path.join(script_dir, 'variants_urls.txt')
    SPIDER_NAME = 'variants'
    NUM_BROWSERS = 3  # Number of browser instances to spawn
    TABS_PER_BROWSER = 4  # Number of tabs per browser

    # Check if scrapy.cfg exists in project root
    scrapy_cfg = os.path.join(project_root, 'scrapy.cfg')
    if not os.path.exists(scrapy_cfg):
        print(f"[ERROR] scrapy.cfg not found at {scrapy_cfg}")
        print("[ERROR] Please ensure the script is in the utils folder of your scrapy project")
        sys.exit(1)

    # Read URLs from file
    print(f"[INFO] Reading URLs from '{INPUT_FILE}'...")
    urls = read_urls_from_file(INPUT_FILE)

    if not urls:
        print("[ERROR] No URLs found in the input file!")
        print(f"[INFO] Please create 'variants_urls.txt' in the utils folder with URLs (comma or newline separated)")
        sys.exit(1)

    print(f"[SUCCESS] Found {len(urls)} URL(s) to process")
    print()

    # Calculate statistics
    total_tabs = NUM_BROWSERS * TABS_PER_BROWSER
    estimated_memory = NUM_BROWSERS * (400 + TABS_PER_BROWSER * 25)
    
    print(f"💡 Configuration:")
    print(f"   • {NUM_BROWSERS} browsers × {TABS_PER_BROWSER} tabs = {total_tabs} concurrent tabs")
    print(f"   • Estimated memory: ~{estimated_memory}MB (~{estimated_memory/1024:.1f}GB)")
    print(f"   • Theoretical speedup: {total_tabs}x vs single tab")
    print()
    
    # Run multi-browser spider
    elapsed_time = run_multi_browser_spider(
        SPIDER_NAME, urls, NUM_BROWSERS, TABS_PER_BROWSER, project_root
    )

    print(f"\n[INFO] All variants have been written to Output/[ModelName]/Variants.csv by the pipeline")
    print(f"\n✅ [SUCCESS] Completed in {elapsed_time:.2f}s!")
    print(f"💡 Used {NUM_BROWSERS} browsers with {TABS_PER_BROWSER} tabs each")
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Script terminated by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
