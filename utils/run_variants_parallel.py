#!/usr/bin/env python3
"""
Script to run multiple variant spiders in parallel from a URL list.
- Reads URLs from variants_urls.txt (comma or newline separated)
- Runs 10 variant spiders in parallel
- Cleans the output CSV by removing duplicate headers
- Outputs to Output/[ModelName]/Variants.csv
"""

import subprocess
import sys
import time
import os
import csv
from multiprocessing import Process, Queue
from datetime import datetime
import re


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


def run_spider_with_url(spider_name, url, url_index, total_urls, project_root, queue):
    """
    Run a single spider with a specific URL.

    Args:
        spider_name: Name of the spider to run
        url: The URL to scrape
        url_index: Index of the current URL
        total_urls: Total number of URLs
        project_root: Root directory of the scrapy project
        queue: Queue to store the result
    """
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"[{timestamp}] [{url_index}/{total_urls}] Starting spider for: {url}")
    start_time = time.time()

    try:
        # Run the spider using scrapy crawl command with custom settings
        # Pipeline will handle output to Output/[ModelName]/Variants.csv
        result = subprocess.run(
            [
                'scrapy', 'crawl', spider_name,
                '-a', f'url={url}',
                '-s', 'LOG_LEVEL=INFO',
                '-s', 'CONCURRENT_REQUESTS=1',
                '-s', 'DOWNLOAD_DELAY=3'
            ],
            capture_output=True,
            text=True,
            cwd=project_root
        )

        elapsed_time = time.time() - start_time

        if result.returncode == 0:
            timestamp = datetime.now().strftime('%H:%M:%S')
            print(f"[{timestamp}] [{url_index}/{total_urls}] ✓ Completed in {elapsed_time:.2f}s")
            queue.put((url_index, 'success', elapsed_time, url))
        else:
            timestamp = datetime.now().strftime('%H:%M:%S')
            print(f"[{timestamp}] [{url_index}/{total_urls}] ✗ Failed with exit code {result.returncode}")
            if result.stderr:
                print(f"[ERROR] {result.stderr[:200]}")
            queue.put((url_index, 'failed', elapsed_time, url))

    except Exception as e:
        elapsed_time = time.time() - start_time
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] [{url_index}/{total_urls}] ✗ Error: {e}")
        queue.put((url_index, 'error', elapsed_time, url))




def run_spiders_in_batches(spider_name, urls, batch_size, project_root):
    """
    Run spiders in batches with parallel execution.

    Args:
        spider_name: Name of the spider to run
        urls: List of URLs to process
        batch_size: Number of spiders to run in parallel
        project_root: Root directory of the scrapy project

    Returns:
        Tuple of (success_count, failed_count)
    """
    total_urls = len(urls)
    result_queue = Queue()
    all_results = []

    print("=" * 80)
    print("RUNNING VARIANT SPIDERS IN PARALLEL")
    print("=" * 80)
    print(f"Total URLs to process: {total_urls}")
    print(f"Parallel workers: {batch_size}")
    print(f"Output will be written to: Output/[ModelName]/Variants.csv")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()

    overall_start_time = time.time()

    # Process URLs in batches
    for batch_start in range(0, total_urls, batch_size):
        batch_end = min(batch_start + batch_size, total_urls)
        batch_urls = urls[batch_start:batch_end]

        print(f"\n[BATCH] Processing URLs {batch_start + 1} to {batch_end} of {total_urls}")
        print("-" * 80)

        processes = []

        for i, url in enumerate(batch_urls):
            url_index = batch_start + i + 1
            process = Process(
                target=run_spider_with_url,
                args=(spider_name, url, url_index, total_urls, project_root, result_queue)
            )
            process.start()
            processes.append(process)
            time.sleep(0.5)  # Small delay to avoid conflicts

        # Wait for all processes in this batch to complete
        for process in processes:
            process.join()

        print(f"[BATCH] Completed URLs {batch_start + 1} to {batch_end}")

    # Collect all results
    while not result_queue.empty():
        result = result_queue.get()
        all_results.append(result)

    total_time = time.time() - overall_start_time

    # Sort results by URL index
    all_results.sort(key=lambda x: x[0])

    # Display summary
    print("\n" + "=" * 80)
    print("EXECUTION SUMMARY")
    print("=" * 80)

    success_count = 0
    failed_count = 0

    for url_index, status, elapsed, url in all_results:
        status_icon = "✓" if status == "success" else "✗"
        status_text = status.upper()
        short_url = url[:60] + "..." if len(url) > 60 else url
        print(f"{status_icon} [{url_index:3d}] {status_text:10s} ({elapsed:6.2f}s) - {short_url}")

        if status == "success":
            success_count += 1
        else:
            failed_count += 1

    print("=" * 80)
    print(f"Total execution time: {total_time:.2f}s")
    print(f"Successful: {success_count}/{total_urls}")
    print(f"Failed: {failed_count}/{total_urls}")
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    return success_count, failed_count


def main():
    """Main function to orchestrate the entire process."""

    # Get the script's directory and project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)  # Parent directory (scrapy project root)

    # Configuration
    INPUT_FILE = os.path.join(script_dir, 'variants_urls.txt')
    SPIDER_NAME = 'variants'
    BATCH_SIZE = 8  # Number of parallel spiders

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

    # Run spiders in batches (pipeline handles output)
    success_count, failed_count = run_spiders_in_batches(
        SPIDER_NAME, urls, BATCH_SIZE, project_root
    )

    print(f"\n[INFO] All variants have been written to Output/[ModelName]/Variants.csv by the pipeline")

    # Exit with appropriate code
    if failed_count > 0:
        print(f"\n[WARNING] {failed_count} spider(s) failed. Check the logs above for details.")
        sys.exit(1)
    else:
        print(f"\n[SUCCESS] All spiders completed successfully!")
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
