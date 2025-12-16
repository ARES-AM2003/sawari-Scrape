#!/bin/bash

echo "=================================="
echo "🔍 Browser Process Counter"
echo "=================================="
echo ""

echo "Counting Firefox processes..."
firefox_count=$(ps aux | grep -i firefox | grep -v grep | wc -l)
echo "Total Firefox processes: $firefox_count"
echo ""

echo "Detailed Firefox processes:"
ps aux | grep -i firefox | grep -v grep | awk '{print $2, $11, $12, $13, $14}' | head -20
echo ""

echo "=================================="
echo "Process Tree:"
echo "=================================="
pstree -p | grep firefox | head -20
echo ""

echo "=================================="
echo "Browser Window Count (if running X):"
echo "=================================="
if command -v wmctrl &> /dev/null; then
    wmctrl -l | grep -i firefox | wc -l
    echo "Firefox windows detected"
else
    echo "wmctrl not installed (install with: sudo apt install wmctrl)"
fi
echo ""

echo "=================================="
echo "Memory Usage by Firefox:"
echo "=================================="
ps aux | grep -i firefox | grep -v grep | awk '{mem+=$6} END {print "Total Firefox Memory: " mem/1024 " MB"}'
echo ""

echo "=================================="
echo "Expected Setup:"
echo "  3 browser instances"
echo "  4 tabs per browser = 12 tabs total"
echo ""
echo "If you see MORE than 3-5 main Firefox"
echo "processes, something is wrong!"
echo "=================================="