#include "config.h"

#include "connectivity_tester.h"
#include "globalregistry.h"

// Global initialization function to create and register the connectivity tester
void connectivity_tester_init() {
    auto tester = std::make_shared<connectivity_tester>();
    Globalreg::globalreg->register_lifetime_global(tester);
    Globalreg::globalreg->insert_global(connectivity_tester::global_name(), tester);
}

// Static initialization - this will be called when the module is loaded
static void __attribute__((constructor)) connectivity_tester_static_init() {
    // Register the initialization function to be called during Kismet startup
    Globalreg::globalreg->register_deferred_global_constructor(connectivity_tester_init);
}
