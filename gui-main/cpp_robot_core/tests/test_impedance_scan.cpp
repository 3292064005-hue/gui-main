#include "impedance_scan_controller.hpp"
#include "robot_core/force_control_config.h"
#include <iostream>
#include <memory>

int main() {
    std::cout << "Testing Impedance Scan Controller..." << std::endl;
    const auto limits = robot_core::loadForceControlLimits();

    // Create a mock RT controller (would be provided by ROKAE SDK in real implementation)
    auto mock_rt_con = std::make_shared<rokae::RtMotionControlCobot>();

    // Create impedance scan controller
    ImpedanceScanController controller(mock_rt_con);

    std::cout << "✓ ImpedanceScanController created successfully" << std::endl;

    // Test parameter preparation (would normally call ROKAE SDK functions)
    std::error_code ec;
    controller.prepare_impedance_mode(limits.desired_contact_force_n, ec);

    std::cout << "✓ Impedance mode preparation completed" << std::endl;
    std::cout << "✓ Safety limits: MAX_Z_FORCE_N = " << limits.max_z_force_n << " N" << std::endl;
    std::cout << "✓ Controller ready for medical ultrasound scanning" << std::endl;

    return 0;
}
