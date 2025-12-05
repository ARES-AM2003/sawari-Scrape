#!/usr/bin/env python3
"""
Complete Pipeline Orchestration Script
This script runs all the scraping and processing scripts in sequence:
1. run_first_spiders.py - Run initial spiders (faq, rating, pros/cons/colors)
2. run_variants_parallel.py - Run variant spiders in parallel
3. run_feature_spec_parallel.py - Run feature & specification spiders
4. run_seedMileage.py - Fill missing mileage data
5. run_processVariant.py - Process variant names and add metadata
6. run_variantcheck.py - Verify variant consistency
7. sheet-creator.py - Create final Excel sheet (only if variants match)

Usage:
    python run_complete_pipeline.py <output_folder>

Example:
    python run_complete_pipeline.py Output/Citroen/C3
"""

import os
import sys
import subprocess
import time
from datetime import datetime


class PipelineRunner:
    """Orchestrates the complete scraping and processing pipeline."""

    def __init__(self, output_folder):
        """
        Initialize the pipeline runner.

        Args:
            output_folder: The output folder path (e.g., "Output/Citroen/C3")
        """
        self.output_folder = output_folder
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.project_root = os.path.dirname(self.script_dir)

        # Define all script paths
        self.scripts = {
            'first_spiders': os.path.join(self.script_dir, 'run_first_spiders.py'),
            'variants': os.path.join(self.script_dir, 'run_variants_parallel.py'),
            'features_specs': os.path.join(self.script_dir, 'run_feat_next.py'),
            'mileage': os.path.join(self.script_dir, 'run_seedMileage.py'),
            'process_variant': os.path.join(self.script_dir, 'run_processVariant.py'),
            'variant_check': os.path.join(self.script_dir, 'run_variantcheck.py'),
            'sheet_creator': os.path.join(self.script_dir, 'sheet-creator.py')
        }

        self.start_time = None
        self.step_times = {}

    def log(self, message, level="INFO"):
        """Print formatted log message."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] [{level}] {message}")

    def print_header(self, title):
        """Print a formatted header."""
        print("\n" + "=" * 80)
        print(f"  {title}")
        print("=" * 80)

    def print_step(self, step_number, step_name):
        """Print step information."""
        print("\n" + "-" * 80)
        print(f"STEP {step_number}: {step_name}")
        print("-" * 80)

    def run_command(self, command, step_name, cwd=None):
        """
        Run a shell command and capture output.

        Args:
            command: Command to run (list of strings)
            step_name: Name of the step for logging
            cwd: Working directory (defaults to project root)

        Returns:
            True if successful, False otherwise
        """
        if cwd is None:
            cwd = self.project_root

        self.log(f"Running: {' '.join(command)}")
        step_start = time.time()

        try:
            result = subprocess.run(
                command,
                cwd=cwd,
                capture_output=False,  # Show output in real-time
                text=True
            )

            elapsed = time.time() - step_start
            self.step_times[step_name] = elapsed

            if result.returncode == 0:
                self.log(f"✓ {step_name} completed successfully in {elapsed:.2f}s", "SUCCESS")
                return True
            else:
                self.log(f"✗ {step_name} failed with exit code {result.returncode}", "ERROR")
                return False

        except Exception as e:
            elapsed = time.time() - step_start
            self.step_times[step_name] = elapsed
            self.log(f"✗ {step_name} error: {e}", "ERROR")
            return False

    def check_script_exists(self, script_name):
        """Check if a script file exists."""
        script_path = self.scripts.get(script_name)
        if not script_path or not os.path.exists(script_path):
            self.log(f"Script not found: {script_path}", "ERROR")
            return False
        return True

    def update_script_paths(self):
        """Update hardcoded paths in scripts to use the output folder."""
        self.log(f"Updating script paths to use folder: {self.output_folder}")

        # Get absolute path
        abs_output_folder = os.path.join(self.project_root, self.output_folder)

        # Update run_seedMileage.py paths
        mileage_script = self.scripts['mileage']
        try:
            with open(mileage_script, 'r', encoding='utf-8') as f:
                content = f.read()

            # Update CSV paths
            variants_csv_path = os.path.join(abs_output_folder, 'Variants.csv')
            content = content.replace(
                'INPUT_CSV_PATH = "/home/ares-am/Projects/BNT/scrapy/Output/Citroen/C3/Variants.csv"',
                f'INPUT_CSV_PATH = "{variants_csv_path}"'
            )
            content = content.replace(
                'OUTPUT_CSV_PATH = "/home/ares-am/Projects/BNT/scrapy/Output/Citroen/C3/Variants.csv"',
                f'OUTPUT_CSV_PATH = "{variants_csv_path}"'
            )

            with open(mileage_script, 'w', encoding='utf-8') as f:
                f.write(content)

            self.log(f"✓ Updated {os.path.basename(mileage_script)}")
        except Exception as e:
            self.log(f"⚠ Could not update {os.path.basename(mileage_script)}: {e}", "WARNING")

        # Update run_processVariant.py paths
        process_script = self.scripts['process_variant']
        try:
            with open(process_script, 'r', encoding='utf-8') as f:
                content = f.read()

            # Update CSV base path
            content = content.replace(
                'CSV_BASE_PATH = "/home/ares-am/Projects/BNT/scrapy/Output/Citroen/C3/"',
                f'CSV_BASE_PATH = "{abs_output_folder}/"'
            )

            with open(process_script, 'w', encoding='utf-8') as f:
                f.write(content)

            self.log(f"✓ Updated {os.path.basename(process_script)}")
        except Exception as e:
            self.log(f"⚠ Could not update {os.path.basename(process_script)}: {e}", "WARNING")

        # Update sheet-creator.py path
        sheet_script = self.scripts['sheet_creator']
        try:
            with open(sheet_script, 'r', encoding='utf-8') as f:
                content = f.read()

            # Update csv_folder
            content = content.replace(
                'csv_folder = "/home/ares-am/Projects/BNT/scrapy/Output/Citroen/C3"',
                f'csv_folder = "{abs_output_folder}"'
            )

            with open(sheet_script, 'w', encoding='utf-8') as f:
                f.write(content)

            self.log(f"✓ Updated {os.path.basename(sheet_script)}")
        except Exception as e:
            self.log(f"⚠ Could not update {os.path.basename(sheet_script)}: {e}", "WARNING")

    def run_step_1(self):
        """Step 1: Run initial spiders (faq, rating, pros/cons/colors)."""
        self.print_step(1, "Running Initial Spiders (FAQ, Rating, Pros/Cons/Colors)")

        if not self.check_script_exists('first_spiders'):
            return False

        command = ['python3', self.scripts['first_spiders']]
        return self.run_command(command, "Initial Spiders")

    def run_step_2(self):
        """Step 2: Run variant spiders in parallel."""
        self.print_step(2, "Running Variant Spiders in Parallel")

        if not self.check_script_exists('variants'):
            return False

        command = ['python3', self.scripts['variants']]
        return self.run_command(command, "Variant Spiders")

    def run_step_3(self):
        """Step 3: Run feature & specification spiders."""
        self.print_step(3, "Running Feature & Specification Spiders")

        if not self.check_script_exists('features_specs'):
            return False

        command = ['python3', self.scripts['features_specs']]
        return self.run_command(command, "Feature & Specification Spiders")

    def run_step_4(self):
        """Step 4: Fill missing mileage data."""
        self.print_step(4, "Filling Missing Mileage Data")

        if not self.check_script_exists('mileage'):
            return False

        command = ['python3', self.scripts['mileage']]
        return self.run_command(command, "Seed Mileage")

    def run_step_5(self):
        """Step 5: Process variant names and metadata."""
        self.print_step(5, "Processing Variant Names and Metadata")

        if not self.check_script_exists('process_variant'):
            return False

        # Get the Variants.csv path
        variants_csv = os.path.join(self.project_root, self.output_folder, 'Variants.csv')

        command = ['python3', self.scripts['process_variant'], variants_csv]
        return self.run_command(command, "Process Variants")

    def run_step_6(self):
        """Step 6: Verify variant consistency."""
        self.print_step(6, "Verifying Variant Consistency")

        if not self.check_script_exists('variant_check'):
            return False

        # Run variant check
        folder_path = os.path.join(self.project_root, self.output_folder)
        command = ['python3', self.scripts['variant_check'], folder_path]

        return self.run_command(command, "Variant Check")

    def run_step_7(self):
        """Step 7: Create final Excel sheet."""
        self.print_step(7, "Creating Final Excel Sheet")

        if not self.check_script_exists('sheet_creator'):
            return False

        command = ['python3', self.scripts['sheet_creator']]
        return self.run_command(command, "Sheet Creator")

    def print_summary(self, success_steps, total_steps):
        """Print execution summary."""
        self.print_header("PIPELINE EXECUTION SUMMARY")

        total_time = time.time() - self.start_time

        print(f"\nTotal Steps: {total_steps}")
        print(f"Successful: {success_steps}")
        print(f"Failed: {total_steps - success_steps}")
        print(f"\nTotal Execution Time: {total_time:.2f}s")

        print("\n" + "-" * 80)
        print("Step Execution Times:")
        print("-" * 80)

        for step_name, elapsed in self.step_times.items():
            print(f"  {step_name:30s} : {elapsed:8.2f}s")

        print("\n" + "=" * 80)
        print(f"Pipeline ended at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

    def run(self):
        """Run the complete pipeline."""
        self.start_time = time.time()

        self.print_header("COMPLETE PIPELINE ORCHESTRATION")
        self.log(f"Output Folder: {self.output_folder}")
        self.log(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Update script paths
        self.update_script_paths()

        # Track steps
        steps = []
        success_count = 0

        # Step 1: Run initial spiders
        if self.run_step_1():
            success_count += 1
            steps.append(('Initial Spiders', True))
        else:
            steps.append(('Initial Spiders', False))
            self.log("Pipeline stopped due to failure in Step 1", "ERROR")
            self.print_summary(success_count, len(steps))
            return False

        # Step 2: Run variant spiders
        if self.run_step_2():
            success_count += 1
            steps.append(('Variant Spiders', True))
        else:
            steps.append(('Variant Spiders', False))
            self.log("Pipeline stopped due to failure in Step 2", "ERROR")
            self.print_summary(success_count, len(steps))
            return False

        # Step 3: Run feature & spec spiders
        if self.run_step_3():
            success_count += 1
            steps.append(('Feature & Spec Spiders', True))
        else:
            steps.append(('Feature & Spec Spiders', False))
            self.log("Pipeline stopped due to failure in Step 3", "ERROR")
            self.print_summary(success_count, len(steps))
            return False

        # Step 4: Fill mileage
        if self.run_step_4():
            success_count += 1
            steps.append(('Seed Mileage', True))
        else:
            steps.append(('Seed Mileage', False))
            self.log("⚠ Mileage filling failed, but continuing pipeline...", "WARNING")
            steps.append(('Seed Mileage', False))

        # Step 5: Process variants
        if self.run_step_5():
            success_count += 1
            steps.append(('Process Variants', True))
        else:
            steps.append(('Process Variants', False))
            self.log("⚠ Variant processing failed, but continuing to check...", "WARNING")

        # Step 6: Variant check
        variant_check_success = self.run_step_6()
        if variant_check_success:
            success_count += 1
            steps.append(('Variant Check', True))

            # Step 7: Create sheet (only if variant check passed)
            self.log("Variant check passed! Proceeding to create Excel sheet...")
            if self.run_step_7():
                success_count += 1
                steps.append(('Sheet Creator', True))
            else:
                steps.append(('Sheet Creator', False))
                self.log("Sheet creation failed", "ERROR")
        else:
            steps.append(('Variant Check', False))
            self.log("⚠ Variant check FAILED! Skipping Excel sheet creation.", "WARNING")
            self.log("Please review the variant mismatch errors above.", "WARNING")

        # Print summary
        self.print_summary(success_count, len(steps))

        return variant_check_success


def main():
    """Main entry point."""
    if len(sys.argv) != 2:
        print("Usage: python run_complete_pipeline.py <output_folder>")
        print("\nExample:")
        print("  python run_complete_pipeline.py Output/Citroen/C3")
        print("\nDescription:")
        print("  Runs the complete scraping and processing pipeline:")
        print("    1. Initial spiders (FAQ, Rating, Pros/Cons/Colors)")
        print("    2. Variant spiders (parallel)")
        print("    3. Feature & Specification spiders (parallel)")
        print("    4. Seed missing mileage data")
        print("    5. Process variant names and metadata")
        print("    6. Verify variant consistency")
        print("    7. Create Excel sheet (only if variants match)")
        sys.exit(1)

    output_folder = sys.argv[1]

    # Validate output folder path
    if not output_folder.startswith('Output/'):
        print(f"⚠ Warning: Output folder should start with 'Output/'")
        print(f"  You provided: {output_folder}")
        try:
            response = input("Continue anyway? (y/n): ")
            if response.lower() != 'y':
                sys.exit(0)
        except (EOFError, KeyboardInterrupt):
            print("\nAssuming 'no' in non-interactive environment")
            sys.exit(0)

    # Run pipeline
    runner = PipelineRunner(output_folder)
    success = runner.run()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Pipeline terminated by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
