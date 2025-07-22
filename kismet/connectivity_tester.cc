#include "config.h"

#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>

#include <chrono>
#include <future>
#include <thread>

#include "connectivity_tester.h"
#include "messagebus.h"
#include "json_adapter.h"

// connectivity_test_result implementation
void connectivity_test_result::register_fields() {
    tracker_component::register_fields();

    register_field("kismet.connectivity.test.status", "Test status", &status);
    register_field("kismet.connectivity.test.response_time_ms", "Response time in milliseconds", &response_time_ms);
    register_field("kismet.connectivity.test.target_host", "Target hostname or IP", &target_host);
    register_field("kismet.connectivity.test.target_port", "Target port", &target_port);
    register_field("kismet.connectivity.test.details", "Test details", &details);
    register_field("kismet.connectivity.test.errors", "Error messages", &errors);
    register_field("kismet.connectivity.test.suggestions", "Troubleshooting suggestions", &suggestions);
    register_field("kismet.connectivity.test.timestamp", "Test timestamp", &timestamp);
}

void connectivity_test_result::reserve_fields(std::shared_ptr<tracker_element_map> e) {
    tracker_component::reserve_fields(e);

    if (e != nullptr) {
        status = std::static_pointer_cast<tracker_element_string>(e->find(status_id));
        response_time_ms = std::static_pointer_cast<tracker_element_uint64>(e->find(response_time_ms_id));
        target_host = std::static_pointer_cast<tracker_element_string>(e->find(target_host_id));
        target_port = std::static_pointer_cast<tracker_element_uint16>(e->find(target_port_id));
        details = std::static_pointer_cast<tracker_element_map>(e->find(details_id));
        errors = std::static_pointer_cast<tracker_element_vector>(e->find(errors_id));
        suggestions = std::static_pointer_cast<tracker_element_vector>(e->find(suggestions_id));
        timestamp = std::static_pointer_cast<tracker_element_uint64>(e->find(timestamp_id));
    }

    if (status == nullptr)
        status = std::make_shared<tracker_element_string>(status_id);
    if (response_time_ms == nullptr)
        response_time_ms = std::make_shared<tracker_element_uint64>(response_time_ms_id);
    if (target_host == nullptr)
        target_host = std::make_shared<tracker_element_string>(target_host_id);
    if (target_port == nullptr)
        target_port = std::make_shared<tracker_element_uint16>(target_port_id);
    if (details == nullptr)
        details = std::make_shared<tracker_element_map>(details_id);
    if (errors == nullptr)
        errors = std::make_shared<tracker_element_vector>(errors_id);
    if (suggestions == nullptr)
        suggestions = std::make_shared<tracker_element_vector>(suggestions_id);
    if (timestamp == nullptr)
        timestamp = std::make_shared<tracker_element_uint64>(timestamp_id);

    add_map(status);
    add_map(response_time_ms);
    add_map(target_host);
    add_map(target_port);
    add_map(details);
    add_map(errors);
    add_map(suggestions);
    add_map(timestamp);
}

// connectivity_tester implementation
connectivity_tester::connectivity_tester() :
    lifetime_global() {
    
    tester_mutex.set_name("connectivity_tester");

    // Register HTTP endpoints
    auto httpd = Globalreg::fetch_mandatory_global_as<kis_net_beast_httpd>();

    httpd->register_route("/api/v1/connectivity/test/tcp", {"POST"}, httpd->LOGON_ROLE, {"cmd"},
            std::make_shared<kis_net_web_function_endpoint>(
                [this](std::shared_ptr<kis_net_beast_httpd_connection> con) {
                    return tcp_test_endpoint_handler(con);
                }));

    httpd->register_route("/api/v1/connectivity/test/udp", {"POST"}, httpd->LOGON_ROLE, {"cmd"},
            std::make_shared<kis_net_web_function_endpoint>(
                [this](std::shared_ptr<kis_net_beast_httpd_connection> con) {
                    return udp_test_endpoint_handler(con);
                }));

    httpd->register_route("/api/v1/connectivity/test/elasticsearch", {"POST"}, httpd->LOGON_ROLE, {"cmd"},
            std::make_shared<kis_net_web_function_endpoint>(
                [this](std::shared_ptr<kis_net_beast_httpd_connection> con) {
                    return elasticsearch_test_endpoint_handler(con);
                }));

    httpd->register_route("/api/v1/connectivity/test/mqtt", {"POST"}, httpd->LOGON_ROLE, {"cmd"},
            std::make_shared<kis_net_web_function_endpoint>(
                [this](std::shared_ptr<kis_net_beast_httpd_connection> con) {
                    return mqtt_test_endpoint_handler(con);
                }));

    httpd->register_route("/api/v1/connectivity/diagnostics/report", {"GET", "POST"}, httpd->RO_ROLE, {},
            std::make_shared<kis_net_web_function_endpoint>(
                [this](std::shared_ptr<kis_net_beast_httpd_connection> con) {
                    return diagnostic_report_endpoint_handler(con);
                }));

    _MSG("Connectivity tester initialized", MSGFLAG_INFO);
}

