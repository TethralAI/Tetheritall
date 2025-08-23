#!/bin/bash

# Performance Test Runner Script
# This script runs various performance tests to validate the system's ability to handle
# complex calls, simultaneous calls, and high user load.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
GATEWAY_BASE=${GATEWAY_BASE:-"http://localhost:8000"}
API_TOKEN=${API_TOKEN:-"test-api-key"}
TEST_DURATION=${TEST_DURATION:-"5m"}
VUS=${VUS:-"50"}
K6_BINARY=${K6_BINARY:-"k6"}

# Test scenarios
declare -A TEST_SCENARIOS=(
    ["constant_load"]="Constant load testing with sustained traffic"
    ["spike_load"]="Spike testing with sudden traffic increases"
    ["stress_load"]="Stress testing with gradual load increase"
    ["complex_operations"]="Complex operations testing"
    ["simultaneous_calls"]="Simultaneous calls testing"
)

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if k6 is installed
    if ! command -v $K6_BINARY &> /dev/null; then
        print_error "k6 is not installed or not in PATH"
        print_status "Please install k6 from https://k6.io/docs/getting-started/installation/"
        exit 1
    fi
    
    # Check if gateway is accessible
    if ! curl -s -f "$GATEWAY_BASE/health" > /dev/null; then
        print_warning "Gateway is not accessible at $GATEWAY_BASE"
        print_status "Make sure the API server is running"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    print_success "Prerequisites check completed"
}

# Function to run a single test
run_test() {
    local test_name=$1
    local description=$2
    local test_vus=${3:-$VUS}
    local test_duration=${4:-$TEST_DURATION}
    
    print_status "Running $test_name: $description"
    print_status "VUs: $test_vus, Duration: $test_duration"
    
    # Create output directory
    mkdir -p "test_results/$(date +%Y%m%d)"
    local output_file="test_results/$(date +%Y%m%d)/${test_name}_$(date +%H%M%S).json"
    
    # Run k6 test
    $K6_BINARY run \
        --env GATEWAY_BASE="$GATEWAY_BASE" \
        --env API_TOKEN="$API_TOKEN" \
        --env VUS="$test_vus" \
        --env TEST_DURATION="$test_duration" \
        --out json="$output_file" \
        --summary-export="test_results/$(date +%Y%m%d)/${test_name}_$(date +%H%M%S)_summary.json" \
        k6/enhanced_load.js
    
    if [ $? -eq 0 ]; then
        print_success "$test_name completed successfully"
        print_status "Results saved to $output_file"
    else
        print_error "$test_name failed"
        return 1
    fi
}

# Function to run all tests
run_all_tests() {
    print_status "Starting comprehensive performance test suite..."
    
    # Create results directory
    mkdir -p "test_results/$(date +%Y%m%d)"
    
    # Run each test scenario
    for test_name in "${!TEST_SCENARIOS[@]}"; do
        case $test_name in
            "constant_load")
                run_test "$test_name" "${TEST_SCENARIOS[$test_name]}" 50 "10m"
                ;;
            "spike_load")
                run_test "$test_name" "${TEST_SCENARIOS[$test_name]}" 100 "5m"
                ;;
            "stress_load")
                run_test "$test_name" "${TEST_SCENARIOS[$test_name]}" 60 "15m"
                ;;
            "complex_operations")
                run_test "$test_name" "${TEST_SCENARIOS[$test_name]}" 10 "5m"
                ;;
            "simultaneous_calls")
                run_test "$test_name" "${TEST_SCENARIOS[$test_name]}" 20 "5m"
                ;;
        esac
        
        # Wait between tests
        if [ $? -eq 0 ]; then
            print_status "Waiting 30 seconds before next test..."
            sleep 30
        fi
    done
    
    print_success "All tests completed"
}

# Function to run a specific test
run_specific_test() {
    local test_name=$1
    
    if [[ -z "${TEST_SCENARIOS[$test_name]}" ]]; then
        print_error "Unknown test: $test_name"
        print_status "Available tests: ${!TEST_SCENARIOS[*]}"
        exit 1
    fi
    
    case $test_name in
        "constant_load")
            run_test "$test_name" "${TEST_SCENARIOS[$test_name]}" 50 "10m"
            ;;
        "spike_load")
            run_test "$test_name" "${TEST_SCENARIOS[$test_name]}" 100 "5m"
            ;;
        "stress_load")
            run_test "$test_name" "${TEST_SCENARIOS[$test_name]}" 60 "15m"
            ;;
        "complex_operations")
            run_test "$test_name" "${TEST_SCENARIOS[$test_name]}" 10 "5m"
            ;;
        "simultaneous_calls")
            run_test "$test_name" "${TEST_SCENARIOS[$test_name]}" 20 "5m"
            ;;
    esac
}

