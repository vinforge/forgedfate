#!/bin/bash
# ForgedFate Filebeat Setup Script
# Automatically installs and configures Filebeat for Kismet integration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
FILEBEAT_VERSION="8.14.0"
FILEBEAT_DEB="filebeat-${FILEBEAT_VERSION}-amd64.deb"
FILEBEAT_URL="https://artifacts.elastic.co/downloads/beats/filebeat/${FILEBEAT_DEB}"

print_header() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                ForgedFate Filebeat Setup                    ║"
    echo "║              Automated Kismet → Elasticsearch               ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
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

check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

check_system() {
    print_step "Checking system requirements..."
    
    # Check if running on supported system
    if ! command -v apt-get &> /dev/null; then
        print_error "This script requires a Debian/Ubuntu system with apt-get"
        exit 1
    fi
    
    # Check if curl is available
    if ! command -v curl &> /dev/null; then
        print_step "Installing curl..."
        apt-get update -qq
        apt-get install -y curl
    fi
    
    # Check if python3 is available
    if ! command -v python3 &> /dev/null; then
        print_step "Installing Python 3..."
        apt-get install -y python3 python3-pip
    fi
    
    # Check if PyYAML is available
    if ! python3 -c "import yaml" &> /dev/null; then
        print_step "Installing PyYAML..."
        apt-get install -y python3-yaml
    fi
    
    print_success "System requirements satisfied"
}

install_filebeat() {
    print_step "Installing Filebeat ${FILEBEAT_VERSION}..."
    
    # Check if Filebeat is already installed
    if command -v filebeat &> /dev/null; then
        local installed_version=$(filebeat version | grep -oP 'version \K[0-9.]+')
        if [[ "$installed_version" == "$FILEBEAT_VERSION" ]]; then
            print_success "Filebeat ${FILEBEAT_VERSION} is already installed"
            return 0
        else
            print_warning "Different Filebeat version detected: $installed_version"
            print_step "Upgrading to version ${FILEBEAT_VERSION}..."
        fi
    fi
    
    # Download Filebeat
    print_step "Downloading Filebeat..."
    cd /tmp
    if [[ -f "$FILEBEAT_DEB" ]]; then
        print_step "Using existing download: $FILEBEAT_DEB"
    else
        curl -L -O "$FILEBEAT_URL"
    fi
    
    # Install Filebeat
    print_step "Installing Filebeat package..."
    dpkg -i "$FILEBEAT_DEB" || {
        print_step "Fixing dependencies..."
        apt-get install -f -y
    }
    
    # Enable but don't start yet
    systemctl enable filebeat
    
    print_success "Filebeat installed successfully"
}

setup_permissions() {
    print_step "Setting up permissions for Kismet logs..."
    
    # Create kismet group if it doesn't exist
    if ! getent group kismet > /dev/null 2>&1; then
        groupadd kismet
        print_step "Created kismet group"
    fi
    
    # Add filebeat user to kismet group
    usermod -a -G kismet filebeat
    
    # Set up log directory permissions
    if [[ -d "/opt/kismet/logs" ]]; then
        chgrp -R kismet /opt/kismet/logs
        chmod -R g+r /opt/kismet/logs
        print_success "Permissions configured for /opt/kismet/logs"
    else
        print_warning "Kismet log directory not found at /opt/kismet/logs"
        print_warning "You may need to adjust permissions manually after running Kismet"
    fi
}

create_integration_script() {
    print_step "Setting up integration script..."
    
    local script_dir="/opt/forgedfate"
    local script_path="$script_dir/filebeat_integration.py"
    
    # Create directory
    mkdir -p "$script_dir"
    
    # Copy integration script if it exists in current directory
    if [[ -f "filebeat_integration.py" ]]; then
        cp "filebeat_integration.py" "$script_path"
        chmod +x "$script_path"
        print_success "Integration script installed to $script_path"
    else
        print_warning "Integration script not found in current directory"
        print_warning "Please copy filebeat_integration.py to $script_path manually"
    fi
    
    # Create convenience symlink
    if [[ -f "$script_path" ]]; then
        ln -sf "$script_path" "/usr/local/bin/forgedfate-filebeat"
        print_success "Created convenience command: forgedfate-filebeat"
    fi
}

show_next_steps() {
    echo -e "${GREEN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                    Setup Complete!                          ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    echo -e "${BLUE}Next Steps:${NC}"
    echo "1. Start Kismet to generate some logs:"
    echo "   ${YELLOW}sudo kismet${NC}"
    echo ""
    echo "2. Configure Filebeat integration using one of these methods:"
    echo ""
    echo "   ${BLUE}Method A: Web Interface (Recommended)${NC}"
    echo "   - Open http://localhost:2501"
    echo "   - Go to API Configuration → Elasticsearch Export"
    echo "   - Click 'Setup Filebeat Integration'"
    echo ""
    echo "   ${BLUE}Method B: Command Line${NC}"
    if [[ -f "/usr/local/bin/forgedfate-filebeat" ]]; then
        echo "   ${YELLOW}sudo forgedfate-filebeat \\${NC}"
    else
        echo "   ${YELLOW}sudo python3 filebeat_integration.py \\${NC}"
    fi
    echo "     ${YELLOW}--elasticsearch-url 'https://your-elasticsearch:9200' \\${NC}"
    echo "     ${YELLOW}--username 'your-username' \\${NC}"
    echo "     ${YELLOW}--password 'your-password' \\${NC}"
    echo "     ${YELLOW}--device-name 'your-device-name'${NC}"
    echo ""
    echo "3. Verify the integration:"
    echo "   ${YELLOW}sudo systemctl status filebeat${NC}"
    echo "   ${YELLOW}sudo journalctl -u filebeat -f${NC}"
    echo ""
    echo -e "${GREEN}For detailed instructions, see: FILEBEAT_INTEGRATION_GUIDE.md${NC}"
}

main() {
    print_header
    
    check_root
    check_system
    install_filebeat
    setup_permissions
    create_integration_script
    
    print_success "ForgedFate Filebeat setup completed successfully!"
    echo ""
    show_next_steps
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "ForgedFate Filebeat Setup Script"
        echo ""
        echo "Usage: $0 [options]"
        echo ""
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --version      Show Filebeat version to install"
        echo ""
        echo "This script will:"
        echo "  1. Install Filebeat $FILEBEAT_VERSION"
        echo "  2. Set up permissions for Kismet log access"
        echo "  3. Install the ForgedFate integration script"
        echo "  4. Provide next steps for configuration"
        echo ""
        exit 0
        ;;
    --version)
        echo "Filebeat version: $FILEBEAT_VERSION"
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac
