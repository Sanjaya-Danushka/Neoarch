# Test Configuration
# This file configures the test environment for NeoArch

import os
import sys

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Test configuration
TEST_CONFIG = {
    'timeout': 30,
    'mock_external_calls': True,
    'test_data_dir': os.path.join(os.path.dirname(__file__), 'data'),
}

# Create test data directory if it doesn't exist
os.makedirs(TEST_CONFIG['test_data_dir'], exist_ok=True)