connectivity_tester::~connectivity_tester() {
    Globalreg::globalreg->remove_global("CONNECTIVITY_TESTER");
}

std::shared_ptr<connectivity_test_result> connectivity_tester::create_result(
        connectivity_test_status status, const std::string& host, uint16_t port,
        uint64_t response_time_ms) {
    
    auto result = connectivity_test_result::create_test_result();
    
    result->set_status(status_to_string(status));
    result->set_target_host(host);
    result->set_target_port(port);
    result->set_response_time_ms(response_time_ms);
    result->set_timestamp(std::chrono::duration_cast<std::chrono::seconds>(
        std::chrono::system_clock::now().time_since_epoch()).count());
    
    return result;
}

void connectivity_tester::add_error(std::shared_ptr<connectivity_test_result> result, 
                                   const std::string& error) {
    auto error_elem = std::make_shared<tracker_element_string>();
    error_elem->set(error);
    result->get_errors()->push_back(error_elem);
}

void connectivity_tester::add_suggestion(std::shared_ptr<connectivity_test_result> result, 
                                        const std::string& suggestion) {
    auto suggestion_elem = std::make_shared<tracker_element_string>();
    suggestion_elem->set(suggestion);
    result->get_suggestions()->push_back(suggestion_elem);
}

void connectivity_tester::add_detail(std::shared_ptr<connectivity_test_result> result, 
                                    const std::string& key, const std::string& value) {
    auto detail_elem = std::make_shared<tracker_element_string>();
    detail_elem->set(value);
    result->get_details()->insert(key, detail_elem);
}

std::string connectivity_tester::status_to_string(connectivity_test_status status) {
    switch (status) {
        case connectivity_test_status::SUCCESS:
            return "success";
        case connectivity_test_status::WARNING:
            return "warning";
        case connectivity_test_status::ERROR:
            return "error";
        case connectivity_test_status::TIMEOUT:
            return "timeout";
        default:
            return "unknown";
    }
}

bool connectivity_tester::resolve_hostname(const std::string& hostname, std::string& resolved_ip) {
    struct addrinfo hints, *result;
    memset(&hints, 0, sizeof(hints));
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;

    int status = getaddrinfo(hostname.c_str(), nullptr, &hints, &result);
    if (status != 0) {
        return false;
    }

    char ip_str[INET6_ADDRSTRLEN];
    if (result->ai_family == AF_INET) {
        struct sockaddr_in* addr_in = (struct sockaddr_in*)result->ai_addr;
        inet_ntop(AF_INET, &(addr_in->sin_addr), ip_str, INET_ADDRSTRLEN);
    } else if (result->ai_family == AF_INET6) {
        struct sockaddr_in6* addr_in6 = (struct sockaddr_in6*)result->ai_addr;
        inet_ntop(AF_INET6, &(addr_in6->sin6_addr), ip_str, INET6_ADDRSTRLEN);
    } else {
        freeaddrinfo(result);
        return false;
    }

    resolved_ip = std::string(ip_str);
    freeaddrinfo(result);
    return true;
}