# Function to show test results
show_results() {
    local results_dir="test_results/$(date +%Y%m%d)"
    
    if [ ! -d "$results_dir" ]; then
        print_error "No test results found for today"
        exit 1
    fi
    
    print_status "Test Results Summary:"
    echo
    
    for summary_file in "$results_dir"/*_summary.json; do
        if [ -f "$summary_file" ]; then
            local test_name=$(basename "$summary_file" _summary.json)
            print_status "Test: $test_name"
            
            # Extract key metrics using jq if available
            if command -v jq &> /dev/null; then
                local http_reqs=$(jq -r '.metrics.http_reqs.values.count // "N/A"' "$summary_file")
                local http_req_duration=$(jq -r '.metrics.http_req_duration.values.avg // "N/A"' "$summary_file")
                local http_req_failed=$(jq -r '.metrics.http_req_failed.values.rate // "N/A"' "$summary_file")
                
                echo "  Total Requests: $http_reqs"
                echo "  Avg Response Time: ${http_req_duration}ms"
                echo "  Error Rate: $(echo "$http_req_failed * 100" | bc -l 2>/dev/null || echo "N/A")%"
            else
                echo "  Results file: $summary_file"
            fi
            echo
        fi
    done
}

# Function to show help
show_help() {
    echo "Performance Test Runner"
    echo
    echo "Usage: $0 [OPTIONS] [TEST_NAME]"
    echo
    echo "Options:"
    echo "  -h, --help          Show this help message"
    echo "  -a, --all           Run all tests"
    echo "  -r, --results       Show test results"
    echo "  -g, --gateway URL   Set gateway URL (default: $GATEWAY_BASE)"
    echo "  -t, --token TOKEN   Set API token (default: $API_TOKEN)"
    echo "  -d, --duration DUR  Set test duration (default: $TEST_DURATION)"
    echo "  -v, --vus VUS       Set virtual users (default: $VUS)"
    echo
    echo "Available Tests:"
    for test_name in "${!TEST_SCENARIOS[@]}"; do
        echo "  $test_name: ${TEST_SCENARIOS[$test_name]}"
    done
    echo
    echo "Examples:"
    echo "  $0 --all                    # Run all tests"
    echo "  $0 constant_load            # Run constant load test"
    echo "  $0 --gateway http://api:8000 --all  # Run all tests with custom gateway"
    echo "  $0 --results                # Show today's test results"
}

# Main script logic
main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -a|--all)
                RUN_ALL=true
                shift
                ;;
            -r|--results)
                SHOW_RESULTS=true
                shift
                ;;
            -g|--gateway)
                GATEWAY_BASE="$2"
                shift 2
                ;;
            -t|--token)
                API_TOKEN="$2"
                shift 2
                ;;
            -d|--duration)
                TEST_DURATION="$2"
                shift 2
                ;;
            -v|--vus)
                VUS="$2"
                shift 2
                ;;
            -*)
                print_error "Unknown option: $1"
                show_help
                exit 1
                ;;
            *)
                TEST_NAME="$1"
                shift
                ;;
        esac
    done
    
    # Check prerequisites
    check_prerequisites
    
    # Show configuration
    print_status "Configuration:"
    echo "  Gateway: $GATEWAY_BASE"
    echo "  API Token: $API_TOKEN"
    echo "  Test Duration: $TEST_DURATION"
    echo "  Virtual Users: $VUS"
    echo
    
    # Execute based on arguments
    if [ "$SHOW_RESULTS" = true ]; then
        show_results
    elif [ "$RUN_ALL" = true ]; then
        run_all_tests
    elif [ -n "$TEST_NAME" ]; then
        run_specific_test "$TEST_NAME"
    else
        print_error "No test specified"
        show_help
        exit 1
    fi
}

# Run main function with all arguments
main "$@"
