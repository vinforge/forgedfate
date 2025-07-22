(
  typeof define === "function" ? function (m) { define("kismet-ui-api-js", m); } :
  typeof exports === "object" ? function (m) { module.exports = m(); } :
  function(m){ this.kismet_ui_api = m(); }
)(function () {

"use strict";

var exports = {};

var local_uri_prefix = ""; 
if (typeof(KISMET_URI_PREFIX) !== 'undefined')
    local_uri_prefix = KISMET_URI_PREFIX;

// Flag we're still loading
exports.load_complete = 0;

// Load our css
$('<link>')
    .appendTo('head')
    .attr({
        type: 'text/css', 
        rel: 'stylesheet',
        href: local_uri_prefix + 'css/kismet.ui.api.css'
    });

var api_panel = null;

// Connectivity monitoring state
var connectivity_monitoring = {
    enabled: false,
    interval: 30000, // 30 seconds
    timer_id: null,
    last_test_results: {}
};

// Export configuration storage
var export_configs = {
    tcp: {
        enabled: false,
        server_host: '172.18.18.20',
        server_port: 8685,
        data_format: 'json',
        update_rate: 5
    },
    udp: {
        enabled: false,
        server_host: '172.18.18.20',
        server_port: 8685,
        data_format: 'json',
        update_rate: 5
    },
    elasticsearch: {
        enabled: false,
        hosts: 'http://localhost:9200',
        username: '',
        password: '',
        index_prefix: 'kismet',
        offline_mode: false
    },
    mqtt: {
        enabled: false,
        broker_host: 'localhost',
        broker_port: 1883,
        topic_prefix: 'kismet',
        username: '',
        password: ''
    }
};

// Load configurations from localStorage
function loadConfigs() {
    var stored = kismet.getStorage('kismet.api.export_configs', null);
    if (stored !== null) {
        export_configs = $.extend(true, export_configs, stored);
    }
}

// Save configurations to localStorage
function saveConfigs() {
    kismet.putStorage('kismet.api.export_configs', export_configs);
}

// Generate command line for export type
function generateCommand(export_type) {
    var config = export_configs[export_type];
    var cmd = 'python kismet_realtime_export.py';
    
    switch(export_type) {
        case 'tcp':
        case 'udp':
            cmd += ` --export-type ${export_type}`;
            cmd += ` --server-host ${config.server_host}`;
            cmd += ` --server-port ${config.server_port}`;
            cmd += ` --data-format ${config.data_format}`;
            cmd += ` --update-rate ${config.update_rate}`;
            break;
            
        case 'elasticsearch':
            cmd = 'python kismet_elasticsearch_export.py';
            cmd += ` --es-hosts "${config.hosts}"`;
            if (config.username) cmd += ` --es-username ${config.username}`;
            if (config.password) cmd += ` --es-password ${config.password}`;
            cmd += ` --index-prefix ${config.index_prefix}`;
            if (config.offline_mode) cmd += ' --offline';
            break;
            
        case 'mqtt':
            cmd += ' --export-type mqtt';
            cmd += ` --mqtt-host ${config.broker_host}`;
            cmd += ` --mqtt-port ${config.broker_port}`;
            cmd += ` --mqtt-topic-prefix ${config.topic_prefix}`;
            if (config.username) cmd += ` --mqtt-username ${config.username}`;
            if (config.password) cmd += ` --mqtt-password ${config.password}`;
            break;
    }
    
    return cmd;
}

// Create configuration panel for export type
function createExportPanel(export_type, container) {
    var config = export_configs[export_type];
    var title = export_type.toUpperCase();
    
    var panel = $('<div>', {
        class: 'k-api-export-panel',
        id: `api-panel-${export_type}`
    });
    
    // Header with enable/disable toggle
    var header = $('<div>', {
        class: 'k-api-panel-header'
    })
    .append(
        $('<h3>')
        .html(`<i class="fa fa-plug"></i> ${title} Export`)
    )
    .append(
        $('<label>', {
            class: 'k-api-toggle'
        })
        .append(
            $('<input>', {
                type: 'checkbox',
                id: `enable-${export_type}`,
                checked: config.enabled
            })
            .on('change', function() {
                config.enabled = $(this).is(':checked');
                saveConfigs();
                updateCommandDisplay(export_type);
            })
        )
        .append(
            $('<span>', {
                class: 'k-api-toggle-slider'
            })
        )
        .append(' Enable')
    );
    
    panel.append(header);
    
    // Configuration fields
    var form = $('<div>', {
        class: 'k-api-form'
    });
    
    if (export_type === 'tcp' || export_type === 'udp') {
        form.append(createFormField('Server Host', 'text', config.server_host, function(val) {
            config.server_host = val;
            saveConfigs();
            updateCommandDisplay(export_type);
            validateAndShowFeedback(export_type);
        }, 'IP address or hostname of the target server'));

        form.append(createFormField('Server Port', 'number', config.server_port, function(val) {
            config.server_port = parseInt(val);
            saveConfigs();
            updateCommandDisplay(export_type);
            validateAndShowFeedback(export_type);
        }, 'Port number (1-65535) where the server is listening'));

        form.append(createSelectField('Data Format', ['json', 'csv', 'simple'], config.data_format, function(val) {
            config.data_format = val;
            saveConfigs();
            updateCommandDisplay(export_type);
        }));

        form.append(createFormField('Update Rate (seconds)', 'number', config.update_rate, function(val) {
            config.update_rate = parseInt(val);
            saveConfigs();
            updateCommandDisplay(export_type);
        }, 'How often to send data updates (1-3600 seconds)'));
    }
    
    if (export_type === 'elasticsearch') {
        form.append(createFormField('Elasticsearch Hosts', 'text', config.hosts, function(val) {
            config.hosts = val;
            saveConfigs();
            updateCommandDisplay(export_type);
            validateAndShowFeedback(export_type);
        }, 'Full URL including protocol (e.g., http://localhost:9200)'));

        form.append(createFormField('Username (optional)', 'text', config.username, function(val) {
            config.username = val;
            saveConfigs();
            updateCommandDisplay(export_type);
        }, 'Username for Elasticsearch authentication (leave empty if not required)'));

        form.append(createFormField('Password (optional)', 'password', config.password, function(val) {
            config.password = val;
            saveConfigs();
            updateCommandDisplay(export_type);
        }, 'Password for Elasticsearch authentication'));

        form.append(createFormField('Index Prefix', 'text', config.index_prefix, function(val) {
            config.index_prefix = val;
            saveConfigs();
            updateCommandDisplay(export_type);
        }, 'Prefix for Elasticsearch index names (e.g., "kismet" creates "kismet-devices")'));
        
        form.append(
            $('<label>')
            .append(
                $('<input>', {
                    type: 'checkbox',
                    checked: config.offline_mode
                })
                .on('change', function() {
                    config.offline_mode = $(this).is(':checked');
                    saveConfigs();
                    updateCommandDisplay(export_type);
                })
            )
            .append(' Offline Mode')
        );
    }
    
    if (export_type === 'mqtt') {
        form.append(createFormField('Broker Host', 'text', config.broker_host, function(val) {
            config.broker_host = val;
            saveConfigs();
            updateCommandDisplay(export_type);
        }));
        
        form.append(createFormField('Broker Port', 'number', config.broker_port, function(val) {
            config.broker_port = parseInt(val);
            saveConfigs();
            updateCommandDisplay(export_type);
        }));
        
        form.append(createFormField('Topic Prefix', 'text', config.topic_prefix, function(val) {
            config.topic_prefix = val;
            saveConfigs();
            updateCommandDisplay(export_type);
        }));
        
        form.append(createFormField('Username (optional)', 'text', config.username, function(val) {
            config.username = val;
            saveConfigs();
            updateCommandDisplay(export_type);
        }));
        
        form.append(createFormField('Password (optional)', 'password', config.password, function(val) {
            config.password = val;
            saveConfigs();
            updateCommandDisplay(export_type);
        }));
    }
    
    panel.append(form);

    // Add context-sensitive help
    var helpSection = createHelpSection(export_type);
    panel.append(helpSection);

    // Command display
    var cmdPanel = $('<div>', {
        class: 'k-api-command-panel'
    })
    .append(
        $('<h4>')
        .html('<i class="fa fa-terminal"></i> Generated Command')
    )
    .append(
        $('<div>', {
            class: 'k-api-command',
            id: `command-${export_type}`
        })
        .html(generateCommand(export_type))
    )
    .append(
        $('<button>', {
            class: 'k-api-copy-btn'
        })
        .html('<i class="fa fa-copy"></i> Copy Command')
        .on('click', function() {
            var cmd = $(`#command-${export_type}`).text();
            navigator.clipboard.writeText(cmd).then(function() {
                $(this).html('<i class="fa fa-check"></i> Copied!');
                setTimeout(() => {
                    $(this).html('<i class="fa fa-copy"></i> Copy Command');
                }, 2000);
            }.bind(this));
        })
    );
    
    panel.append(cmdPanel);

    // Connectivity testing panel
    var connectivityPanel = createConnectivityTestPanel(export_type);
    panel.append(connectivityPanel);

    container.append(panel);

    updateCommandDisplay(export_type);
}

// Update command display
function updateCommandDisplay(export_type) {
    var cmd = generateCommand(export_type);
    $(`#command-${export_type}`).html(cmd);
    
    // Enable/disable panel based on configuration
    var panel = $(`#api-panel-${export_type}`);
    if (export_configs[export_type].enabled) {
        panel.removeClass('k-api-panel-disabled');
    } else {
        panel.addClass('k-api-panel-disabled');
    }
}

// Configuration validation
function validateConfiguration(export_type, config) {
    var errors = [];
    var warnings = [];

    switch(export_type) {
        case 'tcp':
        case 'udp':
            if (!config.server_host || config.server_host.trim() === '') {
                errors.push('Server host is required');
            }
            if (!config.server_port || config.server_port < 1 || config.server_port > 65535) {
                errors.push('Valid port number (1-65535) is required');
            }
            if (config.server_port && (config.server_port < 1024)) {
                warnings.push('Port numbers below 1024 may require elevated privileges');
            }
            break;

        case 'elasticsearch':
            if (!config.hosts || config.hosts.trim() === '') {
                errors.push('Elasticsearch URL is required');
            } else if (!config.hosts.match(/^https?:\/\//)) {
                warnings.push('URL should start with http:// or https://');
            }
            break;

        case 'mqtt':
            if (!config.broker_host || config.broker_host.trim() === '') {
                errors.push('MQTT broker host is required');
            }
            if (!config.broker_port || config.broker_port < 1 || config.broker_port > 65535) {
                errors.push('Valid port number (1-65535) is required');
            }
            if (config.broker_port && config.broker_port !== 1883 && config.broker_port !== 8883) {
                warnings.push('Standard MQTT ports are 1883 (unencrypted) and 8883 (SSL)');
            }
            break;
    }

    return { errors: errors, warnings: warnings };
}

function showValidationFeedback(export_type, validation) {
    var panel = $(`#api-panel-${export_type}`);
    var existingFeedback = panel.find('.k-api-validation-feedback');
    existingFeedback.remove();

    if (validation.errors.length === 0 && validation.warnings.length === 0) {
        return;
    }

    var feedbackDiv = $('<div>', {
        class: 'k-api-validation-feedback'
    });

    if (validation.errors.length > 0) {
        var errorDiv = $('<div>', {
            class: 'k-api-validation-errors'
        })
        .append($('<h5>').html('<i class="fa fa-exclamation-circle"></i> Configuration Errors:'))
        .append($('<ul>'));

        validation.errors.forEach(function(error) {
            errorDiv.find('ul').append($('<li>').text(error));
        });

        feedbackDiv.append(errorDiv);
    }

    if (validation.warnings.length > 0) {
        var warningDiv = $('<div>', {
            class: 'k-api-validation-warnings'
        })
        .append($('<h5>').html('<i class="fa fa-exclamation-triangle"></i> Configuration Warnings:'))
        .append($('<ul>'));

        validation.warnings.forEach(function(warning) {
            warningDiv.find('ul').append($('<li>').text(warning));
        });

        feedbackDiv.append(warningDiv);
    }

    panel.find('.k-api-form').after(feedbackDiv);
}

function validateAndShowFeedback(export_type) {
    var config = export_configs[export_type];
    var validation = validateConfiguration(export_type, config);
    showValidationFeedback(export_type, validation);
}

// Create form field helper with validation
function createFormField(label, type, value, callback, tooltip) {
    var fieldDiv = $('<div>', {
        class: 'k-api-form-field'
    });

    var labelElement = $('<label>')
        .text(label);

    if (tooltip) {
        labelElement.append(
            $('<i>', {
                class: 'fa fa-question-circle k-api-tooltip',
                title: tooltip
            })
        );
    }

    fieldDiv.append(labelElement);

    return fieldDiv.append(
        $('<input>', {
            class: 'k-api-input',
            type: type,
            value: value
        })
        .on('input change', function() {
            callback($(this).val());
        })
    );
}

// Create help section for each export type
function createHelpSection(export_type) {
    var helpContent = '';
    var helpTitle = '';

    switch(export_type) {
        case 'tcp':
            helpTitle = 'TCP Export Help';
            helpContent = 'TCP provides reliable, ordered data delivery with automatic reconnection. ' +
                         'Best for critical data that must not be lost. Common ports: 80 (HTTP), 443 (HTTPS), 8080, 9200.';
            break;

        case 'udp':
            helpTitle = 'UDP Export Help';
            helpContent = 'UDP provides fast, low-latency data transmission without delivery guarantees. ' +
                         'Best for real-time monitoring where speed is more important than reliability. ' +
                         'Note: Some firewalls may block UDP traffic.';
            break;

        case 'elasticsearch':
            helpTitle = 'Elasticsearch Export Help';
            helpContent = 'Elasticsearch provides powerful search and analytics capabilities. ' +
                         'Supports offline mode for disconnected operation. ' +
                         'URL format: http://host:port or https://host:port. Default port: 9200.';
            break;

        case 'mqtt':
            helpTitle = 'MQTT Export Help';
            helpContent = 'MQTT is a lightweight messaging protocol ideal for IoT applications. ' +
                         'Standard ports: 1883 (unencrypted), 8883 (SSL/TLS). ' +
                         'Supports QoS levels and retained messages.';
            break;
    }

    return $('<div>', {
        class: 'k-api-help-section'
    })
    .append(
        $('<h4>')
        .html(`<i class="fa fa-info-circle"></i> ${helpTitle}`)
    )
    .append(
        $('<p>')
        .text(helpContent)
    );
}

// Complete the form field creation
// Form field creation is handled in the createFormField function above

// Create select field helper
function createSelectField(label, options, value, callback) {
    var select = $('<select>', {
        class: 'k-api-select'
    })
    .on('change', function() {
        callback($(this).val());
    });
    
    options.forEach(function(option) {
        select.append(
            $('<option>', {
                value: option,
                selected: option === value
            })
            .text(option)
        );
    });
    
    return $('<div>', {
        class: 'k-api-form-field'
    })
    .append(
        $('<label>')
        .text(label)
    )
    .append(select);
}

// Show API configuration panel
exports.ShowAPI = function() {
    loadConfigs();
    
    var w = $(window).width() * 0.85;
    var h = $(window).height() * 0.85;

    if (w < 600 || h < 500) {
        w = $(window).width() - 10;
        h = $(window).height() - 10;
    }

    var content = $('<div>', {
        class: 'k-api-container'
    })
    .append(
        $('<div>', {
            class: 'k-api-header'
        })
        .append(
            $('<h2>')
            .html('<i class="fa fa-cogs"></i> ForgedFate API Export Configuration')
        )
        .append(
            $('<p>')
            .html('Configure real-time data export to external systems. Enable the export types you need and configure their settings.')
        )
    );
    
    var panels = $('<div>', {
        class: 'k-api-panels'
    });
    
    // Create panels for each export type
    createExportPanel('tcp', panels);
    createExportPanel('udp', panels);
    createExportPanel('elasticsearch', panels);
    createExportPanel('mqtt', panels);
    
    content.append(panels);

    // Add monitoring controls
    addMonitoringControls(content);

    // Add quick start guide
    content.append(
        $('<div>', {
            class: 'k-api-quick-start'
        })
        .append(
            $('<h4>')
            .html('<i class="fa fa-rocket"></i> Quick Start Guide')
        )
        .append(
            $('<ol>')
            .html('<li>Choose an export type and enable it using the toggle switch</li>' +
                  '<li>Configure the connection settings (host, port, credentials)</li>' +
                  '<li>Click "Test Connection" to verify your configuration</li>' +
                  '<li>Copy the generated command and run it in your terminal</li>' +
                  '<li>Use "Start Monitoring" to track connection health in real-time</li>')
        )
    );

    // Add documentation section
    content.append(
        $('<div>', {
            class: 'k-api-docs'
        })
        .append(
            $('<h3>')
            .html('<i class="fa fa-book"></i> Documentation')
        )
        .append(
            $('<p>')
            .html('For detailed usage instructions, see the <strong>TCP_UDP_EXPORT_GUIDE.md</strong> file in the Kismet directory.')
        )
        .append(
            $('<p>')
            .html('<strong>TCP:</strong> Reliable data transmission with automatic reconnection<br>' +
                  '<strong>UDP:</strong> High-speed data transmission for real-time monitoring<br>' +
                  '<strong>Elasticsearch:</strong> Search and analytics with offline support<br>' +
                  '<strong>MQTT:</strong> Message broker integration for IoT systems')
        )
    );

    api_panel = $.jsPanel({
        id: 'api-config',
        headerTitle: '<i class="fa fa-cogs"></i> API Export Configuration',
        paneltype: 'modal',
        headerControls: {
            controls: 'closeonly',
            iconfont: 'jsglyph',
        },
        content: content,
        callback: function() {
            // Initialize tooltips
            $('.k-api-tooltip').each(function() {
                $(this).attr('data-toggle', 'tooltip');
            });

            // Perform initial validation for all enabled exports
            for (var exportType in export_configs) {
                if (export_configs[exportType].enabled) {
                    validateAndShowFeedback(exportType);
                }
            }
        }
    }).resize({
        width: w,
        height: h
    }).reposition({
        my: 'center',
        at: 'center',
        of: 'window',
    });
};

// Connectivity testing functionality
function createConnectivityTestPanel(export_type) {
    var panel = $('<div>', {
        class: 'k-api-connectivity-panel'
    })
    .append(
        $('<h4>')
        .html('<i class="fa fa-wifi"></i> Connection Test')
    );

    var statusContainer = $('<div>', {
        class: 'k-api-connectivity-status',
        id: `connectivity-status-${export_type}`
    })
    .append(
        $('<div>', {
            class: 'k-api-status-indicator',
            id: `status-indicator-${export_type}`
        })
        .html('<i class="fa fa-question-circle"></i> Not tested')
    );

    var testButton = $('<button>', {
        class: 'k-api-test-btn',
        id: `test-btn-${export_type}`
    })
    .html('<i class="fa fa-play"></i> Test Connection')
    .on('click', function() {
        testConnectivity(export_type);
    });

    var resultsContainer = $('<div>', {
        class: 'k-api-test-results',
        id: `test-results-${export_type}`,
        style: 'display: none;'
    });

    panel.append(statusContainer);
    panel.append(testButton);
    panel.append(resultsContainer);

    return panel;
}

function testConnectivity(export_type) {
    var config = export_configs[export_type];
    var testBtn = $(`#test-btn-${export_type}`);
    var statusIndicator = $(`#status-indicator-${export_type}`);
    var resultsContainer = $(`#test-results-${export_type}`);

    // Update UI to show testing state
    testBtn.prop('disabled', true).html('<i class="fa fa-spinner fa-spin"></i> Testing...');
    statusIndicator.html('<i class="fa fa-spinner fa-spin"></i> Testing connection...');
    resultsContainer.hide();

    var testData = {};
    var endpoint = '';

    // Prepare test data based on export type
    switch(export_type) {
        case 'tcp':
        case 'udp':
            testData = {
                host: config.server_host,
                port: config.server_port,
                timeout: 10
            };
            endpoint = `/api/v1/connectivity/test/${export_type}`;
            break;

        case 'elasticsearch':
            testData = {
                url: config.hosts,
                username: config.username || '',
                password: config.password || '',
                timeout: 10
            };
            endpoint = '/api/v1/connectivity/test/elasticsearch';
            break;

        case 'mqtt':
            testData = {
                host: config.broker_host,
                port: config.broker_port,
                username: config.username || '',
                password: config.password || '',
                timeout: 10
            };
            endpoint = '/api/v1/connectivity/test/mqtt';
            break;
    }

    // Make the test request
    $.ajax({
        url: endpoint,
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(testData),
        timeout: 15000,
        success: function(response) {
            displayTestResults(export_type, response);
        },
        error: function(xhr, status, error) {
            var errorResponse = {
                status: 'error',
                errors: [`Request failed: ${error}`],
                suggestions: ['Check if Kismet server is running', 'Verify network connectivity']
            };
            displayTestResults(export_type, errorResponse);
        },
        complete: function() {
            testBtn.prop('disabled', false).html('<i class="fa fa-play"></i> Test Connection');
        }
    });
}

function displayTestResults(export_type, results) {
    var statusIndicator = $(`#status-indicator-${export_type}`);
    var resultsContainer = $(`#test-results-${export_type}`);

    // Update status indicator
    var statusClass = '';
    var statusIcon = '';
    var statusText = '';

    switch(results.status) {
        case 'success':
            statusClass = 'k-api-status-success';
            statusIcon = 'fa-check-circle';
            statusText = 'Connection successful';
            break;
        case 'warning':
            statusClass = 'k-api-status-warning';
            statusIcon = 'fa-exclamation-triangle';
            statusText = 'Connection warning';
            break;
        case 'error':
        case 'timeout':
            statusClass = 'k-api-status-error';
            statusIcon = 'fa-times-circle';
            statusText = 'Connection failed';
            break;
        default:
            statusClass = 'k-api-status-unknown';
            statusIcon = 'fa-question-circle';
            statusText = 'Unknown status';
    }

    statusIndicator.removeClass('k-api-status-success k-api-status-warning k-api-status-error k-api-status-unknown')
                   .addClass(statusClass)
                   .html(`<i class="fa ${statusIcon}"></i> ${statusText}`);

    // Build detailed results
    var resultsHtml = '<div class="k-api-test-details">';

    // Response time
    if (results.response_time_ms !== undefined) {
        resultsHtml += `<div class="k-api-detail-item">
            <strong>Response Time:</strong> ${results.response_time_ms}ms
        </div>`;
    }

    // Details
    if (results.details && Object.keys(results.details).length > 0) {
        resultsHtml += '<div class="k-api-detail-section"><strong>Details:</strong><ul>';
        for (var key in results.details) {
            resultsHtml += `<li><strong>${key}:</strong> ${results.details[key]}</li>`;
        }
        resultsHtml += '</ul></div>';
    }

    // Errors
    if (results.errors && results.errors.length > 0) {
        resultsHtml += '<div class="k-api-error-section"><strong>Errors:</strong><ul>';
        results.errors.forEach(function(error) {
            resultsHtml += `<li class="k-api-error">${error}</li>`;
        });
        resultsHtml += '</ul></div>';
    }

    // Suggestions
    if (results.suggestions && results.suggestions.length > 0) {
        resultsHtml += '<div class="k-api-suggestion-section"><strong>Suggestions:</strong><ul>';
        results.suggestions.forEach(function(suggestion) {
            resultsHtml += `<li class="k-api-suggestion">${suggestion}</li>`;
        });
        resultsHtml += '</ul></div>';
    }

    resultsHtml += '</div>';

    resultsContainer.html(resultsHtml).show();
}

// Real-time connectivity monitoring
function startConnectivityMonitoring() {
    if (connectivity_monitoring.enabled) {
        return; // Already running
    }

    connectivity_monitoring.enabled = true;

    function runMonitoringCycle() {
        // Test all enabled export configurations
        for (var export_type in export_configs) {
            if (export_configs[export_type].enabled) {
                testConnectivitySilent(export_type);
            }
        }

        // Schedule next cycle
        if (connectivity_monitoring.enabled) {
            connectivity_monitoring.timer_id = setTimeout(runMonitoringCycle, connectivity_monitoring.interval);
        }
    }

    // Start first cycle after a short delay
    connectivity_monitoring.timer_id = setTimeout(runMonitoringCycle, 5000);
}

function stopConnectivityMonitoring() {
    connectivity_monitoring.enabled = false;
    if (connectivity_monitoring.timer_id) {
        clearTimeout(connectivity_monitoring.timer_id);
        connectivity_monitoring.timer_id = null;
    }
}

function testConnectivitySilent(export_type) {
    var config = export_configs[export_type];

    var testData = {};
    var endpoint = '';

    // Prepare test data based on export type
    switch(export_type) {
        case 'tcp':
        case 'udp':
            testData = {
                host: config.server_host,
                port: config.server_port,
                timeout: 5 // Shorter timeout for background monitoring
            };
            endpoint = `/api/v1/connectivity/test/${export_type}`;
            break;

        case 'elasticsearch':
            testData = {
                url: config.hosts,
                username: config.username || '',
                password: config.password || '',
                timeout: 5
            };
            endpoint = '/api/v1/connectivity/test/elasticsearch';
            break;

        case 'mqtt':
            testData = {
                host: config.broker_host,
                port: config.broker_port,
                username: config.username || '',
                password: config.password || '',
                timeout: 5
            };
            endpoint = '/api/v1/connectivity/test/mqtt';
            break;
    }

    // Make the test request silently
    $.ajax({
        url: endpoint,
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(testData),
        timeout: 8000,
        success: function(response) {
            updateBackgroundStatus(export_type, response);
            connectivity_monitoring.last_test_results[export_type] = response;
        },
        error: function(xhr, status, error) {
            var errorResponse = {
                status: 'error',
                errors: [`Background test failed: ${error}`],
                timestamp: Date.now()
            };
            updateBackgroundStatus(export_type, errorResponse);
            connectivity_monitoring.last_test_results[export_type] = errorResponse;
        }
    });
}

function updateBackgroundStatus(export_type, results) {
    var statusIndicator = $(`#status-indicator-${export_type}`);

    if (statusIndicator.length === 0) {
        return; // Panel not visible
    }

    // Only update if this is a background test (not user-initiated)
    var currentText = statusIndicator.text();
    if (currentText.includes('Testing') || currentText.includes('Not tested')) {
        return; // Don't override active user test or initial state
    }

    var statusClass = '';
    var statusIcon = '';
    var statusText = '';

    switch(results.status) {
        case 'success':
            statusClass = 'k-api-status-success';
            statusIcon = 'fa-check-circle';
            statusText = 'Connected';
            break;
        case 'warning':
            statusClass = 'k-api-status-warning';
            statusIcon = 'fa-exclamation-triangle';
            statusText = 'Connection issues';
            break;
        case 'error':
        case 'timeout':
            statusClass = 'k-api-status-error';
            statusIcon = 'fa-times-circle';
            statusText = 'Disconnected';
            break;
        default:
            return; // Don't update for unknown status
    }

    statusIndicator.removeClass('k-api-status-success k-api-status-warning k-api-status-error k-api-status-unknown')
                   .addClass(statusClass)
                   .html(`<i class="fa ${statusIcon}"></i> ${statusText} (auto)`);
}

// Add monitoring controls to the main API panel
function addMonitoringControls(container) {
    var monitoringPanel = $('<div>', {
        class: 'k-api-monitoring-panel'
    })
    .append(
        $('<h3>')
        .html('<i class="fa fa-heartbeat"></i> Real-time Monitoring')
    )
    .append(
        $('<p>')
        .html('Automatically test connections every 30 seconds for enabled exports.')
    );

    var controlsDiv = $('<div>', {
        class: 'k-api-monitoring-controls'
    });

    var startBtn = $('<button>', {
        class: 'k-api-monitor-btn k-api-monitor-start',
        id: 'start-monitoring-btn'
    })
    .html('<i class="fa fa-play"></i> Start Monitoring')
    .on('click', function() {
        startConnectivityMonitoring();
        updateMonitoringUI();
    });

    var stopBtn = $('<button>', {
        class: 'k-api-monitor-btn k-api-monitor-stop',
        id: 'stop-monitoring-btn',
        style: 'display: none;'
    })
    .html('<i class="fa fa-stop"></i> Stop Monitoring')
    .on('click', function() {
        stopConnectivityMonitoring();
        updateMonitoringUI();
    });

    var statusDiv = $('<div>', {
        class: 'k-api-monitoring-status',
        id: 'monitoring-status'
    })
    .html('<i class="fa fa-circle-o"></i> Monitoring disabled');

    var diagnosticsBtn = $('<button>', {
        class: 'k-api-monitor-btn k-api-diagnostics-btn'
    })
    .html('<i class="fa fa-stethoscope"></i> Generate Diagnostic Report')
    .on('click', function() {
        showDiagnosticReport();
    });

    controlsDiv.append(startBtn).append(stopBtn).append(diagnosticsBtn).append(statusDiv);
    monitoringPanel.append(controlsDiv);

    container.append(monitoringPanel);
}

function updateMonitoringUI() {
    var startBtn = $('#start-monitoring-btn');
    var stopBtn = $('#stop-monitoring-btn');
    var statusDiv = $('#monitoring-status');

    if (connectivity_monitoring.enabled) {
        startBtn.hide();
        stopBtn.show();
        statusDiv.html('<i class="fa fa-circle" style="color: #28a745;"></i> Monitoring active');
    } else {
        startBtn.show();
        stopBtn.hide();
        statusDiv.html('<i class="fa fa-circle-o"></i> Monitoring disabled');
    }
}

// Diagnostic reporting
function showDiagnosticReport() {
    var diagnosticPanel = $.jsPanel({
        id: 'diagnostic-report',
        headerTitle: '<i class="fa fa-stethoscope"></i> Connectivity Diagnostic Report',
        paneltype: 'modal',
        headerControls: {
            controls: 'closeonly',
            iconfont: 'jsglyph',
        },
        contentSize: {
            width: Math.min($(window).width() * 0.9, 1000),
            height: Math.min($(window).height() * 0.8, 700)
        },
        content: '<div class="k-api-diagnostic-loading"><i class="fa fa-spinner fa-spin"></i> Generating diagnostic report...</div>',
        callback: function() {
            generateDiagnosticReport();
        }
    });
}

function generateDiagnosticReport() {
    $.ajax({
        url: '/api/v1/connectivity/diagnostics/report',
        method: 'GET',
        timeout: 10000,
        success: function(report) {
            displayDiagnosticReport(report);
        },
        error: function(xhr, status, error) {
            var errorHtml = `
                <div class="k-api-diagnostic-error">
                    <h3><i class="fa fa-exclamation-triangle"></i> Error Generating Report</h3>
                    <p>Failed to generate diagnostic report: ${error}</p>
                    <p>Please check that Kismet server is running and try again.</p>
                </div>
            `;
            $('#diagnostic-report .jsPanel-content').html(errorHtml);
        }
    });
}

function displayDiagnosticReport(report) {
    var html = '<div class="k-api-diagnostic-report">';

    // Header
    html += `
        <div class="k-api-diagnostic-header">
            <h2><i class="fa fa-stethoscope"></i> Connectivity Diagnostic Report</h2>
            <p>Generated: ${new Date(report.timestamp * 1000).toLocaleString()}</p>
            <p>Report Type: ${report.report_type}</p>
        </div>
    `;

    // System Information
    if (report.system_info) {
        html += '<div class="k-api-diagnostic-section">';
        html += '<h3><i class="fa fa-server"></i> System Information</h3>';
        html += '<ul>';
        for (var key in report.system_info) {
            html += `<li><strong>${key}:</strong> ${report.system_info[key]}</li>`;
        }
        html += '</ul></div>';
    }

    // Network Diagnostics
    if (report.network_diagnostics) {
        html += '<div class="k-api-diagnostic-section">';
        html += '<h3><i class="fa fa-network-wired"></i> Network Diagnostics</h3>';
        html += '<ul>';
        for (var key in report.network_diagnostics) {
            var value = report.network_diagnostics[key];
            var statusClass = value === 'available' ? 'success' : value === 'unknown' ? 'warning' : 'error';
            html += `<li><strong>${key}:</strong> <span class="k-api-status-${statusClass}">${value}</span></li>`;
        }
        html += '</ul></div>';
    }

    // Export-specific diagnostics
    var exportTypes = ['tcp_diagnostics', 'udp_diagnostics', 'elasticsearch_diagnostics', 'mqtt_diagnostics'];
    exportTypes.forEach(function(exportType) {
        if (report[exportType]) {
            var title = exportType.replace('_diagnostics', '').toUpperCase();
            html += `<div class="k-api-diagnostic-section">`;
            html += `<h3><i class="fa fa-plug"></i> ${title} Diagnostics</h3>`;
            html += '<ul>';
            for (var key in report[exportType]) {
                var value = report[exportType][key];
                if (Array.isArray(value)) {
                    html += `<li><strong>${key}:</strong> ${value.join(', ')}</li>`;
                } else {
                    html += `<li><strong>${key}:</strong> ${value}</li>`;
                }
            }
            html += '</ul></div>';
        }
    });

    // Troubleshooting Guide
    if (report.troubleshooting_guide) {
        html += '<div class="k-api-diagnostic-section">';
        html += '<h3><i class="fa fa-question-circle"></i> Troubleshooting Guide</h3>';
        for (var issue in report.troubleshooting_guide) {
            html += `<div class="k-api-troubleshooting-item">`;
            html += `<h4>${issue.replace(/_/g, ' ').toUpperCase()}</h4>`;
            html += '<ul>';
            report.troubleshooting_guide[issue].forEach(function(suggestion) {
                html += `<li>${suggestion}</li>`;
            });
            html += '</ul></div>';
        }
        html += '</div>';
    }

    // Current Test Results
    if (Object.keys(connectivity_monitoring.last_test_results).length > 0) {
        html += '<div class="k-api-diagnostic-section">';
        html += '<h3><i class="fa fa-history"></i> Recent Test Results</h3>';
        for (var exportType in connectivity_monitoring.last_test_results) {
            var result = connectivity_monitoring.last_test_results[exportType];
            html += `<div class="k-api-test-result-summary">`;
            html += `<h4>${exportType.toUpperCase()}</h4>`;
            html += `<p><strong>Status:</strong> <span class="k-api-status-${result.status}">${result.status}</span></p>`;
            if (result.response_time_ms) {
                html += `<p><strong>Response Time:</strong> ${result.response_time_ms}ms</p>`;
            }
            if (result.errors && result.errors.length > 0) {
                html += `<p><strong>Errors:</strong> ${result.errors.join(', ')}</p>`;
            }
            html += '</div>';
        }
        html += '</div>';
    }

    // Export button
    html += `
        <div class="k-api-diagnostic-actions">
            <button class="k-api-export-btn" onclick="exportDiagnosticReport()">
                <i class="fa fa-download"></i> Export Report
            </button>
        </div>
    `;

    html += '</div>';

    $('#diagnostic-report .jsPanel-content').html(html);
}

function exportDiagnosticReport() {
    // Create a downloadable text version of the report
    var reportText = "KISMET CONNECTIVITY DIAGNOSTIC REPORT\n";
    reportText += "=====================================\n\n";
    reportText += "Generated: " + new Date().toLocaleString() + "\n\n";

    // Add current configuration
    reportText += "CURRENT EXPORT CONFIGURATIONS:\n";
    for (var exportType in export_configs) {
        var config = export_configs[exportType];
        reportText += `\n${exportType.toUpperCase()}:\n`;
        reportText += `  Enabled: ${config.enabled}\n`;
        for (var key in config) {
            if (key !== 'enabled') {
                reportText += `  ${key}: ${config[key]}\n`;
            }
        }
    }

    // Add test results
    if (Object.keys(connectivity_monitoring.last_test_results).length > 0) {
        reportText += "\nRECENT TEST RESULTS:\n";
        for (var exportType in connectivity_monitoring.last_test_results) {
            var result = connectivity_monitoring.last_test_results[exportType];
            reportText += `\n${exportType.toUpperCase()}:\n`;
            reportText += `  Status: ${result.status}\n`;
            if (result.response_time_ms) {
                reportText += `  Response Time: ${result.response_time_ms}ms\n`;
            }
            if (result.errors && result.errors.length > 0) {
                reportText += `  Errors: ${result.errors.join(', ')}\n`;
            }
        }
    }

    // Create and download file
    var blob = new Blob([reportText], { type: 'text/plain' });
    var url = window.URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = 'kismet-connectivity-diagnostic-' + new Date().toISOString().slice(0,19).replace(/:/g, '-') + '.txt';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
}

/* Add the API sidebar item */
kismet_ui_sidebar.AddSidebarItem({
    id: 'sidebar-api',
    listTitle: '<i class="fa fa-cogs"></i> API',
    priority: -50000,
    clickCallback: function() {
        exports.ShowAPI();
    }
});

// We're done loading
exports.load_complete = 1;

return exports;

});
