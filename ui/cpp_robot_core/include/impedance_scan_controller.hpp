#pragma once

#include <algorithm>
#include <array>
#include <cmath>
#include <string>

#include "robot_core/contact_control_contract.h"
#include "robot_core/normal_axis_admittance_controller.h"
#include "robot_core/normal_force_estimator.h"
#include "robot_core/orientation_trim_controller.h"
#include "robot_core/tangential_scan_controller.h"

namespace legacy_example {

/**
 * @brief Fixed demo observations used by the legacy example wrapper.
 *
 * This wrapper exists only to demonstrate how the canonical contact-control
 * components are composed. It is not the production RT mainline and does not
 * talk to the SDK directly.
 */
struct DemoObservation {
  double pressure_force_n{0.0};
  bool pressure_valid{true};
  double pressure_age_ms{0.0};
  double wrench_force_n{0.0};
  bool wrench_valid{true};
  double wrench_age_ms{0.0};
  double requested_tangent_speed_mm_s{0.0};
  double dt_s{0.001};
};

/**
 * @brief Canonical controller composition snapshot emitted by the demo wrapper.
 */
struct DemoContactSnapshot {
  robot_core::NormalForceEstimate force{};
  robot_core::AdmittanceCommand admittance{};
  robot_core::TangentialScanState tangential{};
  robot_core::OrientationTrimState trim{};
};

/**
 * @brief Legacy wrapper kept only for educational/smoke-demo purposes.
 *
 * The production RT mainline lives in SdkRobotFacade and uses the same
 * controller primitives below. This wrapper demonstrates the exact controller
 * composition without claiming to be the production execution path.
 */
class ImpedanceScanController {
public:
  ImpedanceScanController() = default;

  /**
   * @brief Configure the wrapper from the canonical contact-control contract.
   * @param contract Canonical contact-control contract.
   * @return true when the contract is valid and applied; false otherwise.
   * @throws No exceptions are thrown.
   * @boundary Invalid contracts leave the previous configuration untouched.
   */
  bool configure(const robot_core::ContactControlContract& contract) {
    if (!robot_core::validateContactControlContract(contract)) {
      return false;
    }
    contract_ = contract;
    force_estimator_.configure(contract.force_estimator);
    admittance_.configure(contract.seek_contact_admittance);
    tangential_.configure(contract.tangential_scan);
    trim_.configure(contract.orientation_trim);
    return true;
  }

  /**
   * @brief Reset all controller states.
   * @return None.
   * @throws No exceptions are thrown.
   * @boundary Safe to call between simulated phases.
   */
  void reset() {
    force_estimator_.reset();
    admittance_.reset();
    tangential_.reset();
    trim_.reset();
  }

  /**
   * @brief Execute one demonstration control step.
   * @param target_force_n Desired normal force.
   * @param observation Current simulated observation bundle.
   * @return Snapshot of all canonical controller outputs.
   * @throws No exceptions are thrown.
   * @boundary Non-positive dt returns a zero-advance tangential/admittance step.
   */
  DemoContactSnapshot step(double target_force_n, const DemoObservation& observation) {
    robot_core::NormalForceEstimatorInput estimator_input{};
    estimator_input.pressure_force_n = observation.pressure_force_n;
    estimator_input.pressure_valid = observation.pressure_valid;
    estimator_input.pressure_age_ms = observation.pressure_age_ms;
    estimator_input.wrench_force_n = observation.wrench_force_n;
    estimator_input.wrench_valid = observation.wrench_valid;
    estimator_input.wrench_age_ms = observation.wrench_age_ms;
    estimator_input.contact_direction_sign = 1.0;

    DemoContactSnapshot snapshot{};
    snapshot.force = force_estimator_.estimate(estimator_input);
    snapshot.admittance = admittance_.step(target_force_n, snapshot.force.estimated_force_n, observation.dt_s);
    snapshot.tangential = tangential_.advance(observation.requested_tangent_speed_mm_s, observation.dt_s);
    snapshot.trim = trim_.step(snapshot.admittance.state.force_error_n, observation.dt_s);
    return snapshot;
  }

  const robot_core::ContactControlContract& contract() const { return contract_; }

private:
  robot_core::ContactControlContract contract_{};
  robot_core::NormalForceEstimator force_estimator_{};
  robot_core::NormalAxisAdmittanceController admittance_{};
  robot_core::TangentialScanController tangential_{};
  robot_core::OrientationTrimController trim_{};
};

}  // namespace legacy_example
