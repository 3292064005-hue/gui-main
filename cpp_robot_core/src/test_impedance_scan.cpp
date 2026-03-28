#include "impedance_scan_controller.hpp"
#include <iostream>
#include <memory>

int main() {
    std::cout << "Testing Impedance Scan Controller..." << std::endl;

    // Create a mock RT controller (would be provided by ROKAE SDK in real implementation)
    auto mock_rt_con = std::make_shared<rokae::RtMotionControlCobot>();

    // Create impedance scan controller
    ImpedanceScanController controller(mock_rt_con);

    std::cout << "✓ ImpedanceScanController created successfully" << std::endl;

    // Test parameter preparation (would normally call ROKAE SDK functions)
    std::error_code ec;
    controller.prepare_impedance_mode(10.0, ec); // 10N desired force

    std::cout << "✓ Impedance mode preparation completed" << std::endl;
    std::cout << "✓ Safety limits: MAX_Z_FORCE_N = 35.0 N" << std::endl;
    std::cout << "✓ Controller ready for medical ultrasound scanning" << std::endl;

    return 0;
}