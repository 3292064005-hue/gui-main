#pragma once

#include <array>
#include <cmath>

namespace robot_core {

/**
 * @brief High-Performance Position-Based Admittance Controller
 * Computes Delta Pos offset natively at 1kHz.
 * Model: M_d * ddx + D_d * dx + K_d * x = F_ext - F_target
 * Where x is the position deviation from the commanded trajectory along the force axis (Z).
 */
class AdmittanceController {
public:
    AdmittanceController() {
        // Default Tissue constants. M=Mass (kg), D=Damping, K=Stiffness
        M_d = 2.0;
        D_d = 400.0;
        K_d = 0.0; // Pure damping typically used for free-space pressure tracking
        
        dt_ = 0.001; // 1ms loop time

        x_ = 0.0;
        x_dot_ = 0.0;
        x_ddot_ = 0.0;
    }

    // Pass the external sensor Z force (N) and the Desired Target Force (e.g. 10N)
    // Returns the delta displacement (meters) we need to add to the robot TCP Z-axis
    double computeDeltaZ(double f_measured, double f_target) {
        // Compute Error: (f_measured normally pushes negative along local Z, f_target = -10.0)
        double f_error = f_measured - f_target;

        // Apply Deadband to prevent micro-oscillations 
        if (std::abs(f_error) < 0.2) {
            f_error = 0.0;
        }

        // Discrete Admittance Euler Integration (M * x_ddot + D * x_dot + K * x = f_error)
        x_ddot_ = (f_error - D_d * x_dot_ - K_d * x_) / M_d;
        x_dot_ += x_ddot_ * dt_;
        x_ += x_dot_ * dt_;

        // Physical clamping limits (Maximum compliance offset = +/- 5cm)
        if (x_ > 0.05) x_ = 0.05;
        if (x_ < -0.05) x_ = -0.05;

        return x_;
    }

    // Reset integrals upon scan completion or E-Stop
    void reset() {
        x_ = 0.0;
        x_dot_ = 0.0;
        x_ddot_ = 0.0;
    }

private:
    double M_d, D_d, K_d;
    double dt_;
    double x_, x_dot_, x_ddot_;
};

} // namespace robot_core
