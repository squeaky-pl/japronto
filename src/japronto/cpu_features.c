#include <cpuid.h>
#include <assert.h>

#include "cpu_features.h"

int supports_x86_sse42(void)
{
#if defined(__clang__)
  unsigned int eax = 0, ebx = 0, ecx = 0, edx = 0;
  __get_cpuid(1, &eax, &ebx, &ecx, &edx);
  return ecx & bit_SSE42;
#else
  __builtin_cpu_init();
  return __builtin_cpu_supports("sse4.2");
#endif
}