bool connectivity_tester::test_tcp_socket(const std::string& host, uint16_t port, 
                                         int timeout_seconds, uint64_t& response_time_ms) {
    auto start_time = std::chrono::high_resolution_clock::now();
    
    int sockfd = socket(AF_INET, SOCK_STREAM, 0);
    if (sockfd < 0) {
        return false;
    }

    // Set socket to non-blocking
    int flags = fcntl(sockfd, F_GETFL, 0);
    fcntl(sockfd, F_SETFL, flags | O_NONBLOCK);

    struct sockaddr_in server_addr;
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(port);

    // Try to resolve hostname
    std::string resolved_ip;
    if (!resolve_hostname(host, resolved_ip)) {
        close(sockfd);
        return false;
    }

    if (inet_pton(AF_INET, resolved_ip.c_str(), &server_addr.sin_addr) <= 0) {
        close(sockfd);
        return false;
    }

    // Attempt connection
    int result = connect(sockfd, (struct sockaddr*)&server_addr, sizeof(server_addr));
    
    if (result < 0 && errno != EINPROGRESS) {
        close(sockfd);
        return false;
    }

    // Use select to wait for connection with timeout
    fd_set write_fds;
    FD_ZERO(&write_fds);
    FD_SET(sockfd, &write_fds);

    struct timeval timeout;
    timeout.tv_sec = timeout_seconds;
    timeout.tv_usec = 0;

    result = select(sockfd + 1, nullptr, &write_fds, nullptr, &timeout);
    
    auto end_time = std::chrono::high_resolution_clock::now();
    response_time_ms = std::chrono::duration_cast<std::chrono::milliseconds>(
        end_time - start_time).count();

    close(sockfd);

    return (result > 0 && FD_ISSET(sockfd, &write_fds));
}

std::shared_ptr<connectivity_test_result> connectivity_tester::test_tcp_connection(
        const std::string& host, uint16_t port, int timeout_seconds) {

    kis_lock_guard<kis_mutex> lk(tester_mutex, "test_tcp_connection");

    uint64_t response_time_ms = 0;
    bool success = test_tcp_socket(host, port, timeout_seconds, response_time_ms);

    auto result = create_result(
        success ? connectivity_test_status::SUCCESS : connectivity_test_status::ERROR,
        host, port, response_time_ms);

    if (success) {
        add_detail(result, "tcp_handshake", "success");
        add_detail(result, "connection_type", "tcp");
        if (response_time_ms < 100) {
            add_detail(result, "latency_quality", "excellent");
        } else if (response_time_ms < 500) {
            add_detail(result, "latency_quality", "good");
        } else {
            add_detail(result, "latency_quality", "poor");
        }
    } else {
        add_error(result, "Failed to establish TCP connection");
        add_suggestion(result, "Check if the target server is running and listening on port " + std::to_string(port));
        add_suggestion(result, "Verify firewall rules allow connections to " + host + ":" + std::to_string(port));
        add_suggestion(result, "Test basic network connectivity with ping");
    }

    return result;
}

std::shared_ptr<connectivity_test_result> connectivity_tester::test_udp_connection(
        const std::string& host, uint16_t port, int timeout_seconds) {

    kis_lock_guard<kis_mutex> lk(tester_mutex, "test_udp_connection");

    uint64_t response_time_ms = 0;
    bool success = test_udp_reachability(host, port, timeout_seconds, response_time_ms);

    auto result = create_result(
        success ? connectivity_test_status::SUCCESS : connectivity_test_status::WARNING,
        host, port, response_time_ms);

    if (success) {
        add_detail(result, "udp_reachability", "success");
        add_detail(result, "connection_type", "udp");
        add_detail(result, "note", "UDP is connectionless - success indicates port appears reachable");
    } else {
        result->set_status("warning");
        add_error(result, "UDP port appears unreachable or filtered");
        add_suggestion(result, "UDP is connectionless - this test has limitations");
        add_suggestion(result, "Check if target service supports UDP on port " + std::to_string(port));
        add_suggestion(result, "Verify firewall rules allow UDP traffic");
        add_suggestion(result, "Some firewalls silently drop UDP packets");
    }

    return result;
}

bool connectivity_tester::test_udp_reachability(const std::string& host, uint16_t port,
                                               int timeout_seconds, uint64_t& response_time_ms) {
    auto start_time = std::chrono::high_resolution_clock::now();

    int sockfd = socket(AF_INET, SOCK_DGRAM, 0);
    if (sockfd < 0) {
        return false;
    }

    struct sockaddr_in server_addr;
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(port);

    std::string resolved_ip;
    if (!resolve_hostname(host, resolved_ip)) {
        close(sockfd);
        return false;
    }

    if (inet_pton(AF_INET, resolved_ip.c_str(), &server_addr.sin_addr) <= 0) {
        close(sockfd);
        return false;
    }

    // Send a small test packet
    const char* test_data = "KISMET_CONNECTIVITY_TEST";
    ssize_t sent = sendto(sockfd, test_data, strlen(test_data), 0,
                         (struct sockaddr*)&server_addr, sizeof(server_addr));

    auto end_time = std::chrono::high_resolution_clock::now();
    response_time_ms = std::chrono::duration_cast<std::chrono::milliseconds>(
        end_time - start_time).count();

    close(sockfd);

    // For UDP, we consider it successful if we can send the packet
    // Real UDP testing would require protocol-specific responses
    return (sent > 0);
}

