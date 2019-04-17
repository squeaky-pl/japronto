#ifndef _MSC_VER
#include <cpuid.h>
#else
#include <intrin.h>
#define __get_cpuid __cpuid
#endif
#include <assert.h>

#include "cpu_features.h"

int supports_x86_sse42(void)
{
#if defined(__clang__)
  unsigned int eax = 0, ebx = 0, ecx = 0, edx = 0;
  __get_cpuid(1, &eax, &ebx, &ecx, &edx);
  return ecx & bit_SSE42;
#elif defined(_MSC_VER)
  int cpuInfo[4];
  __cpuid(cpuInfo, 0);
  return cpuInfo[3] & 0x01111000;
#else
  __builtin_cpu_init();
  return __builtin_cpu_supports("sse4.2");
#endif
}
