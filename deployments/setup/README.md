# Setup Directory 🔧

This directory contains installation and setup tools for CHATTA.

## Files

- **setup_wizard_enhanced.py** - Intelligent setup wizard with detection
  - Dynamic detection of existing installations
  - Power user bypass options (--express, --skip-wizard)
  - Readiness scoring system
  
- **setup_wizard.py** - Original setup wizard
  - Basic interactive setup
  - Step-by-step configuration

- **install.sh** - Shell installation script
  - One-command installation
  - Platform detection

- **test-install.sh** - Installation testing script
  - Verifies installation process
  - Checks dependencies

## Usage

### Interactive Setup
```bash
python setup/setup_wizard_enhanced.py
```

### Express Setup (Power Users)
```bash
python setup/setup_wizard_enhanced.py --express
```

### Check System Only
```bash
python setup/setup_wizard_enhanced.py --check-only
```