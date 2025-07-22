#ifndef __CONNECTIVITY_TESTER_H__
#define __CONNECTIVITY_TESTER_H__

#include "config.h"

#include <memory>
#include <string>
#include <thread>
#include <future>
#include <chrono>

#include "globalregistry.h"
#include "kis_mutex.h"
#include "kis_net_beast_httpd.h"
#include "trackedelement.h"
#include "trackedcomponent.h"

// Forward declarations
class kis_net_beast_httpd_connection;

// Test result status enumeration
enum class connectivity_test_status {
    SUCCESS,
    WARNING, 
    ERROR,
    TIMEOUT,
    UNKNOWN
};

// Individual test result structure
class connectivity_test_result : public tracker_component {
public:
    connectivity_test_result() :
        tracker_component() {
        register_fields();
        reserve_fields(nullptr);
    }

    connectivity_test_result(int in_id) :
        tracker_component(in_id) {
        register_fields();
        reserve_fields(nullptr);
    }

    connectivity_test_result(int in_id, std::shared_ptr<tracker_element_map> e) :
        tracker_component(in_id, e) {
        register_fields();
        reserve_fields(e);
    }

    virtual uint32_t get_signature() const override {
        return adler32_checksum("connectivity_test_result");
    }

    static std::string global_name() { return "connectivity_test_result"; }

    static std::shared_ptr<connectivity_test_result> create_test_result() {
        return std::make_shared<connectivity_test_result>();
    }

protected:
    virtual void register_fields() override;
    virtual void reserve_fields(std::shared_ptr<tracker_element_map> e) override;

    std::shared_ptr<tracker_element_string> status;
    std::shared_ptr<tracker_element_uint64> response_time_ms;
    std::shared_ptr<tracker_element_string> target_host;
    std::shared_ptr<tracker_element_uint16> target_port;
    std::shared_ptr<tracker_element_map> details;
    std::shared_ptr<tracker_element_vector> errors;
    std::shared_ptr<tracker_element_vector> suggestions;
    std::shared_ptr<tracker_element_uint64> timestamp;

public:
    __Proxy(status, std::string, std::string, std::string, status);
    __Proxy(response_time_ms, uint64_t, uint64_t, uint64_t, response_time_ms);
    __Proxy(target_host, std::string, std::string, std::string, target_host);
    __Proxy(target_port, uint16_t, uint16_t, uint16_t, target_port);
    __Proxy(details, tracker_element_map, tracker_element_map, tracker_element_map, details);
    __Proxy(errors, tracker_element_vector, tracker_element_vector, tracker_element_vector, errors);
    __Proxy(suggestions, tracker_element_vector, tracker_element_vector, tracker_element_vector, suggestions);
    __Proxy(timestamp, uint64_t, uint64_t, uint64_t, timestamp);
};

// Main connectivity tester class
class connectivity_tester : public lifetime_global {
public:
    static std::string global_name() { return "CONNECTIVITY_TESTER"; }

    connectivity_tester();
    virtual ~connectivity_tester();

    // Test methods for different export types
    std::shared_ptr<connectivity_test_result> test_tcp_connection(
        const std::string& host, uint16_t port, int timeout_seconds = 10);
    
    std::shared_ptr<connectivity_test_result> test_udp_connection(
        const std::string& host, uint16_t port, int timeout_seconds = 10);
    
    std::shared_ptr<connectivity_test_result> test_elasticsearch_connection(
        const std::string& url, const std::string& username = "", 
        const std::string& password = "", int timeout_seconds = 10);
    
    std::shared_ptr<connectivity_test_result> test_mqtt_connection(
        const std::string& host, uint16_t port, const std::string& username = "",
        const std::string& password = "", int timeout_seconds = 10);

    // HTTP endpoint handlers
    void tcp_test_endpoint_handler(std::shared_ptr<kis_net_beast_httpd_connection> con);
    void udp_test_endpoint_handler(std::shared_ptr<kis_net_beast_httpd_connection> con);
    void elasticsearch_test_endpoint_handler(std::shared_ptr<kis_net_beast_httpd_connection> con);
    void mqtt_test_endpoint_handler(std::shared_ptr<kis_net_beast_httpd_connection> con);
    void diagnostic_report_endpoint_handler(std::shared_ptr<kis_net_beast_httpd_connection> con);

    // Diagnostic reporting
    std::shared_ptr<tracker_element> generate_diagnostic_report(const std::string& export_type = "");

protected:
    kis_mutex tester_mutex;

    // Helper methods
    std::shared_ptr<connectivity_test_result> create_result(
        connectivity_test_status status, const std::string& host, uint16_t port,
        uint64_t response_time_ms = 0);
    
    void add_error(std::shared_ptr<connectivity_test_result> result, const std::string& error);
    void add_suggestion(std::shared_ptr<connectivity_test_result> result, const std::string& suggestion);
    void add_detail(std::shared_ptr<connectivity_test_result> result, 
                   const std::string& key, const std::string& value);

    // Network testing utilities
    bool test_tcp_socket(const std::string& host, uint16_t port, int timeout_seconds, 
                        uint64_t& response_time_ms);
    bool test_udp_reachability(const std::string& host, uint16_t port, int timeout_seconds,
                              uint64_t& response_time_ms);
    bool test_http_endpoint(const std::string& url, int timeout_seconds,
                           uint64_t& response_time_ms, std::string& response_body);

    // DNS resolution helper
    bool resolve_hostname(const std::string& hostname, std::string& resolved_ip);

    // Status conversion helper
    std::string status_to_string(connectivity_test_status status);
};

#endif
