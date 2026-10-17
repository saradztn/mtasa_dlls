cmake_minimum_required(VERSION 3.10)
project(ngpd_dx9_upscaler LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_library(ngpd_dx9_upscaler SHARED
    ngpd_dx9_upscaler.cpp
)
target_include_directories(ngpd_dx9_upscaler PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})

add_executable(test_upscaler_cli
    test_upscaler_cli.cpp
)
target_link_libraries(test_upscaler_cli PRIVATE ngpd_dx9_upscaler)
