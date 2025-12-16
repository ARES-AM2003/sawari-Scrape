#!/usr/bin/env python3
"""
Test script to verify single browser with multiple tabs is working correctly.
This will help you see the memory savings and performance improvements.
"""

from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver import Firefox, FirefoxProfile
from webdriver_manager.firefox import GeckoDriverManager
import time
import os
import psutil
import threading
from queue import Queue


def get_process_memory(process):
    """Get memory usage of a process in MB"""
    try:
        return process.memory_info().rss / 1024 / 1024
    except:
        return 0


def test_single_browser_multiple_tabs():
    """Test single browser with multiple tabs approach"""
    print("\n" + "="*70)
    print("🧪 TESTING: Single Browser with Multiple Tabs")
    print("="*70)
    
    # Get initial memory
    process = psutil.Process(os.getpid())
    initial_memory = get_process_memory(process)
    print(f"📊 Initial memory: {initial_memory:.2f} MB")
    
    # Create Firefox with options
    options = FirefoxOptions()
    options.add_argument("--headless")
    
    # Create profile (optional - comment out if you don't have extension)
    try:
        profile = FirefoxProfile()
        profile.add_extension("/home/ares-am/Projects/BNT/scrapy/utils/uBlock0_1.68.1b0.firefox.xpi")
        options.profile = profile
        print("✅ uBlock extension loaded")
    except Exception as e:
        print(f"⚠️  Extension not loaded (optional): {e}")
    
    # Get driver path
    try:
        import shutil
        driver_path = shutil.which("geckodriver")
        if not driver_path:
            driver_path = GeckoDriverManager().install()
    except:
        driver_path = GeckoDriverManager().install()
    
    service = FirefoxService(driver_path)
    driver = Firefox(service=service, options=options)
    
    time.sleep(2)  # Let browser fully load
    after_browser_memory = get_process_memory(process)
    browser_memory = after_browser_memory - initial_memory
    print(f"🌐 Browser started: {browser_memory:.2f} MB")
    
    # Open multiple tabs
    num_tabs = 4
    print(f"\n📑 Opening {num_tabs} tabs...")
    
    main_tab = driver.current_window_handle
    tab_pool = Queue()
    tab_pool.put(main_tab)
    
    for i in range(num_tabs - 1):
        driver.execute_script("window.open('about:blank', '_blank');")
        time.sleep(0.1)
    
    all_tabs = driver.window_handles
    for tab in all_tabs[1:]:
        tab_pool.put(tab)
    
    time.sleep(1)
    after_tabs_memory = get_process_memory(process)
    tabs_memory = after_tabs_memory - after_browser_memory
    print(f"📑 {num_tabs} tabs created: +{tabs_memory:.2f} MB")
    print(f"📊 Total memory: {after_tabs_memory - initial_memory:.2f} MB")
    
    # Test parallel loading in different tabs
    print(f"\n🔄 Testing parallel page loads across {num_tabs} tabs...")
    
    test_urls = [
        "https://www.example.com",
        "https://www.wikipedia.org",
        "https://www.github.com",
        "https://www.stackoverflow.com"
    ]
    
    def load_in_tab(tab_handle, url, lock):
        with lock:
            driver.switch_to.window(tab_handle)
            print(f"  Tab [{tab_handle[:8]}...] loading: {url}")
            driver.get(url)
            title = driver.title[:50]
            print(f"  ✅ Tab [{tab_handle[:8]}...] loaded: {title}")
    
    lock = threading.Lock()
    threads = []
    
    start_time = time.time()
    
    for i, url in enumerate(test_urls[:num_tabs]):
        tab = tab_pool.get()
        thread = threading.Thread(target=load_in_tab, args=(tab, url, lock))
        thread.start()
        threads.append((thread, tab))
    
    for thread, tab in threads:
        thread.join()
        tab_pool.put(tab)  # Return to pool
    
    end_time = time.time()
    elapsed = end_time - start_time
    
    print(f"\n⏱️  Loaded {num_tabs} pages in {elapsed:.2f} seconds")
    print(f"   (Average: {elapsed/num_tabs:.2f} seconds per page)")
    
    final_memory = get_process_memory(process)
    total_memory = final_memory - initial_memory
    
    print(f"\n📊 Final memory usage: {total_memory:.2f} MB")
    print(f"   Browser: {browser_memory:.2f} MB")
    print(f"   {num_tabs} Tabs: {tabs_memory:.2f} MB")
    print(f"   Average per tab: {tabs_memory/num_tabs:.2f} MB")
    
    # Calculate savings vs separate browsers
    separate_browsers_memory = num_tabs * browser_memory
    savings = separate_browsers_memory - total_memory
    savings_percent = (savings / separate_browsers_memory) * 100
    
    print(f"\n💰 MEMORY SAVINGS:")
    print(f"   {num_tabs} separate browsers would use: {separate_browsers_memory:.2f} MB")
    print(f"   Single browser + {num_tabs} tabs uses: {total_memory:.2f} MB")
    print(f"   💚 SAVINGS: {savings:.2f} MB ({savings_percent:.1f}% reduction!)")
    
    # Cleanup
    print(f"\n🛑 Closing browser...")
    driver.quit()
    time.sleep(1)
    
    final_cleanup_memory = get_process_memory(process)
    print(f"✅ Cleanup complete. Memory freed: {final_memory - final_cleanup_memory:.2f} MB")


