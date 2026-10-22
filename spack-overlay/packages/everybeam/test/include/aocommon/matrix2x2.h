// Dummy header, which is required for compiling test_invalid_name.cpp.
// The test does not actually use anything from this header.

#ifndef AOCOMMON_MATRIX2x2_H_
#define AOCOMMON_MATRIX2x2_H_

// Define USE_AVX_MATRIX similarly as avx/AvxMacros.h from aocommon.
#if defined(__AVX2__) && defined(__FMA__)
#define USE_AVX_MATRIX
#endif

namespace aocommon {
struct MC2x2 {};
}

#endif // AOCOMMON_MATRIX2x2_H_
