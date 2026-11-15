#pragma once
#include <chrono>

class Timer {
 public:
  Timer() : t0_(std::chrono::steady_clock::now()) {}
  void reset() { t0_ = std::chrono::steady_clock::now(); }
  double ms() const {
    return std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - t0_).count();
  }

 private:
  std::chrono::steady_clock::time_point t0_;
};