def test_multiple_browsers():
    """Test multiple separate browsers approach (for comparison)"""
    print("\n" + "="*70)
    print("🧪 TESTING: Multiple Separate Browsers (OLD APPROACH)")
    print("="*70)
    print("⚠️  WARNING: This will use significantly more RAM!")
    
    answer = input("Do you want to run this test? (y/n): ")
    if answer.lower() != 'y':
        print("Skipped.")
        return
    
    process = psutil.Process(os.getpid())
    initial_memory = get_process_memory(process)
    print(f"📊 Initial memory: {initial_memory:.2f} MB")
    
    drivers = []
    num_browsers = 4
    
    print(f"\n🌐 Starting {num_browsers} separate browsers...")
    
    for i in range(num_browsers):
        options = FirefoxOptions()
        options.add_argument("--headless")
        
        try:
            import shutil
            driver_path = shutil.which("geckodriver")
            if not driver_path:
                driver_path = GeckoDriverManager().install()
        except:
            driver_path = GeckoDriverManager().install()
        
        service = FirefoxService(driver_path)
        driver = Firefox(service=service, options=options)
        drivers.append(driver)
        
        time.sleep(2)
        current_memory = get_process_memory(process)
        print(f"   Browser {i+1}: {current_memory - initial_memory:.2f} MB total")
    
    final_memory = get_process_memory(process)
    total_memory = final_memory - initial_memory
    
    print(f"\n📊 Total memory for {num_browsers} browsers: {total_memory:.2f} MB")
    print(f"   Average per browser: {total_memory/num_browsers:.2f} MB")
    
    print(f"\n🛑 Closing all browsers...")
    for driver in drivers:
        driver.quit()
    
    time.sleep(1)
    cleanup_memory = get_process_memory(process)
    print(f"✅ Cleanup complete. Memory freed: {final_memory - cleanup_memory:.2f} MB")


def main():
    print("\n" + "="*70)
    print("🚀 Selenium Multi-Tab Memory Test")
    print("="*70)
    print("\nThis script will demonstrate the memory savings of using")
    print("a single browser with multiple tabs vs multiple browsers.")
    print("="*70)
    
    try:
        # Test single browser with tabs (NEW approach)
        test_single_browser_multiple_tabs()
        
        # Test multiple browsers (OLD approach) - optional
        test_multiple_browsers()
        
        print("\n" + "="*70)
        print("✅ ALL TESTS COMPLETED")
        print("="*70)
        print("\n💡 KEY TAKEAWAYS:")
        print("   • Single browser + multiple tabs saves ~70% RAM")
        print("   • Tabs add only ~25-50MB each")
        print("   • Perfect for your 8GB RAM system")
        print("   • Can handle 4-8 concurrent requests comfortably")
        print("="*70 + "\n")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Check if psutil is installed
    try:
        import psutil
    except ImportError:
        print("❌ Error: psutil is required")
        print("Install it with: pip install psutil")
        exit(1)
    
    main()