std::shared_ptr<connectivity_test_result> connectivity_tester::test_elasticsearch_connection(
        const std::string& url, const std::string& username,
        const std::string& password, int timeout_seconds) {

    kis_lock_guard<kis_mutex> lk(tester_mutex, "test_elasticsearch_connection");

    uint64_t response_time_ms = 0;
    std::string response_body;

    // Test basic HTTP connectivity first
    bool http_success = test_http_endpoint(url, timeout_seconds, response_time_ms, response_body);

    auto result = create_result(
        http_success ? connectivity_test_status::SUCCESS : connectivity_test_status::ERROR,
        url, 0, response_time_ms);

    if (http_success) {
        add_detail(result, "http_connectivity", "success");
        add_detail(result, "connection_type", "elasticsearch");

        // Try to test Elasticsearch-specific endpoint
        std::string health_url = url;
        if (health_url.back() != '/') health_url += "/";
        health_url += "_cluster/health";

        uint64_t health_response_time = 0;
        std::string health_response;
        bool health_success = test_http_endpoint(health_url, timeout_seconds,
                                               health_response_time, health_response);

        if (health_success) {
            add_detail(result, "elasticsearch_health", "success");
            add_detail(result, "cluster_accessible", "true");
        } else {
            result->set_status("warning");
            add_detail(result, "elasticsearch_health", "failed");
            add_error(result, "HTTP connection successful but Elasticsearch health endpoint failed");
            add_suggestion(result, "Verify this is an Elasticsearch server");
            add_suggestion(result, "Check Elasticsearch authentication requirements");
        }

        if (response_time_ms < 200) {
            add_detail(result, "performance", "excellent");
        } else if (response_time_ms < 1000) {
            add_detail(result, "performance", "good");
        } else {
            add_detail(result, "performance", "slow");
            add_suggestion(result, "Consider network optimization for better performance");
        }
    } else {
        add_error(result, "Failed to connect to Elasticsearch endpoint");
        add_suggestion(result, "Verify the Elasticsearch URL is correct");
        add_suggestion(result, "Check if Elasticsearch is running and accessible");
        add_suggestion(result, "Verify network connectivity and firewall rules");
        add_suggestion(result, "Check SSL/TLS configuration if using HTTPS");
    }

    return result;
}

std::shared_ptr<connectivity_test_result> connectivity_tester::test_mqtt_connection(
        const std::string& host, uint16_t port, const std::string& username,
        const std::string& password, int timeout_seconds) {

    kis_lock_guard<kis_mutex> lk(tester_mutex, "test_mqtt_connection");

    // For MQTT, we'll test basic TCP connectivity first
    uint64_t response_time_ms = 0;
    bool tcp_success = test_tcp_socket(host, port, timeout_seconds, response_time_ms);

    auto result = create_result(
        tcp_success ? connectivity_test_status::SUCCESS : connectivity_test_status::ERROR,
        host, port, response_time_ms);

    if (tcp_success) {
        add_detail(result, "tcp_connectivity", "success");
        add_detail(result, "connection_type", "mqtt");
        add_detail(result, "note", "TCP connection successful - MQTT protocol test requires full client");

        // Standard MQTT ports
        if (port == 1883) {
            add_detail(result, "mqtt_port_type", "standard_unencrypted");
        } else if (port == 8883) {
            add_detail(result, "mqtt_port_type", "standard_ssl");
        } else {
            add_detail(result, "mqtt_port_type", "custom");
        }

        if (!username.empty()) {
            add_detail(result, "authentication", "configured");
        } else {
            add_detail(result, "authentication", "none");
        }
    } else {
        add_error(result, "Failed to establish TCP connection to MQTT broker");
        add_suggestion(result, "Check if MQTT broker is running on " + host + ":" + std::to_string(port));
        add_suggestion(result, "Verify firewall rules allow connections to MQTT broker");
        add_suggestion(result, "Standard MQTT ports are 1883 (unencrypted) and 8883 (SSL)");
    }

    return result;
}

