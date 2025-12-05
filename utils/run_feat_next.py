#!/usr/bin/env python3
"""
Script to run multiple feature-specification spiders in parallel from a URL list.
- Reads URLs from feature_spec_urls.txt (comma or newline separated)
- Runs 6 feature-specification spiders in parallel
- Outputs to Output/[ModelName]/Features.csv and Output/[ModelName]/Specifications.csv
"""

import subprocess
import sys
import time
import os
import csv
from multiprocessing import Process, Queue
from datetime import datetime
import re
from subprocess import TimeoutExpired


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


def remove_duplicate_headers(csv_file):
    """
    Remove duplicate header rows from a CSV file.

    Args:
        csv_file: Path to CSV file to clean
    """
    if not os.path.exists(csv_file):
        print(f"  ⚠️  File not found: {csv_file}")
        return

    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        if len(lines) <= 1:
            print(f"  ℹ️  No duplicate headers to remove in {os.path.basename(csv_file)}")
            return

        # Get the header (first line)
        header = lines[0].strip()

        # Filter out duplicate header lines (keep only data rows after first header)
        cleaned_lines = [lines[0]]  # Keep first header
        duplicates_found = 0

        for line in lines[1:]:
            # Check if this line is a duplicate header
            if line.strip() == header:
                duplicates_found += 1
            else:
                cleaned_lines.append(line)

        # Write back only if duplicates were found
        if duplicates_found > 0:
            with open(csv_file, 'w', encoding='utf-8') as f:
                f.writelines(cleaned_lines)
            print(f"  ✓ Removed {duplicates_found} duplicate header(s) from {os.path.basename(csv_file)}")
        else:
            print(f"  ✓ No duplicate headers found in {os.path.basename(csv_file)}")

    except Exception as e:
        print(f"  ✗ Error cleaning {os.path.basename(csv_file)}: {e}")


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


def run_spider_with_url(spider_name, url, url_index, total_urls, project_root, queue, timeout=150, retry_attempt=0):
    """
    Run a single spider with a specific URL.

    Args:
        spider_name: Name of the spider to run
        url: The URL to scrape
        url_index: Index of the current URL
        total_urls: Total number of URLs
        project_root: Root directory of the scrapy project
        queue: Queue to store the result
        timeout: Maximum time in seconds for the spider to run (default: 150)
        retry_attempt: Current retry attempt number (0 for first attempt)
    """
    retry_prefix = f" [RETRY {retry_attempt}]" if retry_attempt > 0 else ""
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"[{timestamp}] [{url_index}/{total_urls}]{retry_prefix} Starting spider for: {url}")
    start_time = time.time()

    try:
        # Run the spider using scrapy crawl command with custom settings
        # Pipeline will handle output to Output/[ModelName]/Features.csv and Specifications.csv
        result = subprocess.run(
            [
                'scrapy', 'crawl', spider_name,
                '-a', f'start_url={url}',
                '-s', 'LOG_LEVEL=INFO',
                '-s', 'CONCURRENT_REQUESTS=1',
                '-s', 'DOWNLOAD_DELAY=3'
            ],
            capture_output=True,
            text=True,
            cwd=project_root,
            timeout=timeout  # Add timeout parameter
        )

        elapsed_time = time.time() - start_time

        # Check if execution exceeded timeout even if it completed
        if elapsed_time > timeout:
            timestamp = datetime.now().strftime('%H:%M:%S')
            print(f"[{timestamp}] [{url_index}/{total_urls}]{retry_prefix} ✗ Exceeded timeout ({elapsed_time:.2f}s > {timeout}s)")
            queue.put((url_index, 'timeout', elapsed_time, url))
        elif result.returncode == 0:
            timestamp = datetime.now().strftime('%H:%M:%S')
            print(f"[{timestamp}] [{url_index}/{total_urls}]{retry_prefix} ✓ Completed in {elapsed_time:.2f}s")
            queue.put((url_index, 'success', elapsed_time, url))
        else:
            timestamp = datetime.now().strftime('%H:%M:%S')
            print(f"[{timestamp}] [{url_index}/{total_urls}]{retry_prefix} ✗ Failed with exit code {result.returncode}")
            if result.stderr:
                print(f"[ERROR] {result.stderr[:200]}")
            queue.put((url_index, 'failed', elapsed_time, url))

    except TimeoutExpired:
        elapsed_time = time.time() - start_time
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] [{url_index}/{total_urls}]{retry_prefix} ✗ Timeout: Process killed after {timeout}s")
        queue.put((url_index, 'timeout', elapsed_time, url))
    except Exception as e:
        elapsed_time = time.time() - start_time
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] [{url_index}/{total_urls}]{retry_prefix} ✗ Error: {e}")
        queue.put((url_index, 'error', elapsed_time, url))


