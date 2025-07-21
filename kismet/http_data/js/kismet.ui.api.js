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
        }));
        
        form.append(createFormField('Server Port', 'number', config.server_port, function(val) {
            config.server_port = parseInt(val);
            saveConfigs();
            updateCommandDisplay(export_type);
        }));
        
        form.append(createSelectField('Data Format', ['json', 'csv', 'simple'], config.data_format, function(val) {
            config.data_format = val;
            saveConfigs();
            updateCommandDisplay(export_type);
        }));
        
        form.append(createFormField('Update Rate (seconds)', 'number', config.update_rate, function(val) {
            config.update_rate = parseInt(val);
            saveConfigs();
            updateCommandDisplay(export_type);
        }));
    }
    
    if (export_type === 'elasticsearch') {
        form.append(createFormField('Elasticsearch Hosts', 'text', config.hosts, function(val) {
            config.hosts = val;
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
        
        form.append(createFormField('Index Prefix', 'text', config.index_prefix, function(val) {
            config.index_prefix = val;
            saveConfigs();
            updateCommandDisplay(export_type);
        }));
        
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

// Create form field helper
function createFormField(label, type, value, callback) {
    return $('<div>', {
        class: 'k-api-form-field'
    })
    .append(
        $('<label>')
        .text(label)
    )
    .append(
        $('<input>', {
            type: type,
            value: value,
            class: 'k-api-input'
        })
        .on('input', function() {
            callback($(this).val());
        })
    );
}

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
    }).resize({
        width: w,
        height: h
    }).reposition({
        my: 'center',
        at: 'center',
        of: 'window',
    });
};

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