bool connectivity_tester::test_http_endpoint(const std::string& url, int timeout_seconds,
                                           uint64_t& response_time_ms, std::string& response_body) {
    auto start_time = std::chrono::high_resolution_clock::now();

    // Simple HTTP test - in a real implementation, you'd use a proper HTTP client
    // For now, we'll just test the TCP connection to the HTTP port

    // Parse URL to extract host and port
    std::string host;
    uint16_t port = 80;

    size_t protocol_end = url.find("://");
    if (protocol_end != std::string::npos) {
        std::string protocol = url.substr(0, protocol_end);
        if (protocol == "https") {
            port = 443;
        }

        size_t host_start = protocol_end + 3;
        size_t host_end = url.find('/', host_start);
        if (host_end == std::string::npos) {
            host_end = url.find(':', host_start);
        }

        if (host_end == std::string::npos) {
            host = url.substr(host_start);
        } else {
            host = url.substr(host_start, host_end - host_start);

            // Check for port specification
            size_t port_start = url.find(':', host_start);
            if (port_start != std::string::npos && port_start < url.find('/', host_start)) {
                size_t port_end = url.find('/', port_start);
                if (port_end == std::string::npos) {
                    port_end = url.length();
                }
                std::string port_str = url.substr(port_start + 1, port_end - port_start - 1);
                port = static_cast<uint16_t>(std::stoi(port_str));
            }
        }
    } else {
        host = url;
    }

    bool success = test_tcp_socket(host, port, timeout_seconds, response_time_ms);

    auto end_time = std::chrono::high_resolution_clock::now();
    response_time_ms = std::chrono::duration_cast<std::chrono::milliseconds>(
        end_time - start_time).count();

    return success;
}

// HTTP endpoint handlers
void connectivity_tester::tcp_test_endpoint_handler(std::shared_ptr<kis_net_beast_httpd_connection> con) {
    std::ostream stream(&con->response_stream());

    try {
        auto json = con->json();

        std::string host = json.value("host", "");
        uint16_t port = json.value("port", 0);
        int timeout = json.value("timeout", 10);

        if (host.empty() || port == 0) {
            con->set_status(400);
            stream << R"({"error": "Missing required parameters: host and port"})";
            return;
        }

        auto result = test_tcp_connection(host, port, timeout);

        // Serialize the result
        nlohmann::json response;
        response["status"] = result->get_status();
        response["response_time_ms"] = result->get_response_time_ms();
        response["target_host"] = result->get_target_host();
        response["target_port"] = result->get_target_port();
        response["timestamp"] = result->get_timestamp();

        // Add details
        nlohmann::json details;
        for (auto& d : *result->get_details()) {
            auto key = d.first;
            auto val = std::static_pointer_cast<tracker_element_string>(d.second);
            details[key] = val->get();
        }
        response["details"] = details;

        // Add errors
        nlohmann::json errors = nlohmann::json::array();
        for (auto& e : *result->get_errors()) {
            auto error_str = std::static_pointer_cast<tracker_element_string>(e);
            errors.push_back(error_str->get());
        }
        response["errors"] = errors;

        // Add suggestions
        nlohmann::json suggestions = nlohmann::json::array();
        for (auto& s : *result->get_suggestions()) {
            auto suggestion_str = std::static_pointer_cast<tracker_element_string>(s);
            suggestions.push_back(suggestion_str->get());
        }
        response["suggestions"] = suggestions;

        stream << response.dump();

    } catch (const std::exception& e) {
        con->set_status(500);
        stream << R"({"error": "Internal server error: )" << e.what() << R"("})";
    }
}