def run_spiders_in_batches(spider_name, urls, batch_size, project_root, timeout=150, max_retries=2):
    """
    Run spiders in batches with parallel execution and retry mechanism.

    Args:
        spider_name: Name of the spider to run
        urls: List of URLs to process
        batch_size: Number of spiders to run in parallel
        project_root: Root directory of the scrapy project
        timeout: Maximum time in seconds for each spider (default: 150)
        max_retries: Maximum number of retry attempts for failed URLs (default: 2)

    Returns:
        Tuple of (success_count, failed_count)
    """
    total_urls = len(urls)
    result_queue = Queue()
    all_results = []

    print("=" * 80)
    print("RUNNING FEATURE-SPECIFICATION SPIDERS IN PARALLEL")
    print("=" * 80)
    print(f"Total URLs to process: {total_urls}")
    print(f"Parallel workers: {batch_size}")
    print(f"Timeout per spider: {timeout}s")
    print(f"Max retries: {max_retries}")
    print(f"Output will be written to:")
    print(f"  - Output/[ModelName]/Features.csv")
    print(f"  - Output/[ModelName]/Specifications.csv")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()

    overall_start_time = time.time()

    # Create a mapping of URL index to URL for retry purposes
    url_map = {i + 1: url for i, url in enumerate(urls)}

    # Track retry counts for each URL
    retry_counts = {i + 1: 0 for i in range(total_urls)}

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
                args=(spider_name, url, url_index, total_urls, project_root, result_queue, timeout, retry_counts[url_index])
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

    # Process retries for failed URLs
    for retry_attempt in range(1, max_retries + 1):
        # Find all failed/timeout/error URLs from previous attempt
        failed_results = [r for r in all_results if r[1] in ['failed', 'timeout', 'error']]

        if not failed_results:
            break  # No failures to retry

        print(f"\n{'=' * 80}")
        print(f"RETRY ATTEMPT {retry_attempt} - Found {len(failed_results)} failed URL(s)")
        print(f"{'=' * 80}\n")

        # Remove failed results from all_results (we'll add new attempts)
        all_results = [r for r in all_results if r[1] == 'success']

        # Process failed URLs in batches
        failed_urls = [(r[0], r[3]) for r in failed_results]  # (url_index, url)

        for batch_start in range(0, len(failed_urls), batch_size):
            batch_end = min(batch_start + batch_size, len(failed_urls))
            batch_items = failed_urls[batch_start:batch_end]

            print(f"\n[RETRY BATCH] Processing {batch_start + 1} to {batch_end} of {len(failed_urls)} failed URLs")
            print("-" * 80)

            processes = []

            for url_index, url in batch_items:
                retry_counts[url_index] = retry_attempt
                process = Process(
                    target=run_spider_with_url,
                    args=(spider_name, url, url_index, total_urls, project_root, result_queue, timeout, retry_attempt)
                )
                process.start()
                processes.append(process)
                time.sleep(0.5)

            # Wait for all retry processes to complete
            for process in processes:
                process.join()

            print(f"[RETRY BATCH] Completed {batch_start + 1} to {batch_end}")

        # Collect retry results
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
    timeout_count = 0
    error_count = 0

    for url_index, status, elapsed, url in all_results:
        status_icon = "✓" if status == "success" else "✗"
        status_text = status.upper()
        short_url = url[:60] + "..." if len(url) > 60 else url
        retry_info = f" (after {retry_counts[url_index]} retries)" if retry_counts[url_index] > 0 and status == "success" else ""
        print(f"{status_icon} [{url_index:3d}] {status_text:10s} ({elapsed:6.2f}s) - {short_url}{retry_info}")

        if status == "success":
            success_count += 1
        elif status == "timeout":
            timeout_count += 1
            failed_count += 1
        elif status == "error":
            error_count += 1
            failed_count += 1
        else:
            failed_count += 1

    print("=" * 80)
    print(f"Total execution time: {total_time:.2f}s")
    print(f"Successful: {success_count}/{total_urls}")
    print(f"Failed: {failed_count}/{total_urls}")
    if timeout_count > 0:
        print(f"  - Timeouts: {timeout_count}")
    if error_count > 0:
        print(f"  - Errors: {error_count}")
    if failed_count - timeout_count - error_count > 0:
        print(f"  - Other failures: {failed_count - timeout_count - error_count}")
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    return success_count, failed_count


def main():
    """Main function to orchestrate the entire process."""

    # Get the script's directory and project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)  # Parent directory (scrapy project root)

    # Configuration
    INPUT_FILE = os.path.join(script_dir, 'feature_spec_urls.txt')
    SPIDER_NAME = 'feature-specification-fragment'
    BATCH_SIZE = 2  # Number of parallel spiders
    TIMEOUT = 500  # Timeout per spider in seconds
    MAX_RETRIES = 2  # Maximum number of retry attempts for failed URLs

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
        print(f"[INFO] Please create 'feature_spec_urls.txt' in the utils folder with URLs (comma or newline separated)")
        sys.exit(1)

    print(f"[SUCCESS] Found {len(urls)} URL(s) to process")
    print()

    # Run spiders in batches with retry mechanism (pipeline handles output)
    success_count, failed_count = run_spiders_in_batches(
        SPIDER_NAME, urls, BATCH_SIZE, project_root, TIMEOUT, MAX_RETRIES
    )

    print(f"\n[INFO] Features and Specifications have been written to Output/[ModelName]/ by the pipeline")

    # Clean up duplicate headers in output files
    print(f"\n[INFO] Cleaning duplicate headers from CSV files...")
    output_base = os.path.join(project_root, 'Output')

    if os.path.exists(output_base):
        # Find all Features.csv and Specifications.csv files
        for root, dirs, files in os.walk(output_base):
            for file in files:
                if file in ['Features.csv', 'Specifications.csv']:
                    csv_path = os.path.join(root, file)
                    remove_duplicate_headers(csv_path)

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
