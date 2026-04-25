#pragma once

#include <set>
#include <string>
#include <vector>

#include "json_utils.h"

namespace robot_core {

/**
 * @brief Normalize an authority/context token and fall back when empty.
 * @param raw Candidate token from a runtime request or normalized context.
 * @param fallback Value returned when ``raw`` is blank after trimming.
 * @return Trimmed token or ``fallback``.
 * @throws No exceptions are intentionally thrown.
 * @boundary Pure helper; does not mutate runtime state and does not authorize
 * commands by itself.
 */
inline std::string normalizeAuthorityToken(const std::string& raw, const std::string& fallback) {
  const auto begin = raw.find_first_not_of(" \t\r\n");
  if (begin == std::string::npos) return fallback;
  const auto end = raw.find_last_not_of(" \t\r\n");
  return raw.substr(begin, end - begin + 1);
}

/**
 * @brief Serialize authority claims deterministically for reply envelopes.
 * @param claims Set of claim tokens already validated by the authority kernel.
 * @return JSON string array with stable lexical ordering inherited from set.
 * @throws No exceptions are intentionally propagated.
 * @boundary Pure formatting helper; it is not a policy decision point.
 */
inline std::string joinClaims(const std::set<std::string>& claims) {
  std::vector<std::string> items(claims.begin(), claims.end());
  return json::stringArray(items);
}

}  // namespace robot_core