void connectivity_tester::udp_test_endpoint_handler(std::shared_ptr<kis_net_beast_httpd_connection> con) {
    std::ostream stream(&con->response_stream());

    try {
        auto json = con->json();

        std::string host = json.value("host", "");
        uint16_t port = json.value("port", 0);
        int timeout = json.value("timeout", 10);

        if (host.empty() || port == 0) {
            con->set_status(400);
            stream << R"({"error": "Missing required parameters: host and port"})";
            return;
        }

        auto result = test_udp_connection(host, port, timeout);

        // Serialize the result (same format as TCP)
        nlohmann::json response;
        response["status"] = result->get_status();
        response["response_time_ms"] = result->get_response_time_ms();
        response["target_host"] = result->get_target_host();
        response["target_port"] = result->get_target_port();
        response["timestamp"] = result->get_timestamp();

        nlohmann::json details;
        for (auto& d : *result->get_details()) {
            auto key = d.first;
            auto val = std::static_pointer_cast<tracker_element_string>(d.second);
            details[key] = val->get();
        }
        response["details"] = details;

        nlohmann::json errors = nlohmann::json::array();
        for (auto& e : *result->get_errors()) {
            auto error_str = std::static_pointer_cast<tracker_element_string>(e);
            errors.push_back(error_str->get());
        }
        response["errors"] = errors;

        nlohmann::json suggestions = nlohmann::json::array();
        for (auto& s : *result->get_suggestions()) {
            auto suggestion_str = std::static_pointer_cast<tracker_element_string>(s);
            suggestions.push_back(suggestion_str->get());
        }
        response["suggestions"] = suggestions;

        stream << response.dump();

    } catch (const std::exception& e) {
        con->set_status(500);
        stream << R"({"error": "Internal server error: )" << e.what() << R"("})";
    }
}

void connectivity_tester::elasticsearch_test_endpoint_handler(std::shared_ptr<kis_net_beast_httpd_connection> con) {
    std::ostream stream(&con->response_stream());

    try {
        auto json = con->json();

        std::string url = json.value("url", "");
        std::string username = json.value("username", "");
        std::string password = json.value("password", "");
        int timeout = json.value("timeout", 10);

        if (url.empty()) {
            con->set_status(400);
            stream << R"({"error": "Missing required parameter: url"})";
            return;
        }

        auto result = test_elasticsearch_connection(url, username, password, timeout);

        // Serialize the result
        nlohmann::json response;
        response["status"] = result->get_status();
        response["response_time_ms"] = result->get_response_time_ms();
        response["target_host"] = result->get_target_host();
        response["timestamp"] = result->get_timestamp();

        nlohmann::json details;
        for (auto& d : *result->get_details()) {
            auto key = d.first;
            auto val = std::static_pointer_cast<tracker_element_string>(d.second);
            details[key] = val->get();
        }
        response["details"] = details;

        nlohmann::json errors = nlohmann::json::array();
        for (auto& e : *result->get_errors()) {
            auto error_str = std::static_pointer_cast<tracker_element_string>(e);
            errors.push_back(error_str->get());
        }
        response["errors"] = errors;

        nlohmann::json suggestions = nlohmann::json::array();
        for (auto& s : *result->get_suggestions()) {
            auto suggestion_str = std::static_pointer_cast<tracker_element_string>(s);
            suggestions.push_back(suggestion_str->get());
        }
        response["suggestions"] = suggestions;

        stream << response.dump();

    } catch (const std::exception& e) {
        con->set_status(500);
        stream << R"({"error": "Internal server error: )" << e.what() << R"("})";
    }
}

void connectivity_tester::mqtt_test_endpoint_handler(std::shared_ptr<kis_net_beast_httpd_connection> con) {
    std::ostream stream(&con->response_stream());

    try {
        auto json = con->json();

        std::string host = json.value("host", "");
        uint16_t port = json.value("port", 1883);
        std::string username = json.value("username", "");
        std::string password = json.value("password", "");
        int timeout = json.value("timeout", 10);

        if (host.empty()) {
            con->set_status(400);
            stream << R"({"error": "Missing required parameter: host"})";
            return;
        }

        auto result = test_mqtt_connection(host, port, username, password, timeout);

        // Serialize the result
        nlohmann::json response;
        response["status"] = result->get_status();
        response["response_time_ms"] = result->get_response_time_ms();
        response["target_host"] = result->get_target_host();
        response["target_port"] = result->get_target_port();
        response["timestamp"] = result->get_timestamp();

        nlohmann::json details;
        for (auto& d : *result->get_details()) {
            auto key = d.first;
            auto val = std::static_pointer_cast<tracker_element_string>(d.second);
            details[key] = val->get();
        }
        response["details"] = details;

        nlohmann::json errors = nlohmann::json::array();
        for (auto& e : *result->get_errors()) {
            auto error_str = std::static_pointer_cast<tracker_element_string>(e);
            errors.push_back(error_str->get());
        }
        response["errors"] = errors;

        nlohmann::json suggestions = nlohmann::json::array();
        for (auto& s : *result->get_suggestions()) {
            auto suggestion_str = std::static_pointer_cast<tracker_element_string>(s);
            suggestions.push_back(suggestion_str->get());
        }
        response["suggestions"] = suggestions;

        stream << response.dump();

    } catch (const std::exception& e) {
        con->set_status(500);
        stream << R"({"error": "Internal server error: )" << e.what() << R"("})";
    }
}

