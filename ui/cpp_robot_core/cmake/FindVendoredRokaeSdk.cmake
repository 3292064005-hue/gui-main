include_guard(GLOBAL)

set(_VendoredRokaeSdk_HINTS "")
if(DEFINED XCORE_SDK_ROOT AND NOT XCORE_SDK_ROOT STREQUAL "")
  list(APPEND _VendoredRokaeSdk_HINTS "${XCORE_SDK_ROOT}")
endif()
if(DEFINED ENV{XCORE_SDK_ROOT} AND NOT "$ENV{XCORE_SDK_ROOT}" STREQUAL "")
  list(APPEND _VendoredRokaeSdk_HINTS "$ENV{XCORE_SDK_ROOT}")
endif()
if(DEFINED ENV{ROKAE_SDK_ROOT} AND NOT "$ENV{ROKAE_SDK_ROOT}" STREQUAL "")
  list(APPEND _VendoredRokaeSdk_HINTS "$ENV{ROKAE_SDK_ROOT}")
endif()
list(APPEND _VendoredRokaeSdk_HINTS "${CMAKE_CURRENT_LIST_DIR}/../../third_party/rokae_xcore_sdk/robot")

set(VendoredRokaeSdk_FOUND FALSE)
foreach(_sdk_root IN LISTS _VendoredRokaeSdk_HINTS)
  if(EXISTS "${_sdk_root}/include/rokae/robot.h" AND EXISTS "${_sdk_root}/external/Eigen/Core")
    set(VendoredRokaeSdk_ROOT "${_sdk_root}")
    break()
  endif()
endforeach()

if(VendoredRokaeSdk_ROOT)
  set(VendoredRokaeSdk_INCLUDE_DIR "${VendoredRokaeSdk_ROOT}/include")
  set(VendoredRokaeSdk_EXTERNAL_DIR "${VendoredRokaeSdk_ROOT}/external")
  set(VendoredRokaeSdk_LIB_DIR "${VendoredRokaeSdk_ROOT}/lib/Linux/cpp/x86_64")
  set(VendoredRokaeSdk_STATIC_LIB "${VendoredRokaeSdk_LIB_DIR}/libxCoreSDK.a")
  set(VendoredRokaeSdk_XMATE_MODEL_LIB "${VendoredRokaeSdk_LIB_DIR}/libxMateModel.a")
  if(EXISTS "${VendoredRokaeSdk_STATIC_LIB}")
    set(VendoredRokaeSdk_FOUND TRUE)
  endif()
endif()

if(VendoredRokaeSdk_FOUND)
  if(NOT TARGET Rokae::xMateModel AND EXISTS "${VendoredRokaeSdk_XMATE_MODEL_LIB}")
    add_library(Rokae::xMateModel STATIC IMPORTED GLOBAL)
    set_target_properties(Rokae::xMateModel PROPERTIES
      IMPORTED_LOCATION "${VendoredRokaeSdk_XMATE_MODEL_LIB}"
      INTERFACE_INCLUDE_DIRECTORIES "${VendoredRokaeSdk_INCLUDE_DIR};${VendoredRokaeSdk_EXTERNAL_DIR}"
      INTERFACE_COMPILE_DEFINITIONS "XMATEMODEL_LIB_SUPPORTED=1"
    )
  endif()

  if(NOT TARGET Rokae::xCoreSDK)
    add_library(Rokae::xCoreSDK STATIC IMPORTED GLOBAL)
    set(_ROKAE_LINK_LIBS "")
    if(TARGET Rokae::xMateModel)
      list(APPEND _ROKAE_LINK_LIBS Rokae::xMateModel)
    endif()
    set_target_properties(Rokae::xCoreSDK PROPERTIES
      IMPORTED_LOCATION "${VendoredRokaeSdk_STATIC_LIB}"
      INTERFACE_INCLUDE_DIRECTORIES "${VendoredRokaeSdk_INCLUDE_DIR};${VendoredRokaeSdk_EXTERNAL_DIR}"
      INTERFACE_LINK_LIBRARIES "${_ROKAE_LINK_LIBS}"
    )
    if(TARGET Rokae::xMateModel)
      set_property(TARGET Rokae::xCoreSDK APPEND PROPERTY INTERFACE_COMPILE_DEFINITIONS XMATEMODEL_LIB_SUPPORTED=1)
    endif()
  endif()
endif()
