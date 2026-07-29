cmake_minimum_required(VERSION 3.20)
project(redline_exchange_cpp VERSION 0.4.0 LANGUAGES CXX)

option(REDLINE_ENABLE_SANITIZERS "Enable address and undefined-behavior sanitizers" OFF)

add_library(redline_engine cpp/src/order_book.cpp)
target_include_directories(redline_engine PUBLIC cpp/include)
target_compile_features(redline_engine PUBLIC cxx_std_20)

if(MSVC)
  target_compile_options(redline_engine PRIVATE /W4 /permissive-)
else()
  target_compile_options(redline_engine PRIVATE -Wall -Wextra -Wpedantic -Wconversion)
endif()

if(REDLINE_ENABLE_SANITIZERS AND NOT MSVC)
  target_compile_options(redline_engine PUBLIC -fsanitize=address,undefined -fno-omit-frame-pointer)
  target_link_options(redline_engine PUBLIC -fsanitize=address,undefined)
endif()

add_executable(redline_cpp cpp/src/main.cpp)
target_link_libraries(redline_cpp PRIVATE redline_engine)

include(CTest)
if(BUILD_TESTING)
  add_executable(redline_cpp_tests cpp/tests/test_order_book.cpp)
  target_link_libraries(redline_cpp_tests PRIVATE redline_engine)
  add_test(NAME redline_cpp_tests COMMAND redline_cpp_tests)
endif()