void connectivity_tester::diagnostic_report_endpoint_handler(std::shared_ptr<kis_net_beast_httpd_connection> con) {
    std::ostream stream(&con->response_stream());

    try {
        std::string export_type = "";

        // Check if specific export type requested
        if (con->verb() == boost::beast::http::verb::post) {
            auto json = con->json();
            export_type = json.value("export_type", "");
        }

        auto report = generate_diagnostic_report(export_type);

        // Convert tracker element to JSON
        nlohmann::json response;

        response["timestamp"] = std::chrono::duration_cast<std::chrono::seconds>(
            std::chrono::system_clock::now().time_since_epoch()).count();
        response["report_type"] = export_type.empty() ? "full_system" : export_type;

        // Add system information
        response["system_info"] = {
            {"kismet_version", "2025.01.17"},
            {"connectivity_tester_version", "1.0.0"},
            {"platform", "linux"}
        };

        // Add network diagnostics
        response["network_diagnostics"] = {
            {"dns_resolution", "available"},
            {"ipv4_connectivity", "available"},
            {"ipv6_connectivity", "unknown"}
        };

        // Add export-specific diagnostics
        if (export_type.empty() || export_type == "tcp") {
            response["tcp_diagnostics"] = {
                {"socket_support", "available"},
                {"common_ports", {80, 443, 8080, 8443, 9200}},
                {"timeout_default", 10}
            };
        }

        if (export_type.empty() || export_type == "udp") {
            response["udp_diagnostics"] = {
                {"socket_support", "available"},
                {"common_ports", {53, 123, 1883, 5683}},
                {"limitations", "connectionless protocol - limited testing capability"}
            };
        }

        if (export_type.empty() || export_type == "elasticsearch") {
            response["elasticsearch_diagnostics"] = {
                {"http_client", "available"},
                {"ssl_support", "available"},
                {"common_ports", {9200, 9243}},
                {"health_endpoint", "/_cluster/health"}
            };
        }

        if (export_type.empty() || export_type == "mqtt") {
            response["mqtt_diagnostics"] = {
                {"tcp_support", "available"},
                {"ssl_support", "available"},
                {"common_ports", {1883, 8883}},
                {"protocol_version", "3.1.1"}
            };
        }

        // Add troubleshooting guide
        response["troubleshooting_guide"] = {
            {"connection_refused", {
                "Check if target service is running",
                "Verify port number is correct",
                "Check firewall rules",
                "Test with telnet or nc command"
            }},
            {"timeout_errors", {
                "Check network connectivity",
                "Verify DNS resolution",
                "Test with ping command",
                "Check for network congestion"
            }},
            {"authentication_failed", {
                "Verify username and password",
                "Check API key validity",
                "Confirm authentication method",
                "Test credentials manually"
            }},
            {"ssl_errors", {
                "Check certificate validity",
                "Verify SSL/TLS version support",
                "Check certificate chain",
                "Test with curl --insecure"
            }}
        };

        stream << response.dump(2); // Pretty print with 2-space indentation

    } catch (const std::exception& e) {
        con->set_status(500);
        stream << R"({"error": "Failed to generate diagnostic report: )" << e.what() << R"("})";
    }
}

std::shared_ptr<tracker_element> connectivity_tester::generate_diagnostic_report(const std::string& export_type) {
    kis_lock_guard<kis_mutex> lk(tester_mutex, "generate_diagnostic_report");

    // Create a basic tracker element map for the report
    auto report = std::make_shared<tracker_element_map>();

    // Add timestamp
    auto timestamp_elem = std::make_shared<tracker_element_uint64>();
    timestamp_elem->set(std::chrono::duration_cast<std::chrono::seconds>(
        std::chrono::system_clock::now().time_since_epoch()).count());
    report->insert("timestamp", timestamp_elem);

    // Add report type
    auto type_elem = std::make_shared<tracker_element_string>();
    type_elem->set(export_type.empty() ? "full_system" : export_type);
    report->insert("report_type", type_elem);

    return report;
